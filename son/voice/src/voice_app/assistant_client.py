"""Opt-in server consumer of Vincent's interface; not wired to live voice.

Transport success does not establish reviewed evidence or permit factual speech.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError
from typing import Literal

CATALOG_CODES = frozenset({"1.001146", "1.003326", "1.003342", "1.000771"})


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl


class ChatReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["answered", "needs_clarification", "insufficient_context", "out_of_scope"]
    answer: str = Field(min_length=1, max_length=16000)
    citations: list[Citation] = Field(default_factory=list, max_length=20)
    model: str | None = None


@dataclass(frozen=True)
class DraftResult:
    """Consumer-local result, NOT a proposed procedure/report schema."""
    reply: ChatReply | None
    error: str | None = None

    @property
    def available_for_live_advice(self):
        # ChatResponse supplies no pinned human review/checklist identity.
        return False


class AssistantClient:
    def __init__(self, base_url, *, transport=None):
        url = urlsplit(base_url)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"} or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment:
            raise ValueError("The development assistant must use an explicit local HTTP origin")
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def ask(self, message, procedure_code):
        # Explicit catalog routing only; no automatic search, PII collection or history.
        if procedure_code not in CATALOG_CODES or not isinstance(message, str) or not 2 <= len(message.strip()) <= 1000:
            return DraftResult(None, "invalid_request")
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=65,
                                       trust_env=False, follow_redirects=False) as client:
                response = await client.post(self.base_url + "/assistant/chat", json={
                    "message": message.strip(), "procedure_code": procedure_code, "history": []})
            if response.status_code != 200:
                return DraftResult(None, "assistant_http_" + str(response.status_code))
            if len(response.content) > 100000:
                return DraftResult(None, "invalid_response")
            reply = ChatReply.model_validate(response.json())
            if reply.status == "answered" and not reply.citations:
                return DraftResult(None, "missing_citations")
            ids = [citation.id for citation in reply.citations]
            if len(ids) != len(set(ids)):
                return DraftResult(None, "invalid_response")
            return DraftResult(reply)
        except httpx.TimeoutException:
            return DraftResult(None, "assistant_timeout")
        except (httpx.HTTPError, ValidationError, ValueError):
            return DraftResult(None, "invalid_response")
