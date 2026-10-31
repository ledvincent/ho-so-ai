"""Bounded real HTTP journey with fictional questions; no mic/audio validation.

--live permits at most three paid document-model requests. No automatic retries.
Only aggregate evidence is printed; no cookies, signed state or transcripts.
"""
import argparse
import asyncio
import json
import time
import httpx


async def run(language):
    base = "http://127.0.0.1:8003"
    vi = language == "vi"
    async with httpx.AsyncClient(base_url=base, headers={"Origin":base}, timeout=190, trust_env=False) as client:
        session = await client.post("/api/voice/session", params={"language":language})
        session.raise_for_status()
        observations = []
        async def ask(question, **args):
            started = time.monotonic()
            response = await client.post("/api/voice/rag", json={"question":question, **args})
            response.raise_for_status()
            body = response.json()
            assert "retrieval_state" not in body
            observations.append({"status":body.get("status"), "error":body.get("error"),
                                 "procedure_code":body.get("procedure_code"),
                                 "citations":len(body.get("citations",[])), "documents":len(body.get("documents",[])),
                                 "choices":len(body.get("choices",[])), "seconds":round(time.monotonic()-started, 1)})
            return body
        try:
            first = await ask("Tôi muốn gia hạn tạm trú ở Việt Nam." if vi else "I need help extending my stay in Vietnam.")
            assert first["status"] == "needs_clarification" and first["choices"]
            assert not first.get("procedure_code"), "Must not select a procedure before clarification"
            # Select only an actual returned label and preserve its exact ID.
            choice = next(c for c in first["choices"] if "provincial" in c["label"].lower() or "cấp tỉnh" in c["label"].lower())
            selected = await ask("Trong ví dụ giả định, cơ quan bảo lãnh hướng dẫn nộp cấp tỉnh." if vi else
                                 "For this fictional example, the sponsor said provincial immigration office.",
                                 clarification_answer=choice["id"])
            assert selected.get("procedure_code") == "1.001146", observations
            # The selection resolves the original general question. Ask paperwork
            # as its own turn, as specified by Vincent's signed-state semantics.
            documents = await ask("Tôi cần chuẩn bị những giấy tờ gì?" if vi else "What documents do I need?")
            assert documents.get("status") in {"answered", "insufficient_context"}, observations
            assert documents.get("procedure_code") == "1.001146" and documents.get("citations") and documents.get("documents"), observations
            followup = await ask("Thời gian giải quyết là bao lâu?" if vi else "How long does it take?")
            assert followup.get("status") in {"answered", "insufficient_context"}, observations
            assert followup.get("procedure_code") == "1.001146" and followup.get("citations"), observations
            print(json.dumps({"language":language,"observations":observations,"passed":True,"scope":"real HTTP and document model; no audio"}))
        finally:
            await client.delete("/api/voice/session")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--language", choices=["en","vi"], default="en")
    args = parser.parse_args()
    if not args.live:
        print("Not run. --live authorizes at most three paid document-model calls.")
    else:
        asyncio.run(run(args.language))
