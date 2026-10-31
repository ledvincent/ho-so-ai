"use strict";
// The existing layout is a technical test harness, not Kim's product UI.
if (new URLSearchParams(location.search).get("audio") === "realtime") {
  realtimeHarness();
} else if (new URLSearchParams(location.search).get("audio") === "openai") {
  openAIHarness();
} else {
  browserHarness();
}

function browserHarness() {
const $ = (id) => document.getElementById(id);
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let ready = false;
let busy = false;
let listening = false;
let recognition = null;
let generation = 0;

function controls() {
  $("send").disabled = !ready || busy || listening;
  $("utterance").disabled = busy || listening;
  $("microphone").disabled = !ready || busy || !Recognition || !$("audio-consent").checked;
  $("microphone").classList.toggle("listening", listening);
  $("microphone").textContent = listening ? "Dừng nghe" : "Nói bằng giọng nói";
  for (const button of $("choices").querySelectorAll("button")) button.disabled = !ready || busy || listening;
}

function message(content, kind = "assistant") {
  const element = document.createElement("p");
  element.className = `message ${kind}`;
  element.textContent = content;
  $("messages").appendChild(element);
  element.scrollIntoView({block:"nearest"});
}

function speak(content) {
  if (!$("read-aloud").checked || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(content);
  utterance.lang = "vi-VN";
  const voice = window.speechSynthesis.getVoices().find((item) => item.lang.startsWith("vi"));
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function render(response, read = true) {
  message(response.reply);
  $("choices").replaceChildren();
  for (const choice of response.choices || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = choice.label;
    button.addEventListener("click", () => submit(choice.text));
    $("choices").appendChild(button);
  }
  const names = {"1.004194":"Đăng ký tạm trú", "1.002755":"Gia hạn tạm trú"};
  $("candidate-title").textContent = names[response.candidate_code] || "Mình cùng làm rõ.";
  $("candidate-description").textContent = response.candidate_code
    ? `Nhu cầu dự kiến · ${response.candidate_code}. Chưa phải kết quả thủ tục đã được xác thực; đang chờ dữ liệu đã duyệt.`
    : "Chưa chọn thủ tục. Trợ lý sẽ hỏi lại khi chưa rõ nhu cầu.";
  if (read) speak(response.reply);
}

async function api(path, options = {}) {
  const response = await fetch(path, {credentials:"same-origin", ...options});
  if (response.status === 401) {
    ready = false;
    throw new Error("Cuộc hội thoại đã hết hạn. Chọn Bắt đầu lại để tiếp tục.");
  }
  if (!response.ok) {
    const messages = {429:"Đã đạt giới hạn lượt nói. Chọn Bắt đầu lại.", 413:"Nội dung quá dài. Vui lòng rút ngắn.", 503:"Bản thử nghiệm đang bận. Vui lòng thử lại."};
    throw new Error(messages[response.status] || "Không thể kết nối. Vui lòng thử lại.");
  }
  return response.json();
}

async function start() {
  if (busy) return;
  generation += 1;
  stopAudio();
  busy = true;
  ready = false;
  controls();
  $("messages").replaceChildren();
  $("choices").replaceChildren();
  $("utterance").value = "";
  try {
    const response = await api("/api/voice/session", {method:"POST"});
    ready = true;
    render(response, false);
    $("status").textContent = Recognition ? "Sẵn sàng. Bạn có thể nói hoặc nhập nội dung." : "Trình duyệt chưa hỗ trợ nhận dạng giọng nói. Bạn vẫn có thể nhập nội dung.";
  } catch (error) {
    message(error.message, "error");
    $("status").textContent = "Chọn Bắt đầu lại để kết nối.";
  } finally {
    busy = false;
    controls();
  }
}

async function submit(content) {
  content = content.trim();
  if (!content || busy || !ready || listening) return;
  if (content.length > 600) {
    $("status").textContent = "Vui lòng nhập tối đa 600 ký tự.";
    return;
  }
  busy = true;
  window.speechSynthesis?.cancel();
  controls();
  message(content, "user");
  $("utterance").value = "";
  $("status").textContent = "Đang làm rõ nhu cầu…";
  try {
    render(await api("/api/voice/turn", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:content})}));
    $("status").textContent = "Bạn có thể tiếp tục nói hoặc nhập nội dung.";
  } catch (error) {
    message(error.message, "error");
    $("status").textContent = error.message;
  } finally {
    busy = false;
    controls();
  }
}

