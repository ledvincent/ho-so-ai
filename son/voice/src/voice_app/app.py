"""Standalone local voice demo. Vincent/Kim integrations are deliberately absent."""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .dialogue import CHOICES, WELCOME
from .sessions import CapacityReached, MissingSession, PublicSessions, TurnLimit

STATIC = Path(__file__).parent / "static"
COOKIE = "hoso_public_voice"
MAX_BODY = 4096


class TurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=600, strict=True)


def create_app(*, sessions=None, allowed_origins=None, secure_cookie=False):
    store = sessions if sessions is not None else PublicSessions()
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

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "public_dialogue_demo", "reviewed_lookup_available": False, "personal_tools_enabled": False}

    @app.post("/api/voice/session")
    def start(request: Request):
        try:
            token = store.create(request.cookies.get(COOKIE))
        except CapacityReached:
            raise HTTPException(503, detail="session_capacity") from None
        response = JSONResponse({"reply": WELCOME, "state": "welcome", "choices": CHOICES, "expires_in": store.ttl})
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
            return store.turn(request.cookies.get(COOKIE), parsed.text)
        except MissingSession:
            raise HTTPException(401, detail="public_session_expired") from None
        except TurnLimit:
            raise HTTPException(429, detail="turn_limit") from None

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
