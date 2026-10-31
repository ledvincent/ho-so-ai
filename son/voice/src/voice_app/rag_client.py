"""Consumer of Vincent's 61b99f3 chat contract (also compatible with 7c78ec4)."""
import asyncio
import re
from urllib.parse import urlsplit
import httpx
from pydantic import BaseModel, ConfigDict, Field
from .assistant_client import ChatReply
from .privacy import contains_personal_details
from typing import Literal

RAG_TIMEOUT_SECONDS = 180


class DocumentCard(BaseModel):
    # Consumer validation only; Vincent owns the contract and action semantics.
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(max_length=2000)
    kind: Literal["fillable_form", "supporting_document", "submission_instruction"]
    requirement: Literal["required", "conditional", "unconfirmed"]
    condition: str | None = None
    description: str = ""
    originals: int | None = Field(default=None, ge=0)
    copies: int | None = Field(default=None, ge=0)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence_status: str
    form: dict | None = None  # Retained as opaque metadata; never executed.


class Choice(BaseModel):
    id: str = Field(min_length=1, max_length=1000)
    label: str = Field(min_length=1, max_length=2000)


class RagReply(ChatReply):
    choices: list[Choice] = Field(default_factory=list, max_length=20)
    retrieval_state: str | None = Field(default=None, max_length=12000)
    procedure_code: str | None = Field(default=None, pattern=r"^\d\.\d{6}$")
    documents: list[DocumentCard] = Field(default_factory=list, max_length=100)


class RagConversation:
    def __init__(self, base_url, *, transport=None):
        url = urlsplit(base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Expected a server-configured API origin without credentials")
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("Remote API requires HTTPS")
        self.url, self.transport = base_url.rstrip("/"), transport
        self.state = None
        self.history = []
        self.choices = []
        self.last_result = None
        self.requests = 0
        self.lock = asyncio.Lock()

    def clear(self):
        self.state, self.history, self.choices, self.last_result = None, [], [], None

    async def ask(self, question, *, clarification_answer=None, reset=False, cancelled=None):
        if not isinstance(question, str) or not 2 <= len(question.strip()) <= 1000:
            return {"error":"invalid_question"}
        if contains_personal_details(question):
            return {"error":"privacy_rephrase_required"}
        if self.lock.locked():
            return {"error":"lookup_busy"}
        async with self.lock:
            if self.requests >= 12:
                return {"error":"lookup_limit"}
            if reset:
                self.clear()
            if clarification_answer is not None and clarification_answer not in self.choices:
                return {"error":"invalid_choice"}
            payload = {"message":question.strip(), "history":self.history[-4:]}
            if self.state:
                payload["retrieval_state"] = self.state
            if clarification_answer is not None:
                payload["clarification_answer"] = clarification_answer
            self.requests += 1
            try:
                async with asyncio.timeout(RAG_TIMEOUT_SECONDS):
                    async with httpx.AsyncClient(transport=self.transport, trust_env=False, follow_redirects=False, timeout=RAG_TIMEOUT_SECONDS) as client:
                        task = asyncio.create_task(client.post(self.url + "/assistant/chat", json=payload))
                        try:
                            while not task.done():
                                await asyncio.wait({task}, timeout=0.1)
                                if cancelled and await cancelled():
                                    return {"error":"cancelled_by_interruption"}
                            response = await task
                            if cancelled and await cancelled():
                                return {"error":"cancelled_by_interruption"}
                        finally:
                            if not task.done():
                                task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
                if response.status_code != 200:
                    if response.status_code == 409:
                        self.clear()
                    return {"error":"rag_http_" + str(response.status_code)}
                if len(response.content) > 300000:
                    return {"error":"invalid_rag_response"}
                result = RagReply.model_validate(response.json())
                choice_ids = [choice.id for choice in result.choices]
                if len(choice_ids) != len(set(choice_ids)) or (choice_ids and not result.retrieval_state):
                    return {"error":"invalid_rag_response"}
                ids = [c.id for c in result.citations]
                if any(c.url.username or c.url.password for c in result.citations):
                    return {"error":"invalid_citations"}
                markers = re.findall(r"\[([^\[\]\n]+)\]", result.answer)
                if len(ids) != len(set(ids)) or not set(markers) <= set(ids):
                    return {"error":"invalid_citations"}
                if result.status == "answered" and (not ids or not markers):
                    return {"error":"missing_citations"}
                if re.search(r"https?://|<[^>]+>|```", result.answer, re.I):
                    return {"error":"invalid_answer"}
                if any(not set(doc.source_ids) <= set(ids) for doc in result.documents):
                    return {"error":"invalid_citations"}
                # Commit state only after validated success; cancellation cannot commit it.
                self.state = result.retrieval_state
                self.choices = [choice.id for choice in result.choices]
                self.history = (self.history + [{"role":"user", "content":question}, {"role":"assistant", "content":result.answer}])[-4:]
                self.last_result = {"status":result.status, "answer":result.answer, "procedure_code":result.procedure_code,
                        "choices":[c.model_dump() for c in result.choices],
                        "citations":[c.model_dump(mode="json") for c in result.citations],
                        "documents":[d.model_dump() for d in result.documents], "context_reset":reset}
                return self.last_result
            except (httpx.TimeoutException, TimeoutError):
                return {"error":"rag_timeout"}
            except ValueError:
                return {"error":"invalid_rag_response"}
            except httpx.HTTPError:
                return {"error":"rag_unavailable"}
