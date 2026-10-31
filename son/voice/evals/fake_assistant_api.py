"""Local HTTP fixture for voice-consumer development, NOT retrieval or legal advice.

Run: python son/voice/evals/fake_assistant_api.py
Swagger: http://127.0.0.1:8002/docs ; no keys, LLM or database.
"""
import json
from pathlib import Path
import subprocess

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from voice_app.assistant_client import CATALOG_CODES

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


def create_fixture_app():
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
        response = await call_next(request)
        response.headers["X-HoSo-Synthetic-Fixture"] = "1"
        response.headers["Cache-Control"] = "no-store"
        return response

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
