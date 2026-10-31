"""Standalone local voice demo. Vincent/Kim integrations are deliberately absent."""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .languages import Language, SPEECH_LANGUAGES, response as dialogue_response
from .sessions import AudioLimit, CapacityReached, MissingSession, PublicSessions, TurnLimit
from .speech import MAX_AUDIO_INPUT, SpeechUnavailable, audio_extension, configured_speech

STATIC = Path(__file__).parent / "static"
COOKIE = "hoso_public_voice"
MAX_BODY = 4096


class TurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=600, strict=True)
    language: Language | None = None


def create_app(*, sessions=None, allowed_origins=None, secure_cookie=False, speech=None):
    store = sessions if sessions is not None else PublicSessions()
    audio = speech if speech is not None else configured_speech()
    origins = frozenset(allowed_origins or {"http://127.0.0.1:8000", "http://localhost:8000"})
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.method in {"POST", "DELETE"} and request.headers.get("origin") not in origins:
            return JSONResponse({"error": "origin_denied"}, status_code=403)
        response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "Permissions-Policy": "microphone=(self), camera=(), geolocation=()",
        })
        return response

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/voice.js")
    def javascript():
        return FileResponse(STATIC / "voice.js", media_type="application/javascript")

    @app.get("/voice.css")
    def css():
        return FileResponse(STATIC / "voice.css", media_type="text/css")

    @app.get("/audio-client.js")
    def audio_client():
        return FileResponse(STATIC / "audio-client.js", media_type="application/javascript")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "public_dialogue_demo", "reviewed_lookup_available": False,
                "personal_tools_enabled": False, "audio_api_enabled": audio.enabled}

    @app.get("/api/voice/capabilities")
    def capabilities():
        return {"languages": SPEECH_LANGUAGES, "audio_api_enabled": audio.enabled,
                "audio_disclosure_required": True, "transcript_confirmation_required": True,
                "max_audio_bytes": MAX_AUDIO_INPUT, "personal_tools_enabled": False}

    @app.post("/api/voice/session")
    def start(request: Request):
        language = request.query_params.get("language", "vi")
        if language not in SPEECH_LANGUAGES:
            raise HTTPException(422, detail="unsupported_language")
        try:
            token = store.create(request.cookies.get(COOKIE), language=language)
        except CapacityReached:
            raise HTTPException(503, detail="session_capacity") from None
        response = JSONResponse({**dialogue_response(language, "welcome", "welcome", with_choices=True), "expires_in": store.ttl})
        response.set_cookie(COOKIE, token, max_age=store.ttl, httponly=True, secure=secure_cookie, samesite="strict", path="/api/voice")
        return response

    @app.post("/api/voice/turn")
    async def turn(request: Request):
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
            raise HTTPException(415, detail="json_required")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                raise HTTPException(413, detail="input_too_large")
        try:
            data = json.loads(body)
            parsed = TurnInput.model_validate(data)
        except (ValueError, ValidationError):
            # Framework validation defaults can echo raw user input. Never do so.
            raise HTTPException(422, detail="invalid_input") from None
        try:
            return store.turn(request.cookies.get(COOKIE), parsed.text, parsed.language)
        except MissingSession:
            raise HTTPException(401, detail="public_session_expired") from None
        except TurnLimit:
            raise HTTPException(429, detail="turn_limit") from None

    async def audio_request(request, operation):
        token = request.cookies.get(COOKIE)
        if request.headers.get("x-audio-consent") != "1":
            raise HTTPException(403, detail="audio_consent_required")
        if not audio.enabled:
            raise HTTPException(503, detail="audio_not_configured")
        try:
            language, reply = store.audio_begin(token)
        except MissingSession:
            raise HTTPException(401, detail="public_session_expired") from None
        except AudioLimit:
            raise HTTPException(429, detail="audio_limit") from None
        try:
            if operation == "transcribe":
                content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > MAX_AUDIO_INPUT:
                        raise HTTPException(413, detail="audio_too_large")
                try:
                    audio_extension(body, content_type)
                except ValueError:
                    raise HTTPException(415, detail="invalid_audio") from None
                text = await audio.transcribe(bytes(body), content_type, language)
                # Transcription is untrusted. It does not advance state or run a
                # tool until the user confirms it through the normal turn route.
                return JSONResponse({"text": text, "language": language, "requires_confirmation": True})
            # No user-supplied text accepted by the speech endpoint.
            async for chunk in request.stream():
                if chunk:
                    raise HTTPException(422, detail="speech_body_not_allowed")
            body = await audio.speak(reply, language)
            return Response(body, media_type="audio/mpeg", headers={"X-AI-Generated-Audio": "true"})
        except SpeechUnavailable:
            raise HTTPException(503, detail="audio_provider_unavailable") from None
        finally:
            # Expiration/end while an upstream request is pending invalidates
            # the response; revocation cannot unsend previously uploaded audio.
            try:
                store.audio_end(token)
            except MissingSession:
                raise HTTPException(401, detail="public_session_expired") from None

    @app.post("/api/voice/transcribe")
    async def transcribe(request: Request):
        return await audio_request(request, "transcribe")

    @app.post("/api/voice/speech")
    async def speech_reply(request: Request):
        return await audio_request(request, "speech")

    @app.delete("/api/voice/session")
    def end(request: Request):
        store.end(request.cookies.get(COOKIE))
        response = JSONResponse({"state": "ended"})
        response.delete_cookie(COOKIE, path="/api/voice", secure=secure_cookie, httponly=True, samesite="strict")
        return response

    return app


app = create_app(
    allowed_origins=set(filter(None, os.getenv("VOICE_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(","))),
    secure_cookie=os.getenv("VOICE_SECURE_COOKIE") == "1",
)
