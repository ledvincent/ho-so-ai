import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from voice_app.rag_client import RagConversation

def answered():
    return {"status":"answered", "answer":"Synthetic sourced answer [s1]", "citations":[{"id":"s1", "title":"Synthetic", "url":"https://example.org/source"}], "model":"synthetic", "procedure_code":"1.001146", "retrieval_state":"server-signed-next", "documents":[]}

class RagTests(unittest.IsolatedAsyncioTestCase):
    async def test_clarification_state_stays_server_side_and_reset_clears_it(self):
        sent=[]
        def handle(request):
            sent.append(json.loads(request.content))
            if len(sent)==1:
                return httpx.Response(200,json={"status":"needs_clarification", "answer":"Which level?", "choices":[{"id":"province", "label":"Provincial"}], "retrieval_state":"signed-state"})
            return httpx.Response(200,json=answered())
        session=RagConversation("https://example.org",transport=httpx.MockTransport(handle))
        first=await session.ask("Extend my stay")
        self.assertNotIn("retrieval_state", first)
        self.assertEqual((await session.ask("Province",clarification_answer="invented"))["error"],"invalid_choice")
        result=await session.ask("Provincial please",clarification_answer="province")
        self.assertEqual(sent[-1]["retrieval_state"],"signed-state")
        self.assertEqual(sent[-1]["clarification_answer"],"province")
        self.assertEqual(result["procedure_code"],"1.001146")
        await session.ask("Actually a new visa",reset=True)
        self.assertNotIn("retrieval_state",sent[-1])
        self.assertEqual(sent[-1]["history"],[])

    async def test_409_does_not_answer_and_clears_old_selection(self):
        session=RagConversation("http://localhost:9000",transport=httpx.MockTransport(lambda r:httpx.Response(409,text="private provider detail")))
        session.state="old"
        self.assertEqual(await session.ask("What documents?"),{"error":"rag_http_409"})
        self.assertIsNone(session.state)

    async def test_missing_or_forged_citation_is_rejected(self):
        for answer,citations in (("No source",[]),("Wrong [unknown]",answered()["citations"])):
            body={**answered(),"answer":answer,"citations":citations}
            session=RagConversation("https://example.org",transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
            self.assertIn("error",await session.ask("What documents?"))
            self.assertIsNone(session.state)

    async def test_cancel_does_not_commit_history_or_state(self):
        entered=asyncio.Event()
        async def handle(request):
            entered.set()
            await asyncio.Event().wait()
        session=RagConversation("https://example.org",transport=httpx.MockTransport(handle))
        task=asyncio.create_task(session.ask("What documents?"))
        await entered.wait()
        self.assertEqual(await session.ask("Second request"),{"error":"lookup_busy"})
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(session.history,[])
        self.assertIsNone(session.state)

    async def test_sessions_do_not_share_history(self):
        client=lambda:RagConversation("https://example.org",transport=httpx.MockTransport(lambda r:httpx.Response(200,json=answered())))
        a,b=client(),client()
        await a.ask("First fictional question")
        self.assertIsNone(b.state)
        self.assertEqual(b.history,[])

    async def test_disconnected_lookup_keeps_previous_completed_context(self):
        entered = asyncio.Event()
        cancelled = False
        async def slow(request):
            entered.set()
            await asyncio.Event().wait()
        async def disconnected():
            return cancelled
        session = RagConversation("https://example.org", transport=httpx.MockTransport(slow))
        session.state = "previous-signed-selection"
        session.history = [{"role":"user", "content":"Previous general question"}]
        task = asyncio.create_task(session.ask("What documents?", cancelled=disconnected))
        await entered.wait()
        cancelled = True
        self.assertEqual((await task)["error"], "cancelled_by_interruption")
        self.assertEqual(session.state, "previous-signed-selection")
        self.assertEqual(len(session.history), 1)
        session.transport = httpx.MockTransport(lambda r: httpx.Response(200, json=answered()))
        self.assertEqual((await session.ask("How long does it take?"))["status"], "answered")

    async def test_timeout_unavailability_and_invalid_payload_are_distinct(self):
        async def slow(request):
            await asyncio.Event().wait()
        session = RagConversation("https://example.org", transport=httpx.MockTransport(slow))
        with patch("voice_app.rag_client.RAG_TIMEOUT_SECONDS", 0.01):
            self.assertEqual((await session.ask("What documents?"))["error"], "rag_timeout")
        def unavailable(request):
            raise httpx.ConnectError("private infrastructure detail")
        session.transport = httpx.MockTransport(unavailable)
        self.assertEqual((await session.ask("What documents?"))["error"], "rag_unavailable")
        session.transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"unexpected":"private"}))
        self.assertEqual((await session.ask("What documents?"))["error"], "invalid_rag_response")
        self.assertEqual(session.history, [])

    async def test_http_failures_are_not_administrative_answers(self):
        for status in (404, 409, 413, 422, 502, 503, 504):
            session = RagConversation("https://example.org", transport=httpx.MockTransport(lambda r: httpx.Response(status, text="private")))
            self.assertEqual(await session.ask("What documents?"), {"error":f"rag_http_{status}"})

    async def test_personal_values_never_reach_rag_or_history(self):
        sent = []
        def handler(request):
            sent.append(request)
            return httpx.Response(200, json=answered())
        session = RagConversation("https://example.org", transport=httpx.MockTransport(handler))
        for text in (
            "My name is Test Person. Which documents?",
            "Tôi tên Nguyễn Văn Mẫu, cần giấy tờ gì?",
            "My passport number is X1234567; can I extend?",
            "Contact fictional@example.org about extension",
            "Call +84 900 123 456 for an extension",
            "My address is 123 Fictional Street. What documents?",
            "Ngày sinh 2000-01-01, cần giấy tờ gì?",
            "My password is fictional-only",
        ):
            self.assertEqual((await session.ask(text))["error"], "privacy_rephrase_required")
        self.assertEqual(sent, [])
        self.assertEqual(session.history, [])
        self.assertEqual((await session.ask("What documents for procedure 1.001146?"))["status"], "answered")

    async def test_partial_answer_documents_and_unknown_status(self):
        card = {"id":"passport", "title":"Synthetic document", "kind":"supporting_document", "requirement":"conditional",
                "condition":"Synthetic condition", "originals":1, "copies":0, "source_ids":["s1"], "evidence_status":"supported", "form":None}
        body = {**answered(), "status":"insufficient_context", "documents":[card]}
        session = RagConversation("https://example.org", transport=httpx.MockTransport(lambda r: httpx.Response(200,json=body)))
        result = await session.ask("What documents?")
        self.assertEqual(result["status"], "insufficient_context")
        self.assertEqual(result["documents"][0]["condition"], "Synthetic condition")
        self.assertNotIn("retrieval_state", result)
        for status in ("out_of_scope", "insufficient_context"):
            body = {"status":status,"answer":"Synthetic unavailable context", "citations":[]}
            self.assertEqual((await session.ask("Another general request", reset=True))["status"], status)
        body = {**answered(), "status":"approved"}
        self.assertEqual((await session.ask("What documents?"))["error"], "invalid_rag_response")

    async def test_duplicate_choices_and_document_citations_fail_closed(self):
        for body in (
            {"status":"needs_clarification", "answer":"Choose", "choices":[{"id":"x", "label":"One"}]},
            {"status":"needs_clarification", "answer":"Choose", "retrieval_state":"signed", "choices":[{"id":"x","label":"One"},{"id":"x","label":"Two"}]},
            {**answered(), "documents":[{"id":"x","title":"Uncited", "kind":"supporting_document", "requirement":"required", "source_ids":["wrong"], "evidence_status":"supported"}]},
        ):
            session = RagConversation("https://example.org", transport=httpx.MockTransport(lambda r: httpx.Response(200,json=body)))
            self.assertIn("error", await session.ask("What documents?"))
            self.assertIsNone(session.state)

    async def test_bound_applies_even_after_context_reset(self):
        session = RagConversation("https://example.org", transport=httpx.MockTransport(lambda r: httpx.Response(200,json=answered())))
        session.requests = 12
        self.assertEqual(await session.ask("What documents?", reset=True), {"error":"lookup_limit"})

    async def test_second_clarification_uses_new_state_and_new_choice_ids(self):
        sent = []
        def handle(request):
            sent.append(json.loads(request.content))
            if len(sent) <= 2:
                return httpx.Response(200,json={"status":"needs_clarification", "answer":"Synthetic clarification",
                    "choices":[{"id":f"choice-{len(sent)}", "label":"Synthetic option"}], "retrieval_state":f"signed-{len(sent)}"})
            return httpx.Response(200,json=answered())
        session=RagConversation("https://example.org",transport=httpx.MockTransport(handle))
        await session.ask("Extend my stay")
        await session.ask("First option",clarification_answer="choice-1")
        self.assertEqual((await session.ask("Old option",clarification_answer="choice-1"))["error"],"invalid_choice")
        result=await session.ask("Second option",clarification_answer="choice-2")
        self.assertEqual(sent[-1]["retrieval_state"],"signed-2")
        self.assertEqual(result["procedure_code"],"1.001146")
