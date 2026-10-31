"""Consumer of Vincent 7c78ec4. Signed state stays on our server."""
import asyncio
import re
from urllib.parse import urlsplit
import httpx
from pydantic import BaseModel, ConfigDict, Field
from .assistant_client import ChatReply


class Choice(BaseModel):
    id: str = Field(max_length=1000)
    label: str = Field(max_length=2000)


class RagReply(ChatReply):
    choices: list[Choice] = Field(default_factory=list, max_length=20)
    retrieval_state: str | None = Field(default=None, max_length=12000)
    procedure_code: str | None = None
    documents: list[dict] = Field(default_factory=list, max_length=100)


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
        self.lock = asyncio.Lock()

    async def ask(self, question, *, clarification_answer=None, reset=False):
        if not isinstance(question, str) or not 2 <= len(question.strip()) <= 1000:
            return {"error":"invalid_question"}
        if self.lock.locked():
            return {"error":"lookup_busy"}
        async with self.lock:
            if reset:
                self.state, self.history, self.choices = None, [], []
            if clarification_answer is not None and clarification_answer not in self.choices:
                return {"error":"invalid_choice"}
            payload = {"message":question.strip(), "history":self.history[-4:]}
            if self.state:
                payload["retrieval_state"] = self.state
            if clarification_answer is not None:
                payload["clarification_answer"] = clarification_answer
            try:
                async with httpx.AsyncClient(transport=self.transport, trust_env=False, follow_redirects=False, timeout=125) as client:
                    response = await client.post(self.url + "/assistant/chat", json=payload)
                if response.status_code != 200:
                    if response.status_code == 409:
                        self.state, self.history, self.choices = None, [], []
                    return {"error":"rag_http_" + str(response.status_code)}
                if len(response.content) > 300000:
                    return {"error":"invalid_rag_response"}
                result = RagReply.model_validate(response.json())
                ids = [c.id for c in result.citations]
                markers = re.findall(r"\[([^\[\]\n]+)\]", result.answer)
                if len(ids) != len(set(ids)) or not set(markers) <= set(ids):
                    return {"error":"invalid_citations"}
                if result.status == "answered" and (not ids or not markers):
                    return {"error":"missing_citations"}
                if re.search(r"https?://|<[^>]+>|```", result.answer, re.I):
                    return {"error":"invalid_answer"}
                # Commit state only after validated success; cancellation cannot commit it.
                self.state = result.retrieval_state
                self.choices = [choice.id for choice in result.choices]
                self.history = (self.history + [{"role":"user", "content":question}, {"role":"assistant", "content":result.answer}])[-4:]
                return {"status":result.status, "answer":result.answer, "procedure_code":result.procedure_code,
                        "choices":[c.model_dump() for c in result.choices],
                        "citations":[c.model_dump(mode="json") for c in result.citations]}
            except httpx.TimeoutException:
                return {"error":"rag_timeout"}
            except (httpx.HTTPError, ValueError):
                return {"error":"rag_unavailable"}
