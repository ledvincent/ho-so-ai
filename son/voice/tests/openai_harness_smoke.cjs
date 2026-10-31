/* Test-mode UI wiring only. Audio/recognition mocked; no provider calls. */
const assert = require("node:assert/strict");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.VOICE_BROWSER_CHANNEL ? {channel:process.env.VOICE_BROWSER_CHANNEL} : {})});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    let speechCalls = 0, turnCalls = 0;
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/voice/capabilities", (route) => route.fulfill({json:{audio_api_enabled:true}}));
    await page.route("**/api/voice/speech", (route) => {
      assert.equal(route.request().headers()["x-audio-consent"], "1");
      speechCalls++;
      return route.fulfill({status:200, contentType:"audio/mpeg", body:"ID3synthetic not playable audio"});
    });
    await page.route("**/api/voice/transcribe", (route) => route.fulfill({json:{text:"I want to renew temporary residence", language:"en", requires_confirmation:true}}));
    await page.route("**/api/voice/turn", (route) => { turnCalls++; return route.continue(); });
    await page.addInitScript(() => {
      window.mockPlayed = 0;
      window.Audio = class { async play() { window.mockPlayed++; } pause() {} };
      window.SpeechRecognition = class { constructor() { throw new Error("Browser recognition must not run in OpenAI mode"); } };
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {value:async () => ({getTracks:() => [{stop() {}}]})});
      window.MediaRecorder = class {
        static isTypeSupported(type) { return type.startsWith("audio/webm"); }
        constructor() { this.state = "inactive"; }
        start() { this.state = "recording"; }
        stop() {
          this.state = "inactive";
          this.ondataavailable?.({data:new Blob([new Uint8Array([0x1a,0x45,0xdf,0xa3])])});
          this.onstop?.();
        }
      };
    });
    const base = process.env.VOICE_TEST_URL || "http://127.0.0.1:8000";
    await page.goto(base + "/?audio=openai&language=en");
    await page.waitForFunction(() => !document.getElementById("send").disabled);
    assert.equal(speechCalls, 0);
    assert.equal(await page.locator("#read-aloud").isDisabled(), true);
    await page.locator("#audio-consent").check();
    await page.locator("#read-aloud").check();
    await page.waitForFunction(() => window.mockPlayed === 1);
    await page.getByRole("button", {name:"Record with OpenAI", exact:true}).click();
    await page.getByRole("button", {name:"Stop recording", exact:true}).click();
    await page.waitForFunction(() => document.getElementById("utterance").value === "I want to renew temporary residence" && !document.getElementById("send").disabled);
    assert.equal(turnCalls, 0);
    await page.getByRole("button", {name:"Send", exact:true}).click();
    await page.waitForFunction(() => document.getElementById("candidate-title").textContent === "Renew temporary residence");
    await page.waitForFunction(() => window.mockPlayed === 2);
    assert.equal(turnCalls, 1);
    await page.locator("#audio-consent").uncheck();
    assert.equal(await page.locator("#read-aloud").isChecked(), false);
    assert.equal(await page.getByRole("button", {name:"Record with OpenAI", exact:true}).isDisabled(), true);
    assert.deepEqual(errors, []);
    console.log("PASS: OpenAI harness opt-in, greeting playback, recording/transcript confirmation, English response playback, consent withdrawal; no live provider calls");
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
