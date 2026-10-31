"""Mocked call signaling/lifecycle only; not a live microphone or model eval."""
import asyncio
import unittest

import httpx
from fastapi.testclient import TestClient

from voice_app.app import create_app
from voice_app.realtime import RealtimeCalls, call_configuration
from voice_app.sessions import MissingSession, PublicSessions
from voice_app.speech import OpenAISpeech, SpeechUnavailable

ORIGIN = {"Origin":"http://testserver"}
HEADERS = {"X-Audio-Consent":"1", "Content-Type":"application/sdp"}
OFFER = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
ANSWER = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\na=synthetic-test\r\n"


class FakeRealtime:
    enabled = True

    def __init__(self):
        self.created = []
        self.closed = []

    async def create_realtime(self, offer, language, token):
        self.created.append(language)
        return ANSWER, "rtc_synthetic_" + str(len(self.created))

    async def close_realtime(self, call_id):
        self.closed.append(call_id)
        return True


class RealtimeApiTests(unittest.TestCase):
    def test_call_is_owned_by_public_cookie_and_closes_on_end(self):
        provider = FakeRealtime()
        app = create_app(speech=provider, allowed_origins={"http://testserver"})
        with TestClient(app, headers=ORIGIN) as a, TestClient(app, headers=ORIGIN) as b:
            self.assertTrue(a.get("/api/voice/capabilities").json()["realtime_available"])
            a.post("/api/voice/session?language=en")
            result = a.post("/api/voice/realtime", headers=HEADERS, content=OFFER)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.text, ANSWER)
            self.assertNotIn("rtc_", result.text)
            self.assertEqual(result.headers["x-call-max-seconds"], "180")
            self.assertEqual(a.post("/api/voice/realtime", headers=HEADERS, content=OFFER).status_code, 429)
            b.post("/api/voice/session")
            b.delete("/api/voice/realtime")
            self.assertEqual(provider.closed, [])
            a.delete("/api/voice/realtime")
            self.assertEqual(provider.closed, ["rtc_synthetic_1"])

    def test_no_call_before_consent_session_and_valid_offer(self):
        provider = FakeRealtime()
        with TestClient(create_app(speech=provider, allowed_origins={"http://testserver"}), headers=ORIGIN) as client:
            self.assertEqual(client.post("/api/voice/realtime", content=OFFER).status_code, 403)
            self.assertEqual(client.post("/api/voice/realtime", content=OFFER, headers=HEADERS).status_code, 401)
            client.post("/api/voice/session")
            self.assertEqual(client.post("/api/voice/realtime", content="not SDP", headers=HEADERS).status_code, 422)
            self.assertEqual(client.post("/api/voice/realtime", content="x" * 70000, headers=HEADERS).status_code, 413)
            self.assertEqual(provider.created, [])

    def test_restart_and_shutdown_hang_up_provider_calls(self):
        provider = FakeRealtime()
        with TestClient(create_app(speech=provider, allowed_origins={"http://testserver"}), headers=ORIGIN) as client:
            client.post("/api/voice/session")
            client.post("/api/voice/realtime", content=OFFER, headers=HEADERS)
            client.post("/api/voice/session")
            self.assertEqual(len(provider.closed), 1)
            client.post("/api/voice/realtime", content=OFFER, headers=HEADERS)
        self.assertEqual(len(provider.closed), 2)

    def test_public_configuration_has_no_data_or_submission_tools(self):
        for language in ["vi", "en"]:
            config = call_configuration(language, "synthetic-model")
            vad = config["audio"]["input"]["turn_detection"]
            self.assertTrue(vad["create_response"])
            self.assertTrue(vad["interrupt_response"])
            self.assertEqual(config["tools"], [])
            self.assertEqual(config["tool_choice"], "none")
            self.assertIn("NO reviewed legal sources", config["instructions"])


class RealtimeLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_expiry_hangs_up_without_browser(self):
        provider = FakeRealtime()
        sessions = PublicSessions()
        calls = RealtimeCalls(provider, sessions, duration=0.01)
        await calls.create(sessions.create(), OFFER)
        await asyncio.sleep(0.03)
        self.assertEqual(len(provider.closed), 1)
        self.assertEqual(calls.calls, {})

    async def test_end_during_handshake_closes_late_call(self):
        provider = FakeRealtime()
        ready, finish = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            ready.set()
            await finish.wait()
            return ANSWER, "rtc_synthetic_late"
        provider.create_realtime = slow
        sessions = PublicSessions()
        calls = RealtimeCalls(provider, sessions)
        token = sessions.create()
        task = asyncio.create_task(calls.create(token, OFFER))
        await ready.wait()
        await calls.end(token)
        finish.set()
        with self.assertRaises(MissingSession):
            await task
        self.assertEqual(provider.closed, ["rtc_synthetic_late"])
        self.assertEqual(calls.calls, {})

    async def test_unified_request_keeps_key_and_call_id_on_server(self):
        requests = []
        def handle(request):
            requests.append(request)
            if request.url.path.endswith("hangup"):
                return httpx.Response(200)
            return httpx.Response(201, text=ANSWER, headers={"Location":"/v1/realtime/calls/rtc_synthetic"})
        provider = OpenAISpeech("synthetic-api-key", transport=httpx.MockTransport(handle))
        answer, call_id = await provider.create_realtime(OFFER, "en", "synthetic-public-cookie")
        self.assertEqual(answer, ANSWER)
        self.assertEqual(call_id, "rtc_synthetic")
        self.assertEqual(requests[0].headers["authorization"], "Bearer synthetic-api-key")
        self.assertNotIn(b"synthetic-api-key", requests[0].content)
        self.assertNotIn("synthetic-public-cookie", requests[0].headers["openai-safety-identifier"])
        self.assertTrue(await provider.close_realtime(call_id))
        self.assertEqual(requests[-1].url.path, "/v1/realtime/calls/rtc_synthetic/hangup")

    async def test_provider_error_is_not_reflected(self):
        provider = OpenAISpeech("synthetic-api-key", transport=httpx.MockTransport(lambda req: httpx.Response(403, text="SYNTHETIC-PRIVATE-BODY")))
        with self.assertRaises(SpeechUnavailable) as raised:
            await provider.create_realtime(OFFER, "vi", "synthetic-cookie")
        self.assertNotIn("SYNTHETIC-PRIVATE", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
