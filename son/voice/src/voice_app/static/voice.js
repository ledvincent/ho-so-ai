"use strict";
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
