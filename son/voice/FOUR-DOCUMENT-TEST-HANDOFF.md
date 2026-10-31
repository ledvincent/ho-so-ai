# VOICE-01: four real documents, offline consumer test

Owner: Son. Branch: `codex/son/voice-01-browser-conversation`.
Task status: in progress. This increment is ready for review, local only.

The user requested using Vincent's four documents for a first test. Added a
server-side consumer in `src/voice_app/assistant_client.py`, six unit tests in
`tests/test_assistant_client.py`, and `evals/four_documents_smoke.py`, plus README
instructions. Paths are relative to `son/voice/`. No UI, collector, retrieval
pipeline, contract producer, board/status, key storage or existing server changed.

The smoke reads real upstream `procedure.json` files through read-only `git show`
at `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`. Codes tested:
`1.000771`, `1.001146`, `1.003326`, `1.003342`. Each contains six captured sections.
The API fixture is explicitly synthetic and contains an excerpt from that actual
document and its original title/URL. Assertions verify code isolation, empty
history, exact answer transport and source URL preservation. No generated legal
answer, legal translation, new approval or retrieval-quality claim follows.

Consumer: explicit localhost origin only, fixed `/assistant/chat`, allowlisted
codes, bounded question, no history or automatic retries, timeout/error handling,
schema and duplicate/missing citation checks. Provider error bodies are not
returned. Answers remain untrusted plain text; this adapter provides no renderer
or speech path. Its local `DraftResult` is not a shared procedure/report schema.
`available_for_live_advice` is always false because chat does not supply the
agreed pinned human-review/checklist identity. No personal-data tools enabled.

Verification executed:

- `son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -q`:
  **52 passed**, existing dependency deprecation warning only.
- `son/voice/.venv/Scripts/python.exe son/voice/evals/four_documents_smoke.py`:
  **4/4 passed**, real upstream files, mocked API, no network/model/database.
- Read-only local HTTP probes: ports 8000 and 8001 both identify as
  `public_dialogue_demo`, no `/openapi.json`; neither is the expected Vincent API.
  No service was started or stopped and no paid call was made.

Vincent dependency: **received / adaptation required**. The consumer has offline
test evidence, but is **not tested compatible** with his running backend. The
running API URL was requested from Son; no credentials requested in chat.
Next: verify explicit-code context readiness against that actual service, then
agree orchestration and reviewed evidence/version semantics before live advice.
Do not replace his readiness gates with raw Git files in the voice prompt.

Kim app.v1/Clerk/report: notice **received**, **adaptation required**; live personal
access and shared report integration remain **blocked** pending delivered identity,
approval and pinned checklist interfaces. This test establishes no end-to-end
voice-to-report compatibility. Existing foreigner persona remains unchanged.