function stopAudio() {
  if (recognition) {
    recognition.onresult = null;
    recognition.onend = null;
    recognition.onerror = null;
    recognition.abort();
    recognition = null;
  }
  listening = false;
  window.speechSynthesis?.cancel();
}

$("composer").addEventListener("submit", (event) => { event.preventDefault(); submit($("utterance").value); });
$("restart").addEventListener("click", start);
$("audio-consent").addEventListener("change", () => {
  if (!$("audio-consent").checked) stopAudio();
  controls();
});
$("read-aloud").addEventListener("change", () => { if (!$("read-aloud").checked) window.speechSynthesis?.cancel(); });
$("microphone").addEventListener("click", () => {
  if (listening) { recognition?.stop(); return; }
  if (!Recognition || !ready || busy || !$("audio-consent").checked) return;
  window.speechSynthesis?.cancel();
  const current = generation;
  const active = new Recognition();
  recognition = active;
  active.lang = "vi-VN";
  active.interimResults = false;
  active.continuous = false;
  listening = true;
  controls();
  $("status").textContent = "Đang nghe… Chỉ mô tả nhu cầu, không đọc thông tin cá nhân.";
  active.onresult = (event) => {
    if (current !== generation) return;
    // Let the user check recognition before sending; no automatic legal action.
    $("utterance").value = event.results[0][0].transcript.slice(0, 600);
    $("status").textContent = "Kiểm tra nội dung vừa nghe, rồi chọn Gửi.";
  };
  active.onerror = (event) => {
    const messages = {"not-allowed":"Chưa có quyền dùng mic. Cho phép mic hoặc nhập nội dung.", "no-speech":"Chưa nghe rõ. Hãy thử lại hoặc nhập nội dung.", "network":"Dịch vụ giọng nói chưa kết nối. Bạn có thể nhập nội dung."};
    $("status").textContent = messages[event.error] || "Không thể nhận dạng giọng nói. Bạn có thể nhập nội dung.";
  };
  active.onend = () => {
    if (recognition === active) recognition = null;
    listening = false;
    controls();
    $("utterance").focus();
  };
  try { active.start(); } catch {
    stopAudio();
    controls();
    $("status").textContent = "Không thể mở mic. Bạn có thể nhập nội dung.";
  }
});
window.addEventListener("pagehide", () => {
  stopAudio();
  fetch("/api/voice/session", {method:"DELETE", credentials:"same-origin", keepalive:true}).catch(() => {});
});
start();
}

