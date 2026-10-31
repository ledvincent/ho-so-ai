"""Grounded assistant; retrieval is replaceable through get_retriever()."""
import json
import os
import re
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy.exc import SQLAlchemyError

from api.context import context
from api.search import search
from api.assistant_policy import PROMPT

router = APIRouter(prefix="/assistant", tags=["assistant"])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Turn(Strict):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(Strict):
    message: str = Field(min_length=2, max_length=1000)
    procedure_code: str | None = Field(default=None, pattern=r"^\d\.\d{6}$")
    history: list[Turn] = Field(default_factory=list, max_length=12)


class Source(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    text: str = Field(min_length=1, max_length=120000)


class Retrieval(Strict):
    sources: list[Source] = Field(default_factory=list, max_length=20)
    # Optional generated RAG answer is a routing/synthesis aid, not primary evidence.
    answer: str | None = Field(default=None, max_length=12000)
    clarification: str | None = Field(default=None, max_length=2000)

    @field_validator("sources")
    @classmethod
    def unique_ids(cls, sources):
        if len({s.id for s in sources}) != len(sources):
            raise ValueError("Source IDs must be unique")
        return sources


class Generated(Strict):
    status: Literal["answered", "insufficient_context", "needs_clarification", "out_of_scope"]
    answer: str = Field(min_length=1, max_length=16000)
    source_ids: list[str] = Field(max_length=20)


class Citation(Strict):
    id: str
    title: str
    url: HttpUrl


class ChatResponse(Strict):
    status: Literal["answered", "insufficient_context", "needs_clarification", "out_of_scope"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    model: str | None = None


def retrieve(request: ChatRequest) -> Retrieval:
    """Default adapter preserves existing validation and retrieval gates."""
    code = request.procedure_code
    if code is None:
        result = search(request.message)
        matches = result["results"]
        if not matches:
            return Retrieval()
        if len(matches) > 1:
            choices = "; ".join(f'{m["code"]}: {m["name"]}' for m in matches)
            return Retrieval(clarification="Please select a procedure: " + choices)
        code = matches[0]["code"]
    record = context(code, request.message)
    return Retrieval(sources=[Source(
        id="procedure-" + code.replace(".", "-"), title=record["name"],
        url=record["source"]["url"],
        text=json.dumps(record, ensure_ascii=False, default=str),
    )])


def get_retriever():
    # Replace this dependency when the new RAG implementation is ready.
    return retrieve


def build_messages(request: ChatRequest, evidence: Retrieval):
    # History is NOT promoted to trusted assistant turns. Even URLs/titles stay
    # in the data envelope; no client input is interpolated into system policy.
    payload = json.dumps({
        "question": request.message, "selected_procedure": request.procedure_code,
        "untrusted_history": [t.model_dump() for t in request.history],
        "retrieval": {"sources": [s.model_dump(mode="json") for s in evidence.sources],
                      "rag_draft": evidence.answer},
    }, ensure_ascii=False)
    if len(payload) > 140000:
        raise HTTPException(413, "Assistant context is too large; narrow the retrieval")
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": payload}]


def output_format(evidence: Retrieval):
    # A small portable strict schema; runtime Pydantic limits still apply.
    return {"type": "json_schema", "json_schema": {
        "name": "procedure_answer", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
            "required": ["status", "answer", "source_ids"],
            "properties": {
                "status": {"type": "string", "enum": ["answered", "insufficient_context",
                                                       "needs_clarification", "out_of_scope"]},
                "answer": {"type": "string"},
                "source_ids": {"type": "array", "items": {
                    "type": "string", "enum": [s.id for s in evidence.sources]}},
            }}}}


def validate_answer(result: Generated, evidence: Retrieval):
    known = {s.id for s in evidence.sources}
    cited = set(result.source_ids)
    # All brackets are reserved for citations by the response contract.
    markers = re.findall(r"\[([^\[\]\n]+)\]", result.answer)
    if len(cited) != len(result.source_ids) or not cited <= known or set(markers) != cited:
        raise ValueError("Invalid citation references")
    if result.status == "answered" and not cited:
        raise ValueError("Answer missing citations")
    if result.status == "out_of_scope" and cited:
        raise ValueError("Out of scope response must not cite evidence")
    # This rejects common active-content/link channels, not arbitrary semantic
    # injection. Callers must still render text, never HTML or auto-linked prose.
    if re.search(r"https?://|www\.|javascript:|data:|<[^>]+>|```|\]\s*\(", result.answer, re.I):
        raise ValueError("Unexpected link or active content")


def generate(request: ChatRequest, evidence: Retrieval) -> tuple[Generated, str]:
    model = os.getenv("ASSISTANT_MODEL", "").strip()
    base = os.getenv("ASSISTANT_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    # Never send the OpenAI credential to a custom provider by accident.
    key = os.getenv("ASSISTANT_API_KEY")
    if not key and base == "https://api.openai.com/v1":
        key = os.getenv("OPENAI_API_KEY")
    if not model or not key:
        raise HTTPException(503, "Configure ASSISTANT_MODEL and ASSISTANT_API_KEY")
    messages = build_messages(request, evidence)
    try:
        response = httpx.post(base + "/chat/completions",
            headers={"Authorization": "Bearer " + key}, timeout=60,
            json={"model": model, "messages": messages,
                  "max_completion_tokens": 4000, "response_format": output_format(evidence),
                  "store": False})
        response.raise_for_status()
        choice = response.json()["choices"][0]
        if choice["finish_reason"] != "stop" or choice["message"].get("refusal") or choice["message"].get("tool_calls"):
            raise ValueError("Incomplete model response")
        result = Generated.model_validate_json(choice["message"]["content"])
        validate_answer(result, evidence)
        return result, model
    except httpx.TimeoutException:
        raise HTTPException(504, "Assistant provider timed out") from None
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(502, "Assistant provider returned an unusable response") from None


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, retriever=Depends(get_retriever)):
    try:
        evidence = Retrieval.model_validate(retriever(request))
    except LookupError:
        raise HTTPException(404, "Procedure context not found") from None
    except RuntimeError:
        raise HTTPException(409, "Retrieval is not ready or context is not validated") from None
    except (SQLAlchemyError, httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(503, "Retrieval unavailable") from None
    if evidence.clarification:
        return ChatResponse(status="needs_clarification", answer=evidence.clarification)
    if not evidence.sources:
        return ChatResponse(status="insufficient_context",
                            answer="I do not have source context for this question. Please specify the procedure you need.")
    result, model = generate(request, evidence)
    citations = [Citation(id=s.id, title=s.title, url=s.url)
                 for s in evidence.sources if s.id in result.source_ids]
    return ChatResponse(status=result.status, answer=result.answer, citations=citations, model=model)
