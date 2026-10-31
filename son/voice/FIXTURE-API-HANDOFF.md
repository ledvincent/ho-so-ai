# VOICE-01: real local HTTP fixture using four upstream documents

Owner: Son. Task: VOICE-01. Status: in progress; this increment ready for review.
Branch: `codex/son/voice-01-browser-conversation`. Local only, no push or merge.

User authorization: use a fictional API with the four documents while Vincent's
API is unfinished. Added `evals/fake_assistant_api.py`,
`evals/fixture_http_smoke.py`, and README instructions under `son/voice/`.
This is a consumer-owned deterministic test double, not a new RAG pipeline or
assistant model. Vincent's implementation and shared contract are unchanged.

The API runs at `http://127.0.0.1:8002`, `/docs` is the developer test editor.
It reads the four real `procedure.json` files at pinned upstream commit
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4` via Git. Explicit code selects a fixed,
clearly labelled unreviewed excerpt and original citation; no semantic retrieval,
translation, legal interpretation, review approval or form choice occurs. Excerpts
are at most 2000 characters and explicitly marked potentially incomplete.
Request/response fields follow the observed assistant chat transport shape;
fixture-only test message markers exercise no-context and 409 paths. No model,
credentials, database, persistence or request access logging. Use fictional inputs.

Verification executed:

- `son/voice/.venv/Scripts/python.exe son/voice/evals/fixture_http_smoke.py`:
  real HTTP through `AssistantClient` to the running fixture; **4/4 documents pass**
  code/citation checks, plus clarification, no-context, out-of-scope and HTTP 409.
- `son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -q`:
  **52 passed**, existing Starlette dependency deprecation warning only.
- No provider call or live microphone evaluation. Existing servers on 8000/8001
  preserved; fixture remains running separately on loopback 8002 for user testing.

Vincent: **received / adaptation required**. Local fixture HTTP transport is
**tested compatible** only with our consumer and test double, not his runtime.
The voice on 8001 still does not invoke the fixture or speak draft documents.
`DraftResult.available_for_live_advice` remains false. Real orchestration,
validated/pinned evidence and common checklist identity are still required.
Kim app.v1/Clerk/report: notice **received / adaptation required**; identity and
report integration remain **blocked** pending delivered agreements, not tested.
No UI product, board or Son status change; no team message sent.

Next: use the fixture to develop bounded/cancellable voice tool orchestration,
keeping synthetic output distinct from factual advice. Replace the test origin
with Vincent's actual local service once delivered and repeat consumer checks
without bypassing its review/readiness gates. A separate source review is still
required before claiming factual voice/report compatibility.
