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
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/voice/capabilities", (route) => route.fulfill({json:{realtime_available:true}}));
    await page.route("**/realtime-client.js", (route) => route.fulfill({contentType:"application/javascript", path:path.resolve(__dirname, "../src/voice_app/static/realtime-client.js")}));
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
        createDataChannel() { this.channel = {send:(value) => window.syntheticSent.push(JSON.parse(value)), close() {}}; return this.channel; }
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
    await page.goto(base + "/?audio=realtime&language=en");
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
    await page.getByRole("button", {name:"End call", exact:true}).first().click();
    await page.getByRole("button", {name:"Start voice call", exact:true}).waitFor();
    assert.equal(await page.evaluate(() => window.syntheticTrackStops), 1);
    assert.equal(await page.evaluate(() => window.syntheticPeerClosed), 1);
    assert.deepEqual(errors, []);
    console.log("PASS: consent, single live WebRTC connection, bounded audio budget, generation done does not end playout, interruption state, no Record/Send, hangup/mic cleanup; all media/provider mocked");
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