async function openAIHarness() {
  const $ = (id) => document.getElementById(id);
  const language = new URLSearchParams(location.search).get("language") === "en" ? "en" : "vi";
  const en = language === "en";
  let client, ready = false, busy = false, listening = false, transcribing = false, available = false;
  const stateText = {
    idle: en ? "Ready. Use only synthetic demo needs." : "Sẵn sàng. Chỉ dùng nhu cầu giả định để thử.",
    listening: en ? "Listening… Press Stop when finished." : "Đang ghi âm… Chọn Dừng khi nói xong.",
    transcribing: en ? "Transcribing with OpenAI…" : "Đang nhận dạng bằng OpenAI…",
    awaiting_transcript_confirmation: en ? "Check the recognized text, then press Send." : "Kiểm tra nội dung nhận dạng rồi chọn Gửi.",
    loading_speech: en ? "Generating the AI voice…" : "Đang tạo giọng nói AI…",
    speaking: en ? "Playing the AI-generated voice. Recording will interrupt it." : "Đang phát giọng nói AI. Bắt đầu ghi âm để ngắt lời.",
    recording_error: en ? "Microphone error. Try typing instead." : "Không ghi âm được. Bạn có thể nhập nội dung.",
    transcription_error: en ? "Transcription failed. Check the API account or use text." : "Nhận dạng không thành công. Kiểm tra tài khoản API hoặc nhập nội dung.",
    speech_error: en ? "Audio failed. Check model access/credits and try again." : "Tạo âm thanh thất bại. Kiểm tra quyền dùng model/số dư API rồi thử lại.",
    playback_error: en ? "Playback failed. Try enabling Read aloud again." : "Không phát được âm thanh. Thử bật lại Đọc câu trả lời.",
    audio_too_large: en ? "Recording is too large. Please record a shorter request." : "Ghi âm quá dài. Hãy ghi một câu ngắn hơn.",
  };
  const consent = $("audio-consent");
  const read = $("read-aloud");
  const input = $("utterance");
  function controls() {
    $("send").disabled = !ready || busy || listening || transcribing;
    input.disabled = busy || listening || transcribing;
    $("microphone").disabled = !ready || busy || transcribing || !available || !consent.checked || !navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder;
    $("microphone").classList.toggle("listening", listening);
    $("microphone").textContent = listening ? (en ? "Stop recording" : "Dừng ghi âm") : (en ? "Record with OpenAI" : "Ghi âm với OpenAI");
    read.disabled = !ready || !available || !consent.checked;
    for (const button of $("choices").querySelectorAll("button")) button.disabled = !ready || busy || listening || transcribing;
  }
  function message(text, kind = "assistant") {
    const element = document.createElement("p");
    element.className = "message " + kind;
    element.textContent = text;
    $("messages").appendChild(element);
    element.scrollIntoView({block:"nearest"});
  }
  function failure(error) {
    if (error.name === "AbortError") return;
    if (error.message === "voice_http_401") ready = false;
    $("status").textContent = error.message === "voice_http_401"
      ? (en ? "Session expired. Press Restart." : "Phiên đã hết hạn. Chọn Bắt đầu lại.")
      : (en ? "Audio unavailable. Check microphone permission, API credits/model access, or try text." : "Âm thanh chưa khả dụng. Kiểm tra quyền micro, số dư/quyền model API hoặc nhập nội dung.");
    controls();
  }
  function play() {
    if (read.checked && consent.checked && ready) client.readReply().catch(failure);
  }
  function render(response) {
    message(response.reply);
    $("choices").replaceChildren();
    for (const choice of response.choices || []) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = choice.label;
      button.onclick = () => submit(choice.text);
      $("choices").appendChild(button);
    }
    const names = en ? {"1.004194":"Register temporary residence", "1.002755":"Renew temporary residence"} : {"1.004194":"Đăng ký tạm trú", "1.002755":"Gia hạn tạm trú"};
    $("candidate-title").textContent = names[response.candidate_code] || (en ? "Let's clarify your need." : "Mình cùng làm rõ.");
    $("candidate-description").textContent = en
      ? "Intent routing only. Reviewed official data is not connected yet."
      : "Chỉ định hướng nhu cầu. Dữ liệu chính thức đã duyệt chưa được kết nối.";
    controls();
  }
  async function submit(text) {
    if (!ready || busy || listening || transcribing || !text.trim()) return;
    busy = true;
    controls();
    message(text.trim(), "user");
    input.value = "";
    let success = false;
    try { render(await client.turn(text.trim(), language)); success = true; } catch (error) { failure(error); }
    finally { busy = false; controls(); }
    if (success) play();
  }
  async function start() {
    if (busy || !client) return;
    ready = false;
    busy = true;
    controls();
    $("messages").replaceChildren();
    $("choices").replaceChildren();
    input.value = "";
    try {
      const capabilities = await fetch("/api/voice/capabilities").then((result) => result.json());
      available = capabilities.audio_api_enabled;
      const welcome = await client.startSession(language);
      client.setAudioConsent(consent.checked);
      ready = true;
      render(welcome);
      $("status").textContent = available
        ? (en ? "OpenAI is enabled. Accept audio processing, then enable Read aloud to hear the greeting." : "OpenAI đã bật. Đồng ý xử lý âm thanh rồi bật Đọc câu trả lời để nghe lời chào.")
        : (en ? "OpenAI audio is not configured on this server. Text still works." : "Máy chủ chưa cấu hình âm thanh OpenAI. Bạn vẫn có thể nhập nội dung.");
    } catch (error) { failure(error); }
    finally { busy = false; controls(); }
  }
  document.querySelector(".session-heading h2").textContent = en ? "OpenAI audio test · English" : "Thử âm thanh OpenAI · Tiếng Việt";
  consent.parentElement.lastChild.textContent = en
    ? " I agree to send demo audio to OpenAI and hear an AI-generated voice. API requests may incur charges. Do not use personal data."
    : " Tôi đồng ý gửi âm thanh thử nghiệm đến OpenAI và nghe giọng nói do AI tạo. Yêu cầu API có thể mất phí. Không dùng dữ liệu cá nhân.";
  if (en) {
    document.documentElement.lang = "en";
    $("send").textContent = "Send";
    $("send").setAttribute("aria-label", "Send");
    $("restart").textContent = "Restart";
    document.querySelector("label[for=utterance]").textContent = "Type or check your request";
    input.placeholder = "Example: I want to renew temporary residence";
    read.parentElement.lastChild.textContent = " Read aloud";
  }
  controls();
  try {
    const {VoiceAudioClient} = await import("/audio-client.js");
    client = new VoiceAudioClient({
      onState(state) {
        listening = state === "listening";
        transcribing = state === "transcribing";
        if (stateText[state]) $("status").textContent = stateText[state];
        controls();
      },
      onTranscript(transcript) { input.value = transcript.text; input.focus(); },
    });
    $("composer").onsubmit = (event) => { event.preventDefault(); submit(input.value); };
    $("restart").onclick = start;
    consent.onchange = () => { client.setAudioConsent(consent.checked); if (!consent.checked) read.checked = false; controls(); };
    read.onchange = () => { if (read.checked) play(); else client.interrupt(); };
    $("microphone").onclick = () => { if (listening) client.stopRecording(); else client.startRecording().catch(failure); };
    window.addEventListener("pagehide", () => {
      client.interrupt();
      fetch("/api/voice/session", {method:"DELETE", credentials:"same-origin", keepalive:true}).catch(() => {});
    });
    await start();
  } catch (error) { failure(error); }
}

