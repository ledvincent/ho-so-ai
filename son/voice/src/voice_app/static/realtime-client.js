// Full-duplex WebRTC call adapter. No MediaRecorder, Send button or browser API key.
export class RealtimeVoiceClient {
  constructor({onState = () => {}, onTranscript = () => {}, onDiagnostic = () => {}} = {}) {
    this.onState = onState;
    this.onTranscript = onTranscript;
    this.onDiagnostic = onDiagnostic;
    this.version = 0;
    this.peer = null;
    this.channel = null;
    this.stream = null;
    this.audio = null;
    this.pending = null;
    this.timer = null;
  }

  async start({language = "vi", consent = false} = {}) {
    if (!consent) throw new Error("audio_consent_required");
    if (!["vi", "en"].includes(language)) throw new Error("unsupported_language");
    if (!globalThis.RTCPeerConnection || !navigator.mediaDevices?.getUserMedia) throw new Error("webrtc_unavailable");
    await this.stop(false);
    const version = ++this.version;
    const controller = new AbortController();
    this.pending = controller;
    this.onState("connecting");
    try {
      const session = await fetch(`/api/voice/session?language=${language}`, {method:"POST", credentials:"same-origin", signal:controller.signal});
      if (!session.ok) throw new Error(`voice_http_${session.status}`);
      const stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
      if (version !== this.version) { stream.getTracks().forEach((track) => track.stop()); return; }
      this.stream = stream;
      const peer = new RTCPeerConnection();
      this.peer = peer;
      const audio = new Audio();
      audio.autoplay = true;
      this.audio = audio;
      peer.ontrack = (event) => {
        if (version !== this.version) return;
        audio.srcObject = event.streams[0];
        audio.play().catch(() => { if (version === this.version) this.onState("audio_blocked"); });
      };
      peer.onconnectionstatechange = () => {
        if (version !== this.version) return;
        if (peer.connectionState === "connected") this.onState("listening");
        if (["failed", "closed"].includes(peer.connectionState)) {
          this.stop(false).finally(() => this.onState("connection_error"));
        }
      };
      for (const track of stream.getAudioTracks()) peer.addTrack(track, stream);
      const channel = peer.createDataChannel("oai-events");
      this.channel = channel;
      let callerSpeaking = false;
      let playing = false;
      channel.onopen = () => {
        if (version !== this.version) return;
        this.onState("listening");
        // Also upgrades a running older backend without re-entering its key.
        // This changes only the bounded output allowance, not tools or access.
        channel.send(JSON.stringify({type:"session.update", session:{type:"realtime", max_output_tokens:2048}}));
        channel.send(JSON.stringify({type:"response.create", response:{instructions:
          language === "vi"
            ? "Chào ngắn gọn bằng tiếng Việt, giới thiệu bạn là trợ lý giọng nói AI và hỏi người gọi cần hỗ trợ điều gì. Không nói thông tin pháp lý."
            : "Briefly greet the caller in English, introduce yourself as an AI voice assistant, and ask what they need help with. Give no legal facts."}}));
      };
      channel.onmessage = (event) => {
        if (version !== this.version || typeof event.data !== "string" || event.data.length > 65536) return;
        let data;
        try { data = JSON.parse(event.data); } catch { return; }
        if (data.type === "input_audio_buffer.speech_started") { callerSpeaking = true; this.onState("hearing"); }
        if (data.type === "input_audio_buffer.speech_stopped") { callerSpeaking = false; this.onState(playing ? "speaking" : "thinking"); }
        if (data.type === "response.created" && !callerSpeaking && !playing) this.onState("thinking");
        if (data.type === "output_audio_buffer.started") { playing = true; if (!callerSpeaking) this.onState("speaking"); }
        if (["output_audio_buffer.stopped", "output_audio_buffer.cleared"].includes(data.type)) {
          playing = false;
          this.onState(callerSpeaking ? "hearing" : "listening");
        }
        if (data.type === "response.done") {
          // Generation can finish before WebRTC has played the queued audio.
          // Never invite the next turn until output_audio_buffer.stopped.
          const allowedStatuses = ["completed", "cancelled", "failed", "incomplete"];
          const allowedReasons = ["max_output_tokens", "turn_detected", "client_cancelled", "content_filter"];
          const reason = data.response?.status_details?.reason;
          this.onDiagnostic({event:"response_done",
            status:allowedStatuses.includes(data.response?.status) ? data.response.status : "unknown",
            reason:allowedReasons.includes(reason) ? reason : null,
            outputTokens:Number.isInteger(data.response?.usage?.output_tokens) ? data.response.usage.output_tokens : null});
        }
        if (data.type === "response.output_audio_transcript.done" && typeof data.transcript === "string") this.onTranscript(data.transcript.slice(0, 2000));
        if (data.type === "error" && !["response_cancel_not_active", "conversation_already_has_active_response"].includes(data.error?.code)) {
          this.stop(false).finally(() => this.onState("connection_error"));
        }
      };
      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      const answer = await fetch("/api/voice/realtime", {
        method:"POST", credentials:"same-origin", signal:controller.signal,
        headers:{"Content-Type":"application/sdp", "X-Audio-Consent":"1"}, body:offer.sdp,
      });
      if (!answer.ok) throw new Error(`voice_http_${answer.status}`);
      const sdp = await answer.text();
      if (version !== this.version) return;
      await peer.setRemoteDescription({type:"answer", sdp});
      const seconds = Math.min(180, Math.max(1, Number(answer.headers.get("X-Call-Max-Seconds")) || 180));
      this.timer = setTimeout(() => this.stop().catch(() => {}), seconds * 1000);
      if (this.pending === controller) this.pending = null;
    } catch (error) {
      if (version === this.version) {
        await this.stop(false);
        this.onState(error.name === "AbortError" ? "ended" : "connection_error");
      }
      throw error;
    }
  }

  async resumeAudio() {
    if (this.audio) { await this.audio.play(); this.onState("listening"); }
  }

  async stop(notify = true) {
    this.version += 1;
    clearTimeout(this.timer);
    this.pending?.abort();
    this.pending = null;
    if (this.channel) { this.channel.onopen = null; this.channel.onmessage = null; this.channel.close(); this.channel = null; }
    if (this.peer) { this.peer.ontrack = null; this.peer.onconnectionstatechange = null; this.peer.close(); this.peer = null; }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.audio) { this.audio.pause(); this.audio.srcObject = null; this.audio = null; }
    if (notify) this.onState("ended");
    // No API credentials/call IDs in URLs or JS. The cookie selects the owner's call.
    await fetch("/api/voice/realtime", {method:"DELETE", credentials:"same-origin", keepalive:true}).catch(() => {});
  }
}
