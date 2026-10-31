/* Synthetic WebRTC/media/signaling: no live provider, mic or API key. */
const assert = require("node:assert/strict");
const path = require("node:path");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.VOICE_BROWSER_CHANNEL ? {channel:process.env.VOICE_BROWSER_CHANNEL} : {})});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    let calls = 0;
    let documentCalls = 0;
    const fixtureMode = process.env.VOICE_TEST_FIXTURE === "1";
    const ragMode = process.env.VOICE_TEST_RAG === "1";
    let holdDocument = false, releaseDocument, documentStarted;
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/voice/capabilities", (route) => route.fulfill({json:{realtime_available:true}}));
    await page.route("**/realtime-client.js", (route) => route.fulfill({contentType:"application/javascript", path:path.resolve(__dirname, "../src/voice_app/static/realtime-client.js")}));
    await page.route("**/fixture-tool.js", (route) => route.fulfill({contentType:"application/javascript", path:path.resolve(__dirname, "../src/voice_app/static/fixture-tool.js")}));
    await page.route("**/rag-tool.js", (route) => route.fulfill({contentType:"application/javascript", path:path.resolve(__dirname, "../src/voice_app/static/rag-tool.js")}));
    await page.route("**/api/voice/rag", route => {
      const args = route.request().postDataJSON();
      assert.equal(args.question, "Synthetic general procedure question");
      return route.fulfill({json:{status:"answered", answer:"Synthetic sourced answer [s1]", procedure_code:"1.001146", choices:[], citations:[{id:"s1",title:"Synthetic RAG source",url:"https://example.org/source"}]}});
    });
    await page.route("**/api/voice/fixture-document", async (route) => {
      documentCalls++;
      const args = route.request().postDataJSON();
      assert.deepEqual(Object.keys(args), ["procedure_code"]);
      if (holdDocument) await new Promise(resolve => { releaseDocument = resolve; documentStarted?.(); });
      return route.fulfill({headers:{"X-HoSo-Synthetic-Fixture":"1"}, json:{synthetic:true, procedure_code:args.procedure_code,
        document_title:"Synthetic document title", section_heading:"Synthetic heading", section_count:6,
        source_url:"https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=" + args.procedure_code}}).catch(() => {});
    });
    await page.route("**/api/voice/realtime", (route) => {
      if (route.request().method() === "POST") {
        calls++;
        assert.equal(route.request().headers()["x-audio-consent"], "1");
        assert.equal(route.request().headers()["authorization"], undefined);
        return route.fulfill({status:200, contentType:"application/sdp", headers:{"X-Call-Max-Seconds":"180"}, body:"v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"});
      }
      return route.fulfill({json:{state:"ended"}});
    });
    await page.route("**/api/voice/turn", () => { throw new Error("No Send/text turn in a realtime call"); });
    await page.addInitScript(() => {
      window.syntheticTrackStops = 0;
      window.syntheticPeerClosed = 0;
      window.syntheticAudioPlayed = 0;
      window.syntheticSent = [];
      const track = {stop:() => window.syntheticTrackStops++};
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {value:async (options) => {
        window.syntheticEchoCancellation = options.audio.echoCancellation;
        return {getTracks:() => [track], getAudioTracks:() => [track]};
      }});
      window.MediaRecorder = class { constructor() { throw new Error("A phone-like call must not use MediaRecorder"); } };
      window.Audio = class { async play() { window.syntheticAudioPlayed++; } pause() {} };
      window.RTCPeerConnection = class {
        constructor() { window.syntheticPeer = this; }
        addTrack() {}
        createDataChannel() {
          this.channel = {send:(value) => {
            const message = JSON.parse(value);
            window.syntheticSent.push(message);
            if (message.type === "session.update") {
              window.syntheticMicEnabledBeforeProfile = track.enabled;
              window.syntheticGreetedBeforeProfile = window.syntheticSent.some(item => item.type === "response.create");
              queueMicrotask(() => this.channel.onmessage?.({data:JSON.stringify({type:"session.updated", session:message.session})}));
            }
          }, close() {}};
          return this.channel;
        }
        async createOffer() { return {type:"offer", sdp:"v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"}; }
        async setLocalDescription() {}
        async setRemoteDescription() {
          this.connectionState = "connected";
          this.onconnectionstatechange?.();
          this.ontrack?.({streams:[{}]});
          this.channel.onopen?.();
        }
        close() { window.syntheticPeerClosed++; }
      };
    });
    const base = process.env.VOICE_TEST_URL || "http://127.0.0.1:8000";
    await page.goto(base + "/?audio=realtime&language=en" + (fixtureMode ? "&documents=fixture" : ragMode ? "&documents=rag" : ""));
    await page.getByRole("status").getByText(/Accept the disclosure/).waitFor();
    assert.equal(await page.locator("#composer").isVisible(), false);
    assert.equal(await page.locator(".read-toggle").isVisible(), false);
    assert.equal(await page.getByRole("button", {name:"Start voice call", exact:true}).isDisabled(), true);
    assert.equal(calls, 0);
    await page.locator("#audio-consent").check();
    await page.getByRole("button", {name:"Start voice call", exact:true}).click();
    await page.waitForFunction(() => window.syntheticSent.some((item) => item.type === "response.create"));
    assert.equal(await page.evaluate(() => window.syntheticSent[0].type), "session.update");
    assert.equal(await page.evaluate(() => window.syntheticSent[0].session.max_output_tokens), 2048);
    assert.equal(await page.evaluate(ragMode => window.syntheticSent[0].session.instructions.includes(ragMode ? "CONNECTED PROCEDURE ASSISTANT MODE" : "ho-so-ai-foreigner-intake-v2"), ragMode), true);
    assert.equal(await page.evaluate(() => window.syntheticMicEnabledBeforeProfile), false);
    assert.equal(await page.evaluate(() => window.syntheticGreetedBeforeProfile), false);
    if (fixtureMode) {
      assert.equal(await page.evaluate(() => window.syntheticSent[0].session.tools[0].name), "inspect_test_document");
      for (const code of ["1.001146", "1.003326", "1.003342", "1.000771"]) {
        await page.evaluate(code => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.done", response:{status:"completed", output:[{
          type:"function_call", name:"inspect_test_document", call_id:"synthetic_"+code, arguments:JSON.stringify({procedure_code:code})}]}})}), code);
        await page.waitForFunction(code => window.syntheticSent.some(item => item.item?.type === "function_call_output" && JSON.parse(item.item.output).procedure_code === code), code);
      }
      assert.equal(documentCalls, 4);
      assert.equal(await page.evaluate(() => window.syntheticSent.filter(item => item.type === "response.create" && item.response?.tool_choice === "none").length), 4);
      // Duplicate provider event must not fetch or speak again.
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.done", response:{status:"completed", output:[{
        type:"function_call", name:"inspect_test_document", call_id:"synthetic_1.001146", arguments:'{"procedure_code":"1.001146"}'}]}})}));
      assert.equal(documentCalls, 4);
    } else if (ragMode) {
      assert.equal(await page.evaluate(() => window.syntheticSent[0].session.tools[0].name), "ask_procedure_assistant");
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.done", response:{status:"completed", output:[{
        type:"function_call", name:"ask_procedure_assistant", call_id:"synthetic_rag", arguments:JSON.stringify({question:"Synthetic general procedure question"})}]}})}));
      await page.waitForFunction(() => window.syntheticSent.some(item => item.item?.call_id === "synthetic_rag"));
      await page.getByRole("log").getByText("Synthetic sourced answer [s1]", {exact:true}).waitFor();
      await page.getByRole("log").getByText("SOURCE: Synthetic RAG source — https://example.org/source", {exact:true}).waitFor();
      assert.equal(await page.getByRole("log").getByRole("link").getAttribute("href"), "https://example.org/source");
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.output_audio_transcript.done", transcript:"SOURCE: untrusted spoken text — https://example.org/untrusted"})}));
      assert.equal(await page.getByRole("log").getByRole("link").count(), 1, "Spoken prose must never create a source link");
      assert.equal(documentCalls, 0);
    } else {
      assert.equal(await page.evaluate(() => window.syntheticSent[0].session.tools), undefined);
      assert.equal(documentCalls, 0);
    }
    await page.evaluate(() => {
      const emit = (type, extra = {}) => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type, ...extra})});
      emit("input_audio_buffer.speech_started");
      emit("input_audio_buffer.speech_stopped");
      emit("response.created");
      emit("output_audio_buffer.started");
      emit("response.done", {response:{status:"completed"}});
    });
    await page.getByRole("status").getByText("The agent is speaking. You can interrupt by talking.", {exact:true}).waitFor();
    await page.evaluate(() => {
      const emit = (type, extra = {}) => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type, ...extra})});
      emit("input_audio_buffer.speech_started"); // User interrupts mid-response.
      emit("output_audio_buffer.cleared");
      emit("response.done", {response:{status:"cancelled", status_details:{reason:"turn_detected"}}});
    });
    await page.getByRole("status").getByText("Listening to you…", {exact:true}).waitFor();
    await page.evaluate(() => {
      const emit = (type, extra = {}) => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type, ...extra})});
      emit("input_audio_buffer.speech_stopped");
      emit("response.created");
      emit("output_audio_buffer.started");
      emit("response.output_audio_transcript.done", {transcript:"Synthetic conversational reply"});
      emit("response.done", {response:{status:"completed"}});
      emit("output_audio_buffer.stopped");
    });
    await page.getByRole("log").getByText("Synthetic conversational reply").waitFor();
    assert.equal(calls, 1, "multiple turns share one continuous call");
    assert.equal(await page.evaluate(() => window.syntheticEchoCancellation), true);
    if (fixtureMode) {
      holdDocument = true;
      const started = new Promise(resolve => { documentStarted = resolve; });
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.done", response:{status:"completed", output:[{
        type:"function_call", name:"inspect_test_document", call_id:"synthetic_interrupted", arguments:'{"procedure_code":"1.001146"}'}]}})}));
      await started;
      const responseCount = await page.evaluate(() => window.syntheticSent.filter(item => item.type === "response.create").length);
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"input_audio_buffer.speech_started"})}));
      releaseDocument();
      await page.waitForFunction(() => window.syntheticSent.some(item => item.item?.call_id === "synthetic_interrupted" && JSON.parse(item.item.output).error === "cancelled_by_interruption"));
      assert.equal(await page.evaluate(() => window.syntheticSent.filter(item => item.type === "response.create").length), responseCount);
      const lateStarted = new Promise(resolve => { documentStarted = resolve; });
      await page.evaluate(() => window.syntheticPeer.channel.onmessage({data:JSON.stringify({type:"response.done", response:{status:"completed", output:[{
        type:"function_call", name:"inspect_test_document", call_id:"synthetic_hangup", arguments:'{"procedure_code":"1.001146"}'}]}})}));
      await lateStarted;
    }
    await page.getByRole("button", {name:"End call", exact:true}).first().click();
    if (fixtureMode) releaseDocument();
    await page.getByRole("button", {name:"Start voice call", exact:true}).waitFor();
    assert.equal(await page.evaluate(() => window.syntheticTrackStops), 1);
    assert.equal(await page.evaluate(() => window.syntheticPeerClosed), 1);
    if (fixtureMode) assert.equal(await page.evaluate(() => window.syntheticSent.some(item => item.item?.call_id === "synthetic_hangup")), false);
    assert.deepEqual(errors, []);
    console.log("PASS: consent, single live WebRTC connection, bounded audio budget, generation done does not end playout, interruption state, no Record/Send, hangup/mic cleanup; all media/provider mocked");
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
