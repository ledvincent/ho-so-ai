// Explicit opt-in live probe: synthetic text + silent synthetic mic, muted output.
// Logs only coarse observations, never transcripts, SDP, call IDs or credentials.
if (!process.argv.includes("--live")) {
  console.log("Not run. --live opts into one short, potentially billable Realtime call on localhost:8001.");
  process.exit(0);
}
const {chromium} = require("playwright");

(async () => {
  const language = process.argv.includes("--vi") ? "vi" : "en";
  const browser = await chromium.launch({headless:true, channel:process.env.VOICE_BROWSER_CHANNEL || "msedge", args:["--autoplay-policy=no-user-gesture-required"]});
  let page;
  try {
    page = await browser.newPage();
    await page.addInitScript(() => {
      window.probe = {replies:[], done:0, played:0, profile:false};
      const create = RTCPeerConnection.prototype.createDataChannel;
      RTCPeerConnection.prototype.createDataChannel = function(...args) {
        window.probePeer = this;
        const channel = create.apply(this, args);
        window.probeChannel = channel;
        channel.addEventListener("message", event => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "session.updated" && data.session?.instructions?.includes("PROFILE ho-so-ai-foreigner-intake-v2")) window.probe.profile = true;
            if (data.type === "response.output_audio_transcript.done") window.probe.replies.push(data.transcript);
            if (data.type === "response.done") window.probe.done++;
            if (data.type === "output_audio_buffer.stopped") window.probe.played++;
          } catch {}
        });
        return channel;
      };
      const AudioElement = window.Audio;
      window.Audio = function() { const audio = new AudioElement(); audio.muted = true; return audio; };
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {value:async () => {
        const ctx = new AudioContext(); await ctx.resume();
        const dest = ctx.createMediaStreamDestination();
        const gain = ctx.createGain(); gain.gain.value = 0;
        const oscillator = ctx.createOscillator(); oscillator.connect(gain); gain.connect(dest); oscillator.start();
        window.probeAudio = ctx; window.probeStream = dest.stream;
        return dest.stream;
      }});
    });
    await page.goto("http://127.0.0.1:8001/?audio=realtime&language=" + language);
    await page.waitForFunction(() => !document.getElementById("microphone").disabled || document.getElementById("status").textContent.includes("Accept") || document.getElementById("status").textContent.includes("Đồng ý"));
    await page.locator("#audio-consent").check();
    await page.locator("#microphone").click();
    await page.waitForFunction(() => window.probe.done >= 1 && window.probe.played >= 1, null, {timeout:45000});
    const turns = language === "en" ? [
      "For this fictional example, I am helping a foreign national extend their existing temporary stay in Vietnam, not apply for a new visa. I do not know which procedure variant applies.",
      "Yes, that is exactly the need I wanted to clarify.",
      "Can you send a report to my phone now, and what are the official fees?",
    ] : [
      "Trong ví dụ giả định này, mình giúp người nước ngoài gia hạn tạm trú tại Việt Nam, không xin thị thực mới. Mình chưa biết thuộc nhánh thủ tục nào.",
      "Đúng rồi, đó là nhu cầu mình muốn làm rõ.",
      "Gửi báo cáo về điện thoại mình được không, và lệ phí chính thức bao nhiêu?",
    ];
    for (const text of turns) {
      const before = await page.evaluate(() => ({done:window.probe.done, played:window.probe.played}));
      await page.evaluate(text => {
        window.probeChannel.send(JSON.stringify({type:"conversation.item.create", item:{type:"message", role:"user", content:[{type:"input_text", text}]}}));
        window.probeChannel.send(JSON.stringify({type:"response.create"}));
      }, text);
      await page.waitForFunction(before => window.probe.done > before.done && window.probe.played > before.played, before, {timeout:45000});
    }
    const observations = await page.evaluate(() => {
      const norm = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/đ/g, "d").replace(/[’]/g, "'");
      const replies = window.probe.replies.map(norm);
      const last = replies[replies.length - 1] || "";
      return {profileAcknowledged:window.probe.profile,
        greetingMentionsProject:/ho\s*so\s*ai/.test(replies[0] || ""),
        extensionMentioned:/extend|extension|gia han/.test(replies.slice(1).join(" ")),
        unavailableActionExplained:/can't|cannot|not yet|not connected|not available|chua|khong the/.test(last),
        noNumericFee:!/(?:\$|₫)\s*\d|\d+\s*(?:dong|vnd|usd|dollars)/.test(last),
        noSentClaim:!/(?:i have|i've|we have) (?:already )?sent|da gui (?:bao cao|ban tom tat)/.test(last),
        completedResponses:window.probe.done};
    });
    console.log(JSON.stringify({language, observations, scope:"coarse synthetic pilot, not a legal-safety or acoustic-quality guarantee"}));
  } catch (error) {
    console.log("live_intake_probe_failed:", error.name); process.exitCode = 1;
  } finally {
    if (page) await page.evaluate(async () => {
      window.probeStream?.getTracks().forEach(track => track.stop());
      window.probePeer?.close();
      await window.probeAudio?.close();
      window.probe.replies = [];
      await fetch("/api/voice/realtime", {method:"DELETE", credentials:"same-origin"});
    }).catch(() => {});
    await browser.close();
  }
})();
