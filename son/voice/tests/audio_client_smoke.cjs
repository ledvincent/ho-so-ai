/* Synthetic media/HTTP mocks only: no microphone, provider or playable audio. */
const assert = require("node:assert/strict");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.VOICE_BROWSER_CHANNEL ? {channel:process.env.VOICE_BROWSER_CHANNEL} : {})});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    let turnCalls = 0;
    await page.route("**/api/voice/turn", async (route) => { turnCalls += 1; await route.continue(); });
    await page.route("**/api/voice/transcribe", async (route) => {
      assert.equal(route.request().headers()["x-audio-consent"], "1");
      await route.fulfill({json:{text:"I want to renew temporary residence", language:"en", requires_confirmation:true}});
    });
    await page.route("**/api/voice/speech", (route) => route.fulfill({status:200, contentType:"audio/mpeg", body:"ID3synthetic, not playable audio"}));
    await page.goto(process.env.VOICE_TEST_URL || "http://127.0.0.1:8000");
    await page.waitForFunction(() => !document.getElementById("send").disabled);
    const result = await page.evaluate(async () => {
      const {VoiceAudioClient} = await import("/audio-client.js");
      window.syntheticStopped = 0;
      window.syntheticPaused = 0;
      window.syntheticEvents = [];
      window.syntheticTranscript = null;
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {configurable:true, value:async () => ({getTracks:() => [{stop:() => window.syntheticStopped++}]})});
      window.MediaRecorder = class {
        static isTypeSupported(type) { return type.startsWith("audio/webm"); }
        constructor() { this.state = "inactive"; }
        start() { this.state = "recording"; }
        stop() {
          this.state = "inactive";
          this.ondataavailable?.({data:new Blob([new Uint8Array([0x1a, 0x45, 0xdf, 0xa3])])});
          this.onstop?.();
        }
      };
      window.Audio = class {
        async play() {}
        pause() { window.syntheticPaused++; }
      };
      window.sdk = new VoiceAudioClient({onState:(state) => window.syntheticEvents.push(state), onTranscript:(text) => {window.syntheticTranscript = text;}});
      let refused = false;
      try { await window.sdk.startRecording(); } catch (error) { refused = error.message === "audio_consent_required"; }
      const welcome = await window.sdk.startSession("en");
      window.sdk.setAudioConsent(true);
      await window.sdk.readReply();
      await window.sdk.startRecording(); // Interrupts output before microphone opens.
      window.sdk.stopRecording();
      return {refused, language:welcome.language};
    });
    assert.equal(result.refused, true);
    assert.equal(result.language, "en");
    await page.waitForFunction(() => window.syntheticTranscript !== null);
    assert.equal(turnCalls, 0, "transcription must not become an automatic turn");
    const confirmation = await page.evaluate(async () => {
      const reply = await window.sdk.turn(window.syntheticTranscript.text);
      window.sdk.setAudioConsent(false);
      await window.sdk.endSession();
      window.sdk.setAudioConsent(true);
      let endedGuard = false;
      try { await window.sdk.startRecording(); } catch (error) { endedGuard = error.message === "session_required"; }
      return {code:reply.candidate_code, endedGuard, events:window.syntheticEvents, stopped:window.syntheticStopped, paused:window.syntheticPaused};
    });
    assert.equal(confirmation.code, "1.002755");
    assert.equal(confirmation.endedGuard, true);
    assert.equal(turnCalls, 1);
    assert.ok(confirmation.events.includes("speaking"));
    assert.ok(confirmation.events.includes("awaiting_transcript_confirmation"));
    assert.ok(confirmation.stopped > 0);
    assert.ok(confirmation.paused > 0);
    console.log("PASS: English session, consent gate, simulated recording/transcription, user-confirmed turn, interrupt output, release tracks, end session");
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