async function realtimeHarness() {
  const $ = (id) => document.getElementById(id);
  const language = new URLSearchParams(location.search).get("language") === "en" ? "en" : "vi";
  const en = language === "en";
  const ragMode = new URLSearchParams(location.search).get("documents") === "rag";
  const consent = $("audio-consent");
  const call = $("microphone");
  let client, active = false, blocked = false;
  $("composer").hidden = true;
  $("choices").hidden = true;
  document.querySelector(".read-toggle").hidden = true;
  $("restart").hidden = true;
  document.querySelector(".session-heading h2").textContent = en ? "Live voice call · English" : "Cuộc gọi trực tiếp · Tiếng Việt";
  $("candidate-title").textContent = en ? "Just talk." : "Bạn cứ nói nhé.";
  $("candidate-description").textContent = en ? "No recording or Send button. You can interrupt the agent. Official data is not connected." : "Không cần ghi âm rồi gửi. Bạn có thể ngắt lời trợ lý. Dữ liệu chính thức chưa được kết nối.";
  if (ragMode) $("candidate-description").textContent = en
    ? "Live document backend selected. Describe your goal; the agent will clarify it. Sources appear below each lookup."
    : "Đã chọn kết nối kho tài liệu thật. Hãy nói nhu cầu để trợ lý hỏi rõ. Nguồn xuất hiện sau mỗi lần tra cứu.";
  consent.parentElement.lastChild.textContent = en
    ? " I agree to a live AI call: microphone audio and connection data go to OpenAI while connected. Calls may incur charges. Use fictional needs, no personal data."
    : " Tôi đồng ý gọi AI trực tiếp: âm thanh micro và dữ liệu kết nối được gửi đến OpenAI khi đang gọi. Có thể mất phí. Chỉ thử nhu cầu giả định, không dùng dữ liệu cá nhân.";
  const messages = {
    connecting: en ? "Connecting… Allow microphone access." : "Đang kết nối… Hãy cho phép dùng micro.",
    listening: en ? "Call connected. Speak naturally; the agent will answer when you finish." : "Đã kết nối. Bạn cứ nói tự nhiên, trợ lý sẽ trả lời khi bạn nói xong.",
    hearing: en ? "Listening to you…" : "Đang nghe bạn…",
    thinking: en ? "The agent is responding…" : "Trợ lý đang trả lời…",
    speaking: en ? "The agent is speaking. You can interrupt by talking." : "Trợ lý đang nói. Bạn có thể ngắt lời bằng cách nói.",
    ended: en ? "Call ended. Microphone released." : "Đã kết thúc. Micro đã tắt.",
    connection_error: en ? "Call failed. Check microphone permission, Realtime model access and API credits." : "Không gọi được. Kiểm tra quyền micro, quyền model Realtime và số dư API.",
    audio_blocked: en ? "Tap Enable sound to hear the call." : "Chọn Bật âm thanh để nghe cuộc gọi.",
    reconnecting: en ? "Audio connection interrupted; waiting briefly…" : "Kết nối âm thanh bị gián đoạn; đang chờ…",
    microphone_denied: en ? "Microphone permission denied. Allow it in your browser, then start again." : "Quyền micro bị từ chối. Cho phép trong trình duyệt rồi gọi lại.",
    microphone_missing: en ? "No microphone found. Connect one, then start again." : "Không tìm thấy micro. Kết nối micro rồi gọi lại.",
    microphone_busy: en ? "Microphone unavailable. Check other apps, then start again." : "Không dùng được micro. Kiểm tra ứng dụng khác rồi gọi lại.",
  };
  function controls() {
    call.disabled = !client || (!active && !consent.checked);
    call.textContent = blocked ? (en ? "Enable sound" : "Bật âm thanh") : active ? (en ? "End call" : "Kết thúc cuộc gọi") : (en ? "Start voice call" : "Bắt đầu cuộc gọi");
    call.classList.toggle("listening", active);
    $("restart").hidden = !active;
    $("restart").textContent = en ? "End call" : "Kết thúc";
  }
  controls();
  try {
    const capabilities = await fetch("/api/voice/capabilities").then((result) => result.json());
    if (!capabilities.realtime_available) {
      $("status").textContent = en ? "Restart the private server to load the new Realtime backend." : "Khởi động lại máy chủ riêng để nạp chế độ Realtime mới.";
      return;
    }
    const {RealtimeVoiceClient} = await import("/realtime-client.js");
    client = new RealtimeVoiceClient({
      onState(state) {
        if (["ended", "connection_error", "microphone_denied", "microphone_missing", "microphone_busy"].includes(state)) { active = false; blocked = false; }
        if (state === "audio_blocked") blocked = true;
        if (messages[state]) $("status").textContent = blocked ? messages.audio_blocked : messages[state];
        controls();
      },
      onTranscript(text, metadata) {
        const element = document.createElement("p");
        element.className = "message";
        element.textContent = text;
        if (metadata?.kind === "source") {
          try {
            const url = new URL(metadata.source.url);
            if (["https:", "http:"].includes(url.protocol) && !url.username && !url.password) {
              const link = document.createElement("a");
              link.textContent = text;
              link.href = url.href;
              link.target = "_blank";
              link.rel = "noopener noreferrer";
              element.replaceChildren(link);
            }
          } catch {}
        }
        $("messages").appendChild(element);
        element.scrollIntoView({block:"nearest"});
      },
      onError({code}) {
        const descriptions = {
          privacy_rephrase_required: en ? "Please ask a general question without personal details." : "Vui lòng hỏi chung, không kèm thông tin cá nhân.",
          rag_http_409: en ? "Document context expired. Please describe your goal again." : "Ngữ cảnh tài liệu đã hết hạn. Vui lòng nói lại nhu cầu.",
          rag_timeout: en ? "The document check timed out. You can ask to retry." : "Tra cứu quá thời gian. Bạn có thể yêu cầu thử lại.",
          response_truncated: en ? "The spoken response was incomplete. Ask the agent to continue." : "Câu trả lời chưa hoàn tất. Bạn có thể yêu cầu nói tiếp.",
        };
        if (messages[code]) return;
        const element = document.createElement("p");
        element.className = "message error";
        element.textContent = descriptions[code] || (en ? "This turn could not be completed. No verified answer is available; try again or restart the call." : "Chưa hoàn tất lượt này. Chưa có câu trả lời được xác minh; thử lại hoặc gọi lại.");
        $("messages").appendChild(element);
      },
    });
    call.onclick = async () => {
      if (blocked) {
        try { await client.resumeAudio(); blocked = false; $("status").textContent = messages.listening; controls(); }
        catch { $("status").textContent = messages.audio_blocked; }
        return;
      }
      if (active) { await client.stop(); return; }
      active = true;
      $("messages").replaceChildren();
      controls();
      try { await client.start({language, consent:consent.checked, fixtureDocuments:new URLSearchParams(location.search).get("documents") === "fixture", ragDocuments:new URLSearchParams(location.search).get("documents") === "rag"}); }
      catch { active = false; controls(); }
    };
    $("restart").onclick = () => client.stop();
    consent.onchange = () => { if (!consent.checked) client.stop(); controls(); };
    window.addEventListener("pagehide", () => client.stop());
    $("status").textContent = en ? "Accept the disclosure, then Start voice call. No audio is sent before you start." : "Đồng ý thông báo rồi chọn Bắt đầu cuộc gọi. Chưa gửi âm thanh trước khi bắt đầu.";
    if (new URLSearchParams(location.search).get("documents") === "fixture") $("status").textContent += en ? " Fictional document API test; no legal advice." : " Thử API tài liệu giả lập; không phải tư vấn pháp lý.";
    controls();
  } catch {
    $("status").textContent = messages.connection_error;
  }
}
