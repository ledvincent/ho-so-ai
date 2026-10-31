import json
from pathlib import Path
import runpy
import sys
import unittest
import httpx
from fastapi.testclient import TestClient

folder = str(Path(__file__).resolve().parents[1] / "evals")
sys.path.insert(0, folder)
try:
    create_app = runpy.run_path(str(Path(folder)/"live_rag_voice.py"))["create_live_app"]
finally:
    sys.path.pop(0)

class LiveGatewayTests(unittest.TestCase):
    def test_session_origin_state_and_no_fixture_fallback(self):
        received=[]
        def backend(request):
            received.append(json.loads(request.content))
            return httpx.Response(200,json={"status":"needs_clarification","answer":"Which procedure?","choices":[{"id":"extend","label":"Extension"}],"retrieval_state":"signed-private-state"})
        def voice(request):
            return httpx.Response(200,json={"state":"started"},headers={"set-cookie":"hoso_public_voice=synthetic_token-123456789; Path=/api/voice; HttpOnly; SameSite=strict"})
        app=create_app("https://example.org",transport=httpx.MockTransport(backend),voice_transport=httpx.MockTransport(voice))
        with TestClient(app, headers={"Origin":"http://127.0.0.1:8003"}) as client:
            self.assertEqual(client.post("/api/voice/rag",json={"question":"Extend my stay"}).status_code,401)
            self.assertEqual(client.post("/api/voice/session?language=en").status_code,200)
            result=client.post("/api/voice/rag",json={"question":"Extend my stay"})
            self.assertEqual(result.status_code,200)
            self.assertNotIn("retrieval_state", result.json())
            client.post("/api/voice/rag",json={"question":"Extension please","clarification_answer":"extend"})
            self.assertEqual(received[-1]["retrieval_state"],"signed-private-state")
            self.assertEqual(client.post("/api/voice/fixture-document",json={"procedure_code":"1.001146"}).status_code,404)
            self.assertEqual(client.post("/assistant/chat",json={}).status_code,404)
            self.assertEqual(client.post("/api/voice/rag",json={"question":"Extend my stay"},headers={"Origin":"http://evil.example"}).status_code,403)
            client.delete("/api/voice/realtime")
            self.assertEqual(client.post("/api/voice/rag",json={"question":"Extend my stay"}).status_code,401)
