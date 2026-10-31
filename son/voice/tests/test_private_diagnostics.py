from pathlib import Path
import runpy
import unittest
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

install = runpy.run_path(str(Path(__file__).resolve().parents[1] / "evals/start_vincent_private.py"))["install_provider_diagnostics"]


class PrivateDiagnosticsTests(unittest.TestCase):
    def test_only_allowlisted_status_and_code_are_exposed(self):
        app = FastAPI()
        with patch.object(httpx, "post", return_value=httpx.Response(401, json={"error":{"code":"invalid_api_key", "message":"SYNTHETIC-PRIVATE-DETAIL"}})):
            install(app)
            httpx.post("https://api.openai.com/v1/chat/completions", headers={"Authorization":"Bearer SYNTHETIC-KEY"})
            with TestClient(app) as client:
                result = client.get("/voice-runtime/diagnostics")
                self.assertEqual(result.json()["provider"], {"http_status":401,"code":"invalid_api_key"})
                self.assertNotIn("SYNTHETIC", result.text)

    def test_unknown_error_code_is_not_reflected(self):
        app = FastAPI()
        with patch.object(httpx, "post", return_value=httpx.Response(400, json={"error":{"code":"SYNTHETIC-PRIVATE"}})):
            install(app)
            httpx.post("https://api.openai.com/v1/chat/completions")
            with TestClient(app) as client:
                self.assertEqual(client.get("/voice-runtime/diagnostics").json()["provider"]["code"], "provider_error")
