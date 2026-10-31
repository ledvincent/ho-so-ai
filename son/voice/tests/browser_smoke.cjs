/* Synthetic browser checks. Real microphone/recognition needs manual testing. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.VOICE_BROWSER_CHANNEL ? {channel:process.env.VOICE_BROWSER_CHANNEL} : {})});
  const base = process.env.VOICE_TEST_URL || "http://127.0.0.1:8000";
  const output = path.resolve(process.env.VOICE_SCREENSHOT_DIR || "work/voice-qa");
  await fs.mkdir(output, {recursive:true});
  try {
    const context = await browser.newContext({viewport:{width:1280, height:1100}});
    const errors = [];
    context.on("page", (page) => page.on("pageerror", (error) => errors.push(error.message)));
    const page = await context.newPage();
    await page.goto(base);
    await page.getByRole("button", {name:"Gửi", exact:true}).waitFor();
    await page.waitForFunction(() => !document.getElementById("send").disabled);
    await page.getByLabel("Nhập nhu cầu của bạn", {exact:true}).fill("Tôi cần làm tạm trú");
    await page.getByRole("button", {name:"Gửi", exact:true}).click();
    await page.getByRole("log").getByText("Bạn muốn đăng ký tạm trú lần đầu hay gia hạn đăng ký tạm trú đã có?", {exact:true}).waitFor();
    await page.getByRole("button", {name:"Gia hạn tạm trú", exact:true}).click();
    await page.waitForFunction(() => document.getElementById("candidate-description").textContent.includes("1.002755"));
    await page.screenshot({path:path.join(output, "desktop.png"), fullPage:true});

    await page.getByLabel("Nhập nhu cầu của bạn", {exact:true}).fill("đọc hồ sơ của tôi");
    await page.getByRole("button", {name:"Gửi", exact:true}).click();
    await page.getByRole("log").getByText(/Tôi chưa có quyền truy cập hồ sơ cá nhân/).waitFor();
    await page.getByRole("button", {name:"Bắt đầu lại", exact:true}).click();
    await page.waitForFunction(() => !document.getElementById("send").disabled);
    await page.getByLabel("Nhập nhu cầu của bạn", {exact:true}).fill("<img src=x onerror=alert(1)>");
    await page.getByRole("button", {name:"Gửi", exact:true}).click();
    await page.getByRole("log").getByText("<img src=x onerror=alert(1)>", {exact:true}).waitFor();
    assert.equal(await page.locator("#messages img").count(), 0);

    const mobile = await context.newPage();
    await mobile.setViewportSize({width:390, height:844});
    await mobile.addInitScript(() => {
      Object.defineProperty(window, "SpeechRecognition", {value:undefined, configurable:true});
      Object.defineProperty(window, "webkitSpeechRecognition", {value:undefined, configurable:true});
    });
    await mobile.goto(base);
    await mobile.waitForFunction(() => !document.getElementById("send").disabled);
    assert.equal(await mobile.getByRole("button", {name:"Nói bằng giọng nói"}).isDisabled(), true);
    await mobile.getByRole("button", {name:"Đăng ký tạm trú lần đầu", exact:true}).click();
    await mobile.waitForFunction(() => document.getElementById("candidate-description").textContent.includes("1.004194"));
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    assert.equal(await mobile.evaluate(() => localStorage.length), 0);
    await mobile.screenshot({path:path.join(output, "mobile.png"), fullPage:true});

    const audio = await context.newPage();
    await audio.addInitScript(() => {
      // Explicitly synthetic recognition: exercises UI wiring, never a real mic.
      window.SpeechRecognition = class {
        start() {
          queueMicrotask(() => {
            if (window.syntheticMicDenied) this.onerror?.({error:"not-allowed"});
            else this.onresult?.({results:[[{transcript:"Tôi muốn gia hạn tạm trú"}]]});
            this.onend?.();
          });
        }
        stop() { this.onend?.(); }
        abort() {}
      };
    });
    await audio.goto(base);
    await audio.waitForFunction(() => !document.getElementById("send").disabled);
    assert.equal(await audio.getByRole("button", {name:"Nói bằng giọng nói"}).isDisabled(), true);
    await audio.locator("#audio-consent").check();
    await audio.getByRole("button", {name:"Nói bằng giọng nói"}).click();
    await audio.waitForFunction(() => document.getElementById("utterance").value === "Tôi muốn gia hạn tạm trú");
    assert.equal(await audio.locator("#candidate-description").textContent(), "Chưa chọn thủ tục. Trợ lý sẽ hỏi lại khi chưa rõ nhu cầu.");
    await audio.getByRole("button", {name:"Gửi", exact:true}).click();
    await audio.waitForFunction(() => document.getElementById("candidate-description").textContent.includes("1.002755"));
    await audio.evaluate(() => { window.syntheticMicDenied = true; });
    await audio.getByRole("button", {name:"Nói bằng giọng nói"}).click();
    await audio.getByRole("status").getByText(/Chưa có quyền dùng mic/).waitFor();
    assert.equal(await audio.getByLabel("Nhập nhu cầu của bạn", {exact:true}).isEnabled(), true);
    assert.deepEqual(errors, []);
    console.log("PASS: clarification, renewal, personal refusal, restart, escaped input, mobile registration, text fallback, no horizontal overflow, no localStorage, synthetic speech-to-text confirmation, synthetic mic denial");
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
