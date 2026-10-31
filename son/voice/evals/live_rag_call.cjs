// Real Realtime + RAG, synthetic silent microphone and fictional text input.
// At most one call and three document-model requests; never an acoustic acceptance test.
if (!process.argv.includes("--live")) {
  console.log("Not run. --live permits one Realtime call and at most three RAG generations.");
  process.exit(0);
}
const assert = require("node:assert/strict");
const {chromium} = require("playwright");

(async()=>{
  const vi=process.argv.includes("--vi");
  const browser=await chromium.launch({headless:true,channel:process.env.VOICE_BROWSER_CHANNEL||"msedge",args:["--autoplay-policy=no-user-gesture-required"]});
  let page;
  try {
    page=await browser.newPage();
    let requests=0;
    await page.route("**/api/voice/rag", route=>{
      if(++requests>6) return route.fulfill({status:429,json:{error:"probe_request_limit"}});
      return route.continue();
    });
    await page.addInitScript(()=>{
      window.probe={tools:[],requests:[],spokenTools:[],played:0,profile:false,errors:[],responseFailures:0};
      const toolResponses=new Map();
      let waitingTool=null;
      const create=RTCPeerConnection.prototype.createDataChannel;
      RTCPeerConnection.prototype.createDataChannel=function(...args){
        window.probePeer=this;
        const channel=create.apply(this,args);
        window.probeChannel=channel;
        const send=channel.send.bind(channel);
        channel.send=value=>{
          const event=JSON.parse(value);
          if(event.item?.type==="function_call_output") {
            const output=JSON.parse(event.item.output);
            probe.tools.push({status:output.status,error:output.error,procedure:output.procedure_code,citations:output.citations?.length||0,choices:output.choices?.length||0,choiceLabels:output.choices?.map(c=>c.label)||[],reset:output.context_reset});
          }
          if(event.type==="response.create" && event.response?.tool_choice==="none") waitingTool=probe.tools.length;
          return send(value);
        };
        channel.addEventListener("message",event=>{
          const data=JSON.parse(event.data);
          if(data.type==="session.updated" && data.session?.instructions?.includes("CONNECTED PROCEDURE ASSISTANT MODE")) probe.profile=true;
          if(data.type==="response.created" && waitingTool!==null) {
            toolResponses.set(data.response.id,waitingTool);waitingTool=null;
          }
          if(data.type==="output_audio_buffer.stopped") {
            probe.played++;
            if(toolResponses.has(data.response_id)) probe.spokenTools.push(toolResponses.get(data.response_id));
          }
          if(data.type==="response.done" && ["failed","incomplete"].includes(data.response?.status)) probe.responseFailures++;
          if(data.type==="response.done") for(const item of data.response?.output||[]) {
            if(item.type==="function_call") {
              const args=JSON.parse(item.arguments);
              probe.requests.push({reset:args.reset,choice:args.clarification_answer,question:args.question});
            }
          }
          if(data.type==="error") probe.errors.push("realtime_error");
        });
        return channel;
      };
      const AudioElement=window.Audio;
      window.Audio=function(){const audio=new AudioElement();audio.muted=true;return audio;};
      Object.defineProperty(navigator.mediaDevices,"getUserMedia",{value:async()=>{
        const ctx=new AudioContext();await ctx.resume();
        const dest=ctx.createMediaStreamDestination(),gain=ctx.createGain(),osc=ctx.createOscillator();
        gain.gain.value=0;osc.connect(gain);gain.connect(dest);osc.start();
        window.probeAudio=ctx;window.probeStream=dest.stream;return dest.stream;
      }});
    });
    await page.goto("http://127.0.0.1:8003/?audio=realtime&documents=rag&language="+(vi?"vi":"en"));
    await page.locator("#audio-consent").check();
    await page.locator("#microphone").click();
    await page.waitForFunction(()=>probe.profile && probe.played>=1,null,{timeout:45000});
    let step=0;
    async function turn(text){
      const before=await page.evaluate(()=>({tools:probe.tools.length,played:probe.played}));
      await page.evaluate(text=>{
        probeChannel.send(JSON.stringify({type:"conversation.item.create",item:{type:"message",role:"user",content:[{type:"input_text",text}]}}));
        probeChannel.send(JSON.stringify({type:"response.create"}));
      },text);
      await page.waitForFunction(before=>probe.tools.length>before.tools,before,{timeout:195000});
      assert.equal(await page.evaluate(()=>Boolean(probe.tools.at(-1).error)),false,"Document tool returned an error");
      console.log(JSON.stringify({language:vi?"vi":"en",step:++step,result:await page.evaluate(()=>probe.tools.at(-1))}));
      // Correlate the exact response: a short answer may already have finished
      // before this wait starts, and an earlier 'checking' filler does not count.
      await page.waitForFunction(index=>probe.spokenTools.includes(index),before.tools+1,{timeout:60000});
      return page.evaluate(()=>probe.tools.at(-1));
    }
    let last=await turn(vi?"Tôi muốn gia hạn tạm trú ở Việt Nam.":"I need help extending my stay in Vietnam.");
    assert.equal(last.status,"needs_clarification");
    assert.ok(!last.procedure && last.choices>0);
    // Follow every actual backend clarification, rather than assuming one turn.
    for(let i=0;i<3 && !last.procedure;i++){
      const label=last.choiceLabels.find(label=>/provincial|cấp tỉnh/i.test(label));
      assert.ok(label,"No offered provincial option; do not invent a choice");
      last=await turn(vi?`Trong ví dụ giả định này, tôi chọn: ${label}.`:`For this fictional example, I choose: ${label}.`);
    }
    assert.equal(last.procedure,"1.001146");
    const documents=await turn(vi?"Tôi cần chuẩn bị những giấy tờ gì?":"What documents do I need?");
    const followup=await turn(vi?"Thời gian giải quyết là bao lâu?":"How long does it take?");
    const result=await page.evaluate(()=>({profile:probe.profile,tools:probe.tools,played:probe.played,errors:probe.errors,responseFailures:probe.responseFailures,
      sourceLinks:document.querySelectorAll("#messages a[href^='https://']").length}));
    assert.equal(result.tools[0].status,"needs_clarification");
    assert.ok(result.tools[0].choices>0);
    assert.equal(documents.procedure,"1.001146");
    assert.equal(followup.procedure,"1.001146");
    assert.ok(documents.citations>0 && followup.citations>0 && result.sourceLinks>0);
    assert.equal(result.responseFailures,0);
    assert.deepEqual(result.errors,[]);
    console.log(JSON.stringify({language:vi?"vi":"en",passed:true,...result,scope:"real providers/WebRTC, synthetic input, muted output; human microphone test still required"}));
  } catch(error){
    console.log(JSON.stringify({language:vi?"vi":"en",passed:false,error:error.name,observations:page?await page.evaluate(()=>window.probe).catch(()=>null):null}));
    process.exitCode=1;
  } finally {
    if(page) await page.evaluate(async()=>{
      probeStream?.getTracks().forEach(track=>track.stop());probePeer?.close();await probeAudio?.close();
      await fetch("/api/voice/realtime",{method:"DELETE",credentials:"same-origin"});
      await fetch("/api/voice/session",{method:"DELETE",credentials:"same-origin"});
    }).catch(()=>{});
    await browser.close();
  }
})();
