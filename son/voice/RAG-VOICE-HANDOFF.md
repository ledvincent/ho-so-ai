# VOICE-01: current RAG contract consumer

Owner: Son. Branch: `codex/son/voice-01-browser-conversation`.
Code: `89609f3fd68dca496bc60a8bc8834345ad4fb209`, local, not pushed.
Status: implementation ready for review; live integration blocked on an accessible
Vincent API origin. User confirmed the API code was pushed but supplied no URL.

Dependency inspected by read-only Git:
`7c78ec4a731a2200d834f40e530eb0f2b5b9d38e` on `codex/procedure-foundation`,
`docs/assistant.md`, `docs/rag.md`, `api/assistant.py`. This version supports
clarification choices, signed retrieval state, selected code and document cards.
Source readiness remains enforced by Vincent; a published index is not approval.

Delivered paths under `son/voice/`: `src/voice_app/rag_client.py`,
`static/rag-tool.js` (inside `src/voice_app`), updated Realtime client/harness,
`evals/live_rag_voice.py`, parametrized development gateway, README and tests.
The new mode is `documents=rag`, using port 8003 only after explicit startup with
`--assistant-url`. No upstream URL is guessed and no service is launched against
fake data under a real-mode label. Existing 8000/8001/8002 services preserved.

The consumer keeps signed state and four previous messages server-side, validates
returned shape/citation membership, offers server-provided choices, supports an
explicit reset for changed intent, and clears invalid state on 409. Cancellation,
session end/expiry and separate cookies prevent cross-call state reuse. It passes
no signed token or form action to the model. Model tool output carries the answer,
choices and citations; complete answer/source text appears in the diagnostic log.
The model is instructed to preserve conditions/quantities and avoid inventing
facts when retrieval fails. Prompts do not prove semantic faithfulness.

The API can return document cards, but this increment does not render forms or
execute their actions. Kim's product interface and the separate integration chat
remain untouched. The latter was observed actively adapting UI-03 in its own
checkout; this increment is confined to the voice component and its handoff.
No collector/RAG producer, board or manager-owned Son status changes.

Verification: **62 Python tests pass**; ordinary, fixture and new RAG browser
smokes pass with mocked media/providers. Covered signed-state continuity, invalid
choice, citation failures, 409 clearing, cancellation, concurrent lookup exclusion,
session isolation, cookie/origin gates, no fixture fallback and tool result/source
display. Profile parity and whitespace checks pass. Existing Starlette dependency
deprecation warning remains. No new paid call, real RAG query or live voice/RAG
test was performed; the deployable backend endpoint is not yet available here.

Vincent: **received / adaptation required**; consumer behavior **tested compatible
with synthetic responses matching the inspected contract**, not his runtime.
Kim app.v1/Clerk and UI-03: **received / adaptation required**, no personal access,
form approval, submission or report integration claim. Pinned review/checklist
identity for voice-to-report remains a separate unresolved shared contract.

Next required input: Vincent's actual reachable API origin, and its authentication
scheme if protected (never an OpenAI key in chat). Then check `/assistant/setup`
and exercise clarification -> selected sourced answer -> follow-up -> correction,
before a single bounded synthetic live voice pilot. Do not start or rebuild his
database, approve sources, or replace readiness checks with raw Git documents.
Run command and sample question are documented in the component README.
