"""Local HTTP fixture for voice-consumer development, NOT retrieval or legal advice.

Run: python son/voice/evals/fake_assistant_api.py
Swagger: http://127.0.0.1:8002/docs ; no keys, LLM or database.
"""
import json
import re
from pathlib import Path
import subprocess

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from voice_app.assistant_client import AssistantClient, CATALOG_CODES

REVISION = "9386f428e6794acd0a8b9e4cb3cc759bf5c989b4"
ROOT = Path(__file__).resolve().parents[3]


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=2, max_length=1000)
    procedure_code: str | None = Field(default=None, pattern=r"^\d\.\d{6}$")
    history: list[Turn] = Field(default_factory=list, max_length=12)


def create_fixture_app(*, voice_transport=None):
    documents = {}
    for code in sorted(CATALOG_CODES):
        raw = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}",
            "show", f"{REVISION}:data/procedures/{code}/procedure.json"], cwd=ROOT)
        document = json.loads(raw)
        assert document["code"] == code
        documents[code] = document
    app = FastAPI(title="Ho So AI — SYNTHETIC API / real document excerpts",
                  description="Development fixture only. No relevance search, model, review or legal advice. Message text is not used for retrieval. Never submit personal data.")

    @app.middleware("http")
    async def mark_fixture(request, call_next):
        if request.method in {"POST", "DELETE"} and request.url.path.startswith("/api/voice/") and request.headers.get("origin") not in {"http://127.0.0.1:8002", "http://localhost:8002"}:
            return JSONResponse({"detail":"origin_denied"}, status_code=403)
        response = await call_next(request)
        response.headers["X-HoSo-Synthetic-Fixture"] = "1"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path != "/docs":
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'"
        return response

    static = ROOT / "son/voice/src/voice_app/static"

    @app.get("/")
    def voice_page():
        return FileResponse(static / "index.html")

    @app.get("/voice.js")
    @app.get("/voice.css")
    @app.get("/audio-client.js")
    @app.get("/realtime-client.js")
    @app.get("/fixture-tool.js")
    def voice_asset(request: Request):
        asset = request.url.path[1:]
        return FileResponse(static / asset)

    @app.api_route("/api/voice/{operation}", methods=["GET", "POST", "DELETE"])
    async def voice_bridge(operation: str, request: Request):
        if operation == "fixture-document" and request.method == "POST":
            raw = await bounded_body(request, 256)
            try:
                payload = json.loads(raw)
                code = payload["procedure_code"]
                if set(payload) != {"procedure_code"} or code not in documents:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise HTTPException(422, "invalid_fixture_code") from None
            result = await AssistantClient("http://127.0.0.1:8002", transport=httpx.ASGITransport(app=app)).ask("Fictional connection test: inspect document identity.", code)
            if result.reply is None or result.reply.status != "answered":
                raise HTTPException(503, "fixture_unavailable")
            document = documents[code]
            # Only document identity/headings enter the voice model. Draft legal
            # requirements in the raw fixture answer do not enter live speech.
            return {"synthetic":True, "procedure_code":code, "document_title":result.reply.citations[0].title,
                    "section_heading":document["document_json"]["sections"][0]["heading"],
                    "section_count":len(document["document_json"]["sections"]),
                    "source_url":str(result.reply.citations[0].url),
                    "notice":"Connection test only; unreviewed document identity, not a legal answer. No requirements, fees or deadlines are supplied."}
        allowed = {("GET", "capabilities"), ("POST", "session"), ("DELETE", "session"),
                   ("POST", "realtime"), ("DELETE", "realtime")}
        if (request.method, operation) not in allowed:
            raise HTTPException(404)
        raw = await bounded_body(request, 65536 if operation == "realtime" else 0)
        headers = {"Origin":"http://127.0.0.1:8001"}
        for name in ("content-type", "x-audio-consent"):
            if name in request.headers:
                headers[name] = request.headers[name]
        # Isolate the fixture call from an existing direct call on port 8001.
        cookie = request.cookies.get("hoso_fixture_voice")
        if cookie and re.fullmatch(r"[A-Za-z0-9_-]{20,128}", cookie):
            headers["Cookie"] = "hoso_public_voice=" + cookie
        params = {"language":request.query_params.get("language", "vi")} if operation == "session" else {}
        try:
            async with httpx.AsyncClient(transport=voice_transport, trust_env=False, follow_redirects=False, timeout=30) as client:
                upstream = await client.request(request.method, "http://127.0.0.1:8001/api/voice/" + operation, content=raw, params=params, headers=headers)
        except httpx.HTTPError:
            raise HTTPException(503, "private_voice_server_unavailable") from None
        response = Response(upstream.content, status_code=upstream.status_code,
                            media_type=upstream.headers.get("content-type"))
        for name in ("x-call-max-seconds", "set-cookie"):
            if name in upstream.headers:
                response.headers[name] = upstream.headers[name].replace("hoso_public_voice=", "hoso_fixture_voice=") if name == "set-cookie" else upstream.headers[name]
        return response

    async def bounded_body(request, limit):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                raise HTTPException(413, "fixture_request_too_large")
        return bytes(body)

    @app.get("/health")
    def health():
        return {"status":"ok", "synthetic_api":True, "live_advice_enabled":False,
                "upstream_commit":REVISION, "procedures":[{"code":code, "name":d["name"]} for code,d in documents.items()]}

    @app.post("/assistant/chat")
    def chat(request: ChatRequest):
        reply = {"status":"insufficient_context", "answer":"TEST FIXTURE: no validated answer is available.", "citations":[], "model":None}
        if request.procedure_code is None:
            return {**reply, "status":"needs_clarification", "answer":"TEST FIXTURE: choose one explicit catalog code; no search is performed."}
        if request.procedure_code not in documents:
            return {**reply, "status":"out_of_scope", "answer":"TEST FIXTURE: procedure not in this four-document catalog."}
        if request.message == "[test:unready]":
            return JSONResponse({"detail":"TEST FIXTURE: context gate not ready"}, status_code=409)
        if request.message == "[test:no-context]":
            return reply
        document = documents[request.procedure_code]
        section = next(s for s in document["document_json"]["sections"] if s.get("text_verbatim"))
        source_id = "procedure-" + request.procedure_code.replace(".", "-")
        # Fixed excerpt, not a relevant answer to the question. No translation or synthesis.
        excerpt = section["text_verbatim"][:2000]
        return {"status":"answered", "answer":"TEST FIXTURE — UNREVIEWED DOCUMENT EXCERPT, NOT AN ANSWER TO YOUR QUESTION.\n"
                + section["heading"] + "\n" + excerpt + "\n[EXCERPT ENDS HERE; FULL SECTION MAY CONTINUE] " + f"[{source_id}]",
                "citations":[{"id":source_id, "title":document["name"], "url":document["source_url"]}], "model":None}
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_fixture_app(), host="127.0.0.1", port=8002, access_log=False)
