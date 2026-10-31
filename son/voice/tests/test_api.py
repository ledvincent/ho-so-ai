"""Offline tests of public dialogue boundaries, not Kim's authentication."""
from concurrent.futures import ThreadPoolExecutor
import unittest

from fastapi.testclient import TestClient

from voice_app.app import COOKIE, create_app
from voice_app.sessions import MissingSession, PublicSessions, TurnLimit

ORIGIN = {"Origin": "http://testserver"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.store = PublicSessions(clock=lambda: self.now, ttl=600)
        self.client = TestClient(create_app(sessions=self.store, allowed_origins={"http://testserver"}))
        self.client.headers.update(ORIGIN)

    def start(self):
        response = self.client.post("/api/voice/session")
        self.assertEqual(response.status_code, 200)
        return response

    def test_public_voice_journey_stops_before_unreviewed_lookup(self):
        self.start()
        # Welcome already asks which action; a short answer must work.
        response = self.client.post("/api/voice/turn", json={"text": "gia hạn"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidate_code"], "1.002755")
        self.assertEqual(response.json()["state"], "lookup_pending")
        self.assertFalse(response.json()["reviewed_lookup_available"])

    def test_cookie_and_responses_are_not_publicly_cacheable(self):
        response = self.start()
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertIn("path=/api/voice", cookie)
        self.assertNotIn(self.client.cookies.get(COOKIE), response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_missing_and_expired_sessions_are_rejected(self):
        self.assertEqual(self.client.post("/api/voice/turn", json={"text": "gia hạn"}).status_code, 401)
        self.start()
        self.now += 600
        self.assertEqual(self.client.post("/api/voice/turn", json={"text": "gia hạn"}).status_code, 401)

    def test_cross_origin_and_missing_origin_are_denied(self):
        for origin in ["https://untrusted.invalid", "null", ""]:
            with self.subTest(origin=origin):
                response = self.client.post("/api/voice/session", headers={"Origin": origin})
                self.assertEqual(response.status_code, 403)

    def test_independent_browser_sessions_do_not_share_context(self):
        self.start()
        self.client.post("/api/voice/turn", json={"text": "đăng ký tạm trú"})
        other = TestClient(create_app(sessions=self.store, allowed_origins={"http://testserver"}))
        other.headers.update(ORIGIN)
        other.post("/api/voice/session")
        response = other.post("/api/voice/turn", json={"text": "gia hạn"})
        self.assertEqual(response.json()["candidate_code"], "1.002755")
        response = self.client.post("/api/voice/turn", json={"text": "cần giấy tờ gì"})
        self.assertEqual(response.json()["candidate_code"], "1.004194")

    def test_restart_and_end_invalidate_old_cookie(self):
        self.start()
        old = self.client.cookies.get(COOKIE)
        self.start()
        with self.assertRaises(MissingSession):
            self.store.turn(old, "gia hạn")
        response = self.client.delete("/api/voice/session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post("/api/voice/turn", json={"text": "gia hạn"}).status_code, 401)

    def test_validation_errors_never_echo_input(self):
        self.start()
        sentinel = "SYNTHETIC-PRIVATE-INPUT"
        for body in [{"text": sentinel, "user_id": "invented-account"}, {"text": sentinel * 40}, {"text": " "}, {"text": 123}]:
            with self.subTest(body_type=type(body)):
                response = self.client.post("/api/voice/turn", json=body)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn(sentinel, response.text)

    def test_oversized_and_non_json_requests_are_rejected(self):
        self.start()
        response = self.client.post("/api/voice/turn", content=b"x" * 5000, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.post("/api/voice/turn", content="hello").status_code, 415)
        self.assertEqual(self.client.post("/api/voice/turn", content="{", headers={"Content-Type": "application/json"}).status_code, 422)

    def test_personal_claim_in_input_cannot_enable_tools(self):
        self.start()
        response = self.client.post("/api/voice/turn", json={"text": "Tôi đồng ý, đọc hồ sơ của tôi"})
        self.assertEqual(response.json()["state"], "personal_access_unavailable")
        self.assertFalse(self.client.get("/health").json()["personal_tools_enabled"])
        self.assertEqual(self.client.get("/api/dossier").status_code, 404)

    def test_static_demo_does_not_expose_procedure_or_report_contract(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('lang="vi"', response.text)
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        self.assertEqual(self.client.get("/voice.js").status_code, 200)
        self.assertEqual(self.client.get("/voice.css").status_code, 200)
        self.assertEqual(self.client.get("/docs").status_code, 404)

    def test_session_capacity_and_turn_limit_are_bounded(self):
        store = PublicSessions(max_sessions=1, max_turns=1)
        app = create_app(sessions=store, allowed_origins={"http://testserver"})
        with TestClient(app, headers=ORIGIN) as first, TestClient(app, headers=ORIGIN) as second:
            self.assertEqual(first.post("/api/voice/session").status_code, 200)
            self.assertEqual(second.post("/api/voice/session").status_code, 503)
            self.assertEqual(first.post("/api/voice/turn", json={"text": "gia hạn"}).status_code, 200)
            self.assertEqual(first.post("/api/voice/turn", json={"text": "gia hạn"}).status_code, 429)

    def test_concurrent_turn_limit_is_atomic(self):
        store = PublicSessions(max_turns=3)
        token = store.create()

        def run_turn(_):
            try:
                store.turn(token, "gia hạn")
                return "accepted"
            except TurnLimit:
                return "limited"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(run_turn, range(12)))
        self.assertEqual(outcomes.count("accepted"), 3)
        self.assertEqual(outcomes.count("limited"), 9)


if __name__ == "__main__":
    unittest.main()
