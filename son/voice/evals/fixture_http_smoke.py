"""Real HTTP against our local fixture only; no provider requests or live voice."""
import asyncio
import json

import httpx

from voice_app.assistant_client import AssistantClient, CATALOG_CODES


async def main():
    async with httpx.AsyncClient(trust_env=False, timeout=5) as http:
        health = await http.get("http://127.0.0.1:8002/health")
        health.raise_for_status()
        assert health.json()["synthetic_api"] is True
        assert health.json()["live_advice_enabled"] is False
        client = AssistantClient("http://127.0.0.1:8002")
        passed = []
        for code in sorted(CATALOG_CODES):
            result = await client.ask("Fictional transport test: show the fixed document excerpt.", code)
            assert result.error is None and result.reply.status == "answered"
            assert result.reply.answer.startswith("TEST FIXTURE")
            assert result.reply.citations[0].id == "procedure-" + code.replace(".", "-")
            assert "ma_thu_tuc=" + code in str(result.reply.citations[0].url)
            assert not result.available_for_live_advice
            passed.append(code)
        unavailable = await client.ask("[test:unready]", "1.001146")
        assert unavailable.error == "assistant_http_409" and unavailable.reply is None
        missing = await client.ask("[test:no-context]", "1.001146")
        assert missing.reply.status == "insufficient_context"
        for body, expected in (({"message":"Fictional test"}, "needs_clarification"),
                ({"message":"Fictional test", "procedure_code":"1.004194"}, "out_of_scope")):
            response = await http.post("http://127.0.0.1:8002/assistant/chat", json=body)
            assert response.json()["status"] == expected
            assert response.headers["x-hoso-synthetic-fixture"] == "1"
        print(json.dumps({"real_local_http":True, "synthetic_api":True, "documents_passed":passed,
                          "clarification_no_context_out_of_scope_409":"passed", "live_voice_connected":False}))


if __name__ == "__main__":
    asyncio.run(main())
