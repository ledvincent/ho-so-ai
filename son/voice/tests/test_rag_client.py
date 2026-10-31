import asyncio
import json
import unittest
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
