// Headless integration adapter for Kim's UI. No markup, styles or credentials.
export class VoiceAudioClient {
  constructor({base = "", onState = () => {}, onTranscript = () => {}} = {}) {
    this.base = base;
    this.onState = onState;
    this.onTranscript = onTranscript;
    this.consent = false;
    this.recorder = null;
    this.stream = null;
    this.playback = null;
    this.playbackUrl = null;
    this.pending = null;
    this.timer = null;
    this.generation = 0;
    this.sessionActive = false;
  }

  // The product UI must disclose audio upload and AI-generated speech first.
  setAudioConsent(value) {
    this.consent = value === true;
    if (!this.consent) this.interrupt();
  }

  async request(path, options = {}, audio = false) {
    const result = await fetch(this.base + path, {
      credentials: "same-origin", ...options,
      headers: {...options.headers, ...(audio ? {"X-Audio-Consent":"1"} : {})},
    });
    if (!result.ok) throw new Error(`voice_http_${result.status}`);
    return result;
  }

  async startSession(language = "vi") {
    if (!["vi", "en"].includes(language)) throw new Error("unsupported_language");
    this.interrupt();
    this.sessionActive = false;
    const generation = this.generation;
    const response = await this.request(`/api/voice/session?language=${language}`, {method:"POST"});
    const result = await response.json();
    if (generation !== this.generation) throw new Error("session_cancelled");
    this.sessionActive = true;
    return result;
  }

  async turn(text, language) {
    if (!this.sessionActive) throw new Error("session_required");
    this.interrupt();
    const result = await this.request("/api/voice/turn", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text, ...(language ? {language} : {})}),
    });
    return result.json();
  }

  interrupt() {
    this.generation += 1;
    clearTimeout(this.timer);
    if (this.recorder) {
      this.recorder.onstop = null;
      this.recorder.ondataavailable = null;
      if (this.recorder.state !== "inactive") this.recorder.stop();
      this.recorder = null;
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.pending?.abort();
    this.pending = null;
    this.playback?.pause();
    this.playback = null;
    if (this.playbackUrl) URL.revokeObjectURL(this.playbackUrl);
    this.playbackUrl = null;
    this.onState("idle");
  }

  async startRecording() {
    if (!this.consent) throw new Error("audio_consent_required");
    if (!this.sessionActive) throw new Error("session_required");
    if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) throw new Error("recording_unavailable");
    this.interrupt(); // Barge-in stops queued output before opening the microphone.
    const generation = this.generation;
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    if (generation !== this.generation) { stream.getTracks().forEach((track) => track.stop()); return; }
    this.stream = stream;
    const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find((type) => MediaRecorder.isTypeSupported(type));
    if (!mimeType) { this.interrupt(); throw new Error("recording_format_unavailable"); }
    const chunks = [];
    let bytes = 0;
    try {
      this.recorder = new MediaRecorder(stream, {mimeType, audioBitsPerSecond:64000});
      this.recorder.ondataavailable = (event) => {
        bytes += event.data.size;
        if (bytes > 2 * 1024 * 1024) { this.interrupt(); this.onState("audio_too_large"); return; }
        chunks.push(event.data);
      };
      this.recorder.onerror = () => { this.interrupt(); this.onState("recording_error"); };
      this.recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        this.stream = null;
        this.recorder = null;
        clearTimeout(this.timer);
        if (generation !== this.generation || !this.consent) return;
        const controller = new AbortController();
        this.pending = controller;
        try {
          this.onState("transcribing");
          const blob = new Blob(chunks, {type:mimeType});
          const response = await this.request("/api/voice/transcribe", {
            method:"POST", headers:{"Content-Type":mimeType}, body:blob, signal:controller.signal,
          }, true);
          const transcript = await response.json();
          if (generation === this.generation && this.consent) {
            this.onTranscript(transcript); // UI confirmation required; no automatic turn.
            this.onState("awaiting_transcript_confirmation");
          }
        } catch (error) {
          if (generation === this.generation) this.onState(error.name === "AbortError" ? "idle" : "transcription_error");
        } finally {
          if (this.pending === controller) this.pending = null;
        }
      };
      this.recorder.start(250);
      this.timer = setTimeout(() => this.stopRecording(), 20000);
      this.onState("listening");
    } catch (error) { this.interrupt(); throw error; }
  }

  stopRecording() {
    clearTimeout(this.timer);
    if (this.recorder?.state === "recording") this.recorder.stop();
  }

  async readReply() {
    if (!this.consent) throw new Error("audio_consent_required");
    if (!this.sessionActive) throw new Error("session_required");
    this.interrupt();
    const generation = this.generation;
    const controller = new AbortController();
    this.pending = controller;
    try {
      this.onState("loading_speech");
      const result = await this.request("/api/voice/speech", {method:"POST", signal:controller.signal}, true);
      const blob = await result.blob();
      if (generation !== this.generation || !this.consent) return;
      this.playbackUrl = URL.createObjectURL(blob);
      const player = new Audio(this.playbackUrl);
      this.playback = player;
      player.onended = () => { if (generation === this.generation) this.interrupt(); };
      player.onerror = () => { if (generation === this.generation) { this.interrupt(); this.onState("playback_error"); } };
      await player.play();
      if (generation === this.generation && this.consent) this.onState("speaking");
    } catch (error) {
      if (generation === this.generation) { this.interrupt(); this.onState("speech_error"); }
      throw error;
    } finally {
      if (this.pending === controller) this.pending = null;
    }
  }

  async endSession() {
    this.interrupt();
    this.sessionActive = false;
    await this.request("/api/voice/session", {method:"DELETE"});
    this.onState("ended");
  }
}
