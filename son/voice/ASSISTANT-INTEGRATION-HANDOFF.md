# VOICE-01: assistant dependency assessment

Owner: Son. Status: **received / adaptation required**, not **tested compatible**.
Branch: `codex/son/voice-01-browser-conversation`.
Existing voice implementation: `45943572a225fa0cd628d5977a04e66ad5c9dcc8`.
Dependency inspected: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`, fetched from
`origin/codex/procedure-foundation` without checkout, merge or server restart.

## Observed interface

Read via `git show`: `docs/assistant.md`, `api/assistant.py`,
`docs/procedure-profiles.md`, `data/README.md` at that exact dependency SHA.

`POST /assistant/chat` accepts `message` (2–1000 characters), optional
`procedure_code` (pattern `digit.six-digits`), and up to 12 history entries
(`user` or `assistant`, content 1–8000 characters). It is stateless, non-streaming
and returns `status`, `answer`, `citations` (`id`, `title`, `url`), and nullable
`model`. Statuses: `answered`, `needs_clarification`, `insufficient_context`,
`out_of_scope`. An explicit code bypasses search, not context validation. Without
it, search depends on embeddings/calibration readiness; that readiness has not
been demonstrated here. Retrieval uses the current message, not history.

No evidence avoids a model call. Error paths include 404 context missing, 409
context/retrieval gate not ready, 413 oversized context, 422 bad request, 503
configuration/retrieval unavailable, 502 unusable provider output, 504 timeout.
Provider timeout is 60 seconds; no automatic retry is documented. Citation checks
do not establish semantic entailment or human approval. No runtime compatibility
test was executed for this assessment.

## Blocking scope decision

**Update after this assessment:** Son explicitly selected alignment with Vincent
for the first test. The Realtime profile now targets foreigner temporary-stay
extension, with `1.001146` as a candidate only. See `FOREIGNER-DEMO-HANDOFF.md`.
The historical mismatch below describes the prior state. The domain choice is
resolved for this test; reviewed evidence/version/checklist and API orchestration
remain pending. No runtime compatibility with Vincent is claimed.

Current scope doc and deterministic voice routing target `1.004194` registration
and `1.002755` renewal; the Realtime persona targets the same citizen journey.
The dependency catalog lists `1.001146`, `1.003326`, `1.003342`, `1.000771`, covering
foreigner/visa-related procedures with NA5. These are not interchangeable with
the citizen journey. Do not map by the word “renewal,” reuse NA5 as CT01, or label
any published profile reviewed merely because it exists.

Son must choose the demo domain with the team: retain the citizen journey and
request corresponding reviewed records, or explicitly rescope to a selected
foreigner procedure. The latter needs coordinated scope, voice persona/routing,
eligibility clarification, form and report changes. This handoff makes no domain
decision and enables neither route for factual advice.

## Proposed consumer adaptation, after gates are resolved

Keep Realtime as the conversation transport. A server-side voice adapter could
send a bounded, non-personal question plus a confirmed allowed code and bounded
history to the existing endpoint. It must preserve the code on follow-ups and ask
for clarification when a standalone follow-up is ambiguous. Do not build another
RAG pipeline, expose provider keys, or forward unrestricted transcripts/history.
Current Realtime has no tools; tool/sideband orchestration, cancellation on hangup,
bounded waiting and protection against stale responses still require design and
implementation. Do not substitute a second concurrent assistant or speak a draft
before its status and evidence have been checked.

Handle all four statuses explicitly. Errors/no match/unready context produce an
availability explanation, never a fallback legal answer from model memory.
Treat answer text as untrusted plain text; preserve citation linkage outside
speech instead of speaking raw bracket IDs or trusting generated links. VI/EN
language handling needs agreement: the request has no explicit language field.

The chat response does **not** expose a dedicated canonical selected procedure
code, pinned procedure/profile version or baseline, exact source snapshot/hash,
human-review status tied to hashes, or versioned checklist/report identity.
Source IDs must not be parsed as a replacement contract. Supporting profile
endpoints are documented, but resolving a separate current profile after chat
does not prove both used the same snapshot. Vincent must specify the pinned,
reviewed evidence handoff; Son and Kim must consume the same version/checklist
before any live voice-to-report claim. Kim app.v1/Clerk and owner/approval checks
remain separate pending integrations; a public voice cookie is not identity.

## Offline consumer tests to implement with an agreed adapter

- Fake HTTP responses for every status/error; no provider/network required.
- Reject unsupported or mismatched codes; retain confirmed code across turns.
- Bound question/history and handle ambiguous follow-ups without guessing.
- Reject answered output lacking usable citations or required pinned review data.
- Treat HTML, URLs and source text as data, never executable instructions.
- Cancel on hangup; ignore stale/wrong-session responses and avoid automatic retries.
- Verify no personal identifiers, dossier values, credentials or transcripts leak
  to logs; deny personal access without the agreed server authorization.
- Assert voice/report share exact approved procedure version and checklist once
  that contract is supplied; do not invent its schema in these tests.

These are proposed tests, not executed tests or compatibility evidence. This
documentation-only increment ran no API, collector, RAG, model or paid call and
launched no assistant/server. No product UI, board or Son status file was edited.
The initial broad fetch reported a concurrent remote-ref update error; the
subsequent targeted branch fetch succeeded with the exact SHA above. Existing
checkout, unrelated local prototypes and servers were preserved.
