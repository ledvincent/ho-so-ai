"""Optional audio transport. No free-form generated answers or personal tools."""
import json
import os

MAX_AUDIO_INPUT = 2 * 1024 * 1024
MAX_AUDIO_OUTPUT = 4 * 1024 * 1024


class SpeechUnavailable(Exception):
    """Sanitized failure; never expose provider bodies, keys or transcriptions."""


class DisabledSpeech:
    enabled = False


def audio_extension(body: bytes, content_type: str):
    checks = {
        "audio/webm": ("webm", body.startswith(bytes.fromhex("1a45dfa3"))),
        "audio/ogg": ("ogg", body.startswith(b"OggS")),
        "audio/wav": ("wav", body.startswith(b"RIFF") and body[8:12] == b"WAVE"),
        "audio/mp4": ("mp4", body[4:8] == b"ftyp"),
        "audio/mpeg": ("mp3", body.startswith(b"ID3") or (len(body) > 1 and body[0] == 255 and body[1] & 224 == 224)),
    }
    extension, valid = checks.get(content_type, (None, False))
    if not valid:
        raise ValueError("invalid_audio")
    return extension


class OpenAISpeech:
    enabled = True

    def __init__(self, api_key, *, transcription_model="gpt-4o-mini-transcribe", speech_model="gpt-4o-mini-tts", transport=None):
        self._api_key = api_key
        self.transcription_model = transcription_model
        self.speech_model = speech_model
        self.transport = transport

    async def _post(self, path, max_bytes, **kwargs):
        import httpx  # Optional `audio` extra; never required for offline dialogue.

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False, transport=self.transport) as client:
                async with client.stream("POST", "https://api.openai.com/v1/audio/" + path,
                                         headers={"Authorization": "Bearer " + self._api_key}, **kwargs) as result:
                    if result.status_code != 200:
                        raise SpeechUnavailable()
                    body = bytearray()
                    async for chunk in result.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise SpeechUnavailable()
                    return bytes(body)
        except httpx.HTTPError:
            raise SpeechUnavailable() from None

    async def transcribe(self, body, content_type, language):
        extension = audio_extension(body, content_type)
        raw = await self._post("transcriptions", 64 * 1024,
                               files={"file": ("utterance." + extension, body, content_type)},
                               data={"model": self.transcription_model, "language": language, "response_format": "json"})
        try:
            text = json.loads(raw)["text"]
            if not isinstance(text, str) or not text.strip() or len(text) > 600:
                raise ValueError()
            return text.strip()
        except (ValueError, KeyError, TypeError):
            raise SpeechUnavailable() from None

    async def speak(self, text, language):
        # The caller supplies only the latest server-owned canned reply, never
        # arbitrary client text, retrieved HTML, or generated legal statements.
        instructions = "Read the supplied text clearly and calmly in " + ("Vietnamese." if language == "vi" else "English.")
        body = await self._post("speech", MAX_AUDIO_OUTPUT,
                                json={"model": self.speech_model, "voice": "coral", "input": text,
                                      "instructions": instructions, "response_format": "mp3"})
        try:
            audio_extension(body, "audio/mpeg")
        except ValueError:
            raise SpeechUnavailable() from None
        return body


def configured_speech():
    # An explicit flag AND a server key are required; importing the app never
    # contacts a provider and does not implicitly enable paid audio requests.
    key = os.getenv("OPENAI_API_KEY")
    if os.getenv("VOICE_ENABLE_AUDIO_API") != "1" or not key:
        return DisabledSpeech()
    return OpenAISpeech(key, transcription_model=os.getenv("VOICE_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
                        speech_model=os.getenv("VOICE_TTS_MODEL", "gpt-4o-mini-tts"))
