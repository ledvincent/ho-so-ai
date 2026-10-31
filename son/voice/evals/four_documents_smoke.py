"""Read four pinned upstream documents; simulate transport, never legal advice.

Run from the repo root: python son/voice/evals/four_documents_smoke.py
No network, database, provider key or document import pipeline.
"""
import asyncio
import json
from pathlib import Path
import subprocess

import httpx

from voice_app.assistant_client import AssistantClient, CATALOG_CODES

REVISION = "9386f428e6794acd0a8b9e4cb3cc759bf5c989b4"
ROOT = Path(__file__).resolve().parents[3]


async def main():
    observations = []
    for code in sorted(CATALOG_CODES):
        path = f"data/procedures/{code}/procedure.json"
        raw = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}",
                                       "show", f"{REVISION}:{path}"], cwd=ROOT)
        document = json.loads(raw)
        assert document["code"] == code and document["procedure_code"] == code
        sections = document["document_json"]["sections"]
        assert sections and document["sha256"] and document["source_url"]
        excerpt = next(section["text_verbatim"] for section in sections if section.get("text_verbatim"))
        # Genuine document excerpt, explicitly wrapped as a synthetic response.
        # No inference that the source, interpretation or form is human-approved.
        citation_id = "procedure-" + code.replace(".", "-")
        body = {"status":"answered", "answer":"SYNTHETIC TRANSPORT FIXTURE: " + excerpt[:2000] + f" [{citation_id}]",
                "citations":[{"id":citation_id, "title":document["name"], "url":document["source_url"]}], "model":None}
        requests = []
        def handle(request):
            requests.append(json.loads(request.content))
            assert request.url.path == "/assistant/chat"
            return httpx.Response(200, json=body)
        result = await AssistantClient("http://localhost:8999", transport=httpx.MockTransport(handle)).ask(
            "For a fictional developer test, what source context is available for this procedure?", code)
        assert requests == [{"message":"For a fictional developer test, what source context is available for this procedure?", "procedure_code":code, "history":[]}]
        assert result.error is None and result.reply.answer == body["answer"]
        assert str(result.reply.citations[0].url) == document["source_url"]
        assert not result.available_for_live_advice
        observations.append({"code":code, "sections":len(sections), "source_sha256":document["sha256"],
                             "request_and_citation_preserved":True, "live_advice_enabled":False})
    print(json.dumps({"upstream_commit":REVISION, "mode":"real documents, mocked API; no model or live voice", "documents":observations}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
