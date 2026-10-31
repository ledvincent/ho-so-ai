/* Provider-free tests of the reusable SDK, including asynchronous cancellation. */
const assert = require("node:assert/strict");
const path = require("node:path");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true, channel:process.env.VOICE_BROWSER_CHANNEL || "msedge"});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    let lookups = 0, deleted = 0, release, entered, hold = false;
    await page.route("**/*", async route => {
      const url = new URL(route.request().url());
      if (url.pathname === "/") return route.fulfill({contentType:"text/html",body:"<!doctype html><title>SDK test</title>"});
      if (["/realtime-client.js","/rag-tool.js"].includes(url.pathname)) return route.fulfill({contentType:"application/javascript",path:path.resolve(__dirname,"../src/voice_app/static"+url.pathname)});
      if (url.pathname === "/api/voice/session") {
        if (route.request().method() === "DELETE") deleted++;
        return route.fulfill({json:{}});
      }
      if (url.pathname === "/api/voice/realtime") return route.fulfill({status:200,headers:{"X-Call-Max-Seconds":"480"},body:"v=0\r\n"});
      if (url.pathname === "/api/voice/rag") {
        lookups++;
        if (hold) await new Promise(resolve => { release=resolve; entered?.(); });
        return route.fulfill({json:{status:"answered",answer:"Synthetic sourced answer [s1]",citations:[{id:"s1",title:"Source",url:"https://example.org/source"}],
          choices:[],procedure_code:"1.001146",context_reset:true,documents:[{id:"document",form:{schema_url:"/never-fetch"}}]}}).catch(()=>{});
      }
      throw new Error("Unexpected fetch: "+url.pathname);
    });
    await page.goto("http://localhost:9876/");
    await page.evaluate(async () => {
      window.observed={sent:[],results:[],finals:[],errors:[],states:[],resets:0,stops:0,closed:0,paused:0};
      window.denyMic=false;
      Object.defineProperty(navigator.mediaDevices,"getUserMedia",{value:async()=>{
        if (window.denyMic) throw new DOMException("Synthetic denial","NotAllowedError");
        const track={enabled:true,stop:()=>observed.stops++};
        return {getTracks:()=>[track],getAudioTracks:()=>[track]};
      }});
      window.Audio=class {async play(){} pause(){observed.paused++;}};
      window.RTCPeerConnection=class {
        constructor(){window.peer=this;}
        addTrack(){}
        createDataChannel(){
          this.channel={send:value=>{
            const data=JSON.parse(value); observed.sent.push(data);
            if(data.type==="session.update") queueMicrotask(()=>this.channel.onmessage?.({data:JSON.stringify({type:"session.updated",session:data.session})}));
          },close:()=>{}};
          return this.channel;
        }
        async createOffer(){return {sdp:"v=0\r\n"};}
        async setLocalDescription(){}
        async setRemoteDescription(){this.connectionState="connected"; this.channel.onopen?.();}
        close(){observed.closed++;}
      };
      const {RealtimeVoiceClient}=await import("/realtime-client.js");
      window.client=new RealtimeVoiceClient({onState:x=>observed.states.push(x),onError:x=>observed.errors.push(x),
        onResult:x=>observed.results.push(x),onFinalTranscript:x=>observed.finals.push(x),onContextReset:()=>observed.resets++});
      window.emit=(type,extra={})=>peer.channel.onmessage({data:JSON.stringify({type,...extra})});
      window.tool=(id,responseId)=>emit("response.done",{response:{id:responseId,status:"completed",output:[{type:"function_call",name:"ask_procedure_assistant",call_id:id,arguments:JSON.stringify({question:"Synthetic general question"})}]}});
      await client.start({language:"vi",consent:true,ragDocuments:true});
    });
    await page.waitForFunction(()=>observed.sent.some(x=>x.type==="response.create"));
    await page.evaluate(()=>{
      tool("normal"); tool("normal");
      emit("conversation.item.input_audio_transcription.completed",{item_id:"input1",transcript:"Synthetic caller question"});
      emit("conversation.item.input_audio_transcription.completed",{item_id:"input1",transcript:"Synthetic caller question"});
      emit("response.output_audio_transcript.done",{item_id:"output1",transcript:"Synthetic assistant speech"});
    });
    await page.waitForFunction(()=>observed.results.length===1);
    assert.equal(lookups,1);
    assert.equal(await page.evaluate(()=>observed.finals.length),2);
    assert.equal(await page.evaluate(()=>observed.finals[0].role),"user");
    assert.equal(await page.evaluate(()=>observed.results[0].documents[0].id),"document");
    assert.equal(await page.evaluate(()=>observed.resets),1);
    assert.equal(await page.evaluate(()=>JSON.parse(observed.sent.find(x=>x.item?.call_id==="normal").item.output).documents),undefined);
    // A completed event arriving after barge-in must not start its stale lookup.
    await page.evaluate(()=>{
      emit("response.created",{response:{id:"old-response"}});
      emit("input_audio_buffer.speech_started");
      tool("stale", "old-response");
    });
    await page.waitForFunction(()=>observed.sent.some(x=>x.item?.call_id==="stale"));
    assert.equal(lookups,1);
    hold=true;
    let started=new Promise(resolve=>{entered=resolve;});
    await page.evaluate(()=>{emit("input_audio_buffer.speech_stopped"); tool("interrupted");});
    await started;
    const before=await page.evaluate(()=>observed.sent.filter(x=>x.type==="response.create").length);
    await page.evaluate(()=>emit("input_audio_buffer.speech_started"));
    release();
    await page.waitForFunction(()=>observed.sent.some(x=>x.item?.call_id==="interrupted" && JSON.parse(x.item.output).error==="cancelled_by_interruption"));
    assert.equal(await page.evaluate(()=>observed.results.length),1);
    assert.equal(await page.evaluate(()=>observed.sent.filter(x=>x.type==="response.create").length),before);
    started=new Promise(resolve=>{entered=resolve;});
    await page.evaluate(()=>{emit("input_audio_buffer.speech_stopped"); tool("hangup");});
    await started;
    await page.evaluate(()=>client.stop());
    release();
    assert.equal(await page.evaluate(()=>observed.sent.some(x=>x.item?.call_id==="hangup")),false);
    assert.equal(await page.evaluate(()=>observed.stops),1);
    assert.equal(await page.evaluate(()=>observed.closed),1);
    assert.equal(await page.evaluate(()=>observed.paused),1);
    assert.ok(deleted>=2);
    hold=false;
    // Fresh call, then transport failure must release the new microphone.
    await page.evaluate(()=>client.start({language:"en",consent:true,ragDocuments:true}));
    await page.evaluate(()=>{peer.connectionState="disconnected"; peer.onconnectionstatechange();});
    await page.waitForFunction(()=>observed.errors.some(x=>x.code==="audio_disconnected"),null,{timeout:12000});
    await page.waitForFunction(()=>observed.stops===2);
    await page.evaluate(async()=>{window.denyMic=true; try {await client.start({consent:true});} catch {}});
    assert.equal(await page.evaluate(()=>observed.states.at(-1)),"microphone_denied");
    assert.equal(await page.evaluate(()=>observed.errors.at(-1).code),"microphone_denied");
    // Two rapid start requests may create only the newest call; teardown must
    // finish before its new session cookie is issued.
    await page.evaluate(async()=>{
      window.denyMic=false;
      await Promise.all([client.start({consent:true,ragDocuments:true}),client.start({consent:true,ragDocuments:true})]);
      await client.stop();
    });
    assert.equal(await page.evaluate(()=>observed.stops),3);
    assert.equal(await page.evaluate(()=>observed.closed),3);
    assert.deepEqual(errors,[]);
    console.log("PASS: SDK callbacks, final transcripts/dedup, opaque document metadata, stale events, RAG cancellation, hangup, fresh call, disconnect and denied microphone. All network/media mocked.");
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
