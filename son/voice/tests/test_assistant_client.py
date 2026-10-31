"""Offline consumer transport checks, not legal-grounding evaluations."""
import unittest
import httpx

from voice_app.assistant_client import AssistantClient, CATALOG_CODES


class AssistantConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_statuses_and_unreviewed_output_never_enable_advice(self):
        for status in ("answered", "needs_clarification", "insufficient_context", "out_of_scope"):
            body = {"status": status, "answer": "Synthetic transport test.", "citations":
                    [{"id":"synthetic", "title":"Synthetic", "url":"https://example.org/source"}] if status == "answered" else [], "model":None}
            client = AssistantClient("http://127.0.0.1:8999", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
            result = await client.ask("Fictional question", "1.001146")
            self.assertEqual(result.reply.status, status)
            self.assertFalse(result.available_for_live_advice)

    async def test_errors_do_not_leak_provider_body_or_retry(self):
        for code in (404, 409, 413, 422, 502, 503, 504):
            requests = []
            def handle(request):
                requests.append(request)
                return httpx.Response(code, text="SYNTHETIC_PRIVATE_ERROR")
            result = await AssistantClient("http://localhost:8999", transport=httpx.MockTransport(handle)).ask("Fictional question", "1.001146")
            self.assertEqual(result.error, "assistant_http_" + str(code))
            self.assertNotIn("PRIVATE", repr(result))
            self.assertEqual(len(requests), 1)

    async def test_missing_citation_and_unexpected_shape_fail(self):
        for body in ({"status":"answered", "answer":"Uncited", "citations":[]}, {"status":"invented", "answer":"No"}):
            result = await AssistantClient("http://localhost:8999", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))).ask("Fictional question", "1.001146")
            self.assertIsNone(result.reply)
            self.assertFalse(result.available_for_live_advice)

    async def test_invalid_code_stops_before_transport(self):
        def forbidden(request):
            self.fail("Invalid input must not reach transport")
        client = AssistantClient("http://localhost:8999", transport=httpx.MockTransport(forbidden))
        for code in ("1.004194", "1.002755", "bogus"):
            self.assertEqual((await client.ask("Fictional question", code)).error, "invalid_request")
        self.assertEqual(len(CATALOG_CODES), 4)

    async def test_timeout_has_no_fallback_answer(self):
        def timeout(request):
            raise httpx.ReadTimeout("private timeout detail", request=request)
        result = await AssistantClient("http://localhost:8999", transport=httpx.MockTransport(timeout)).ask("Fictional question", "1.001146")
        self.assertEqual(result.error, "assistant_timeout")
        self.assertIsNone(result.reply)

    def test_external_origins_are_rejected(self):
        for url in ("https://example.org", "http://localhost.evil.test", "http://user:pass@localhost", "http://localhost/path"):
            with self.assertRaises(ValueError):
                AssistantClient(url)
