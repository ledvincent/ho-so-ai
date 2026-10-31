"""Offline gateway checks using real upstream document metadata, mocked voice."""
import json
from pathlib import Path
import runpy
import unittest

import httpx
from fastapi.testclient import TestClient

create_app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "evals/fake_assistant_api.py"))["create_fixture_app"]
ORIGIN = {"Origin":"http://127.0.0.1:8002"}


class FixtureGatewayTests(unittest.TestCase):
    def test_only_nonlegal_metadata_enters_voice_for_four_codes(self):
        with TestClient(create_app(), headers=ORIGIN) as client:
            for code in ("1.001146", "1.003326", "1.003342", "1.000771"):
                response = client.post("/api/voice/fixture-document", json={"procedure_code":code})
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertTrue(body["synthetic"])
                self.assertEqual(body["procedure_code"], code)
                self.assertEqual(body["section_count"], 6)
                self.assertIn("ma_thu_tuc=" + code, body["source_url"])
                self.assertNotIn("answer", body)
                self.assertNotIn("requirements", body)

    def test_origin_input_and_size_gates(self):
        with TestClient(create_app()) as client:
            self.assertEqual(client.post("/api/voice/fixture-document", json={"procedure_code":"1.001146"}).status_code, 403)
            for payload in ({"procedure_code":"1.004194"}, {"procedure_code":"1.001146", "transcript":"must not be sent"}):
                self.assertEqual(client.post("/api/voice/fixture-document", json=payload, headers=ORIGIN).status_code, 422)
            self.assertEqual(client.post("/api/voice/fixture-document", content="x"*257, headers=ORIGIN).status_code, 413)
            self.assertEqual(client.post("/api/voice/turn", json={}, headers=ORIGIN).status_code, 404)

    def test_fixed_proxy_origin_and_isolated_cookie(self):
        seen = []
        def voice(request):
            seen.append(request)
            return httpx.Response(200, json={"state":"started"}, headers={"set-cookie":"hoso_public_voice=synthetic_cookie-1234567890; HttpOnly; Path=/api/voice; SameSite=strict"})
        with TestClient(create_app(voice_transport=httpx.MockTransport(voice)), headers=ORIGIN) as client:
            client.cookies.set("hoso_fixture_voice", "fixture_token-1234567890_")
            client.cookies.set("hoso_public_voice", "UNRELATED_DIRECT_CALL")
            response = client.post("/api/voice/session?language=en")
            self.assertEqual(response.status_code, 200)
            self.assertIn("hoso_fixture_voice=", response.headers["set-cookie"])
            self.assertEqual(str(seen[0].url), "http://127.0.0.1:8001/api/voice/session?language=en")
            self.assertEqual(seen[0].headers["origin"], "http://127.0.0.1:8001")
            self.assertEqual(seen[0].headers["cookie"], "hoso_public_voice=fixture_token-1234567890_")
            self.assertNotIn("authorization", seen[0].headers)

    def test_same_diagnostic_assets_and_no_generic_proxy(self):
        with TestClient(create_app()) as client:
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/fixture-tool.js").status_code, 200)
            self.assertTrue(client.get("/health").json()["synthetic_api"])
            self.assertEqual(client.get("/api/voice/anything").status_code, 404)


if __name__ == "__main__":
    unittest.main()
