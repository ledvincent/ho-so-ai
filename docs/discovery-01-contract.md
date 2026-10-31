# DISCOVERY-01: Vincent discovery consumer routes

Draft consumer integration seam, 2026-10-31. Backend owner: Kim. UI owner:
the existing frontend chat. Producer: Vincent, exact source
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`. Base UI-02 snapshot:
`edb3c1cd4d41a5ac1ae8b0125e84c197862145a5`.

This maps Vincent's existing responses; it does not define a new authoritative
procedure schema, infer procedure identity from prose, or replace his retrieval.
The backend owns only new Next server handlers/helpers and tests. No frontend
views, existing field-assist endpoints or shared database changes in this task.
Manager alone updates Kim's team status.

## Consumer flow

1. Verify the existing login session. Start a general procedure conversation through
   `/api/discovery/chat`, which forwards to Vincent's existing grounded assistant.
   Render his answer/citations as text and safe links; do not derive routing from prose.
2. Call structured search and display the returned candidate names/codes. Keep `not_found`
   distinct from unavailable retrieval. Multiple candidates require a choice;
   even one result requires explicit user confirmation.
3. After confirmation, load that exact procedure. Display its requirements and
   original forms, preserving source/revision/review information. If several forms
   exist, let the user choose an actual association; never select the first blindly.
4. Request the schema for that exact procedure/form association. Only a supported,
   validated workflow enables its matching form editor. Other forms remain readable
   originals. Draft status never authorizes official filled-document download.

There is no server conversation or selection store. The UI owns confirmation and
must discard stale responses after a query edit, selection change or account
transition. GET requests inspect data; they do not record confirmation. Neither
`new visa` nor a search score implies `1.001146` or `1.003342`. Never parse
`/assistant/chat` prose or citation IDs to select a procedure, form or version.
After the user confirms a code, retain it in every Q&A follow-up. Before confirmation,
omit it; the assistant may discuss a candidate, but that does not confirm selection.

## Exact browser routes

Every route uses the existing verified application session, no-store responses
and a fixed server-configured producer origin. The browser receives no upstream
credential. Session cookies/Bearer tokens are never forwarded to Vincent.

| Browser route | Producer request | Consumer result |
| --- | --- | --- |
| POST `/api/discovery/chat` with `{message,procedure_code?,history}` | POST `/assistant/chat` with the same validated body | Existing `{status,answer,citations:[{id,title,url}],model}`; never a form patch or structured procedure selection |
| POST `/api/discovery/search` with `{query:string}` | POST `/search` with the same bounded query | Existing `{status:"found"|"not_found",results:[{code,name,score,similarity}]}`, at most 5 candidates |
| GET `/api/discovery/procedures/{code}` | GET `/procedures/{code}` | Existing snapshot/forms/requirements/profile shape; validated code and form relationships |
| GET `/api/discovery/procedures/{code}/profile` | GET procedure, then GET `/procedures/{code}/profile` | Existing structured profile, evidence, criteria and comparisons; baseline/run/output hash must match the current snapshot |
| GET `/api/discovery/procedures/{code}/forms/{sha256}/original` | GET procedure, then GET `/forms/{sha256}/original` | Bounded attachment with verified SHA256; never an automatic upstream URL redirect |
| GET `/api/discovery/procedures/{code}/forms/{sha256}/analysis` | GET procedure, then GET `/forms/{sha256}/analysis` | Existing analysis shape, matched hash and association |
| GET `/api/discovery/procedures/{code}/forms/{sha256}/schema` | GET procedure and analysis, then explicit supported workflow schema | Existing producer workflow schema, only when its code, form hash, revision and mapping match the supported source |

`code` is a procedure identifier such as `1.001146`; hashes are 64 lowercase hex
characters. Query-string parameters and arbitrary URL/path selectors are rejected.
Search accepts only `query`, trimmed length 2..1000, body <=4096 bytes, JSON with
exact configured Origin. Cross-site requests are rejected; same-origin GET may
omit Origin. All routes independently check the session before producer access.

Chat accepts only Vincent's keys: trimmed `message` length 2..1000; optional/null
`procedure_code`; optional `history` (default empty), at most 12 turns with only
`role:"user"|"assistant"` and trimmed `content` length 1..8000. Body <=400 KiB to
accommodate bounded multi-byte text. The proxy keeps no history. Response statuses
are `answered`, `needs_clarification`, `insufficient_context`, `out_of_scope`.
Answers are bounded to16000 characters, citations to20 safe unique IDs/URLs and
500-character titles, model to256 characters or null. An `answered` response must
include citations. This validation does not prove the answer is legally correct.

In procedure responses, each non-null `original_download_url` must exactly equal
the producer path `/forms/{that form's hash}/original`; the adapter rewrites it
to the protected browser route above. It never fetches a returned URL. Other
source links must use safe HTTP(S) syntax with no credentials; render text as text
and links as links, never as HTML. `field_schema_ref` remains a repo-relative
metadata reference, not a fetchable generic endpoint. Original downloads are
attachments with `nosniff`; byte hash is checked before returning them.

The explicit workflow allowlist currently contains only procedure `1.001146`
with the NA5 original hash from the pinned source snapshot
`a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751`.
Its schema must match the pinned field definitions, fixed values and review/version
metadata. A different procedure sharing the same file does not gain NA5 filling.
The current procedure must also have `analysis.facts_ready === true`; a parsed
snapshot with blocked/unavailable analysis cannot enable filling. Originals remain
inspectable with their actual readiness/review labels. Unsupported or changed
mappings fail closed. No workflow preview/download proxy
is exposed in this bounded discovery checkpoint. Originals may be DOCX or another
supported attachment type; original download does not imply an inline PDF preview.

## Configuration, errors and limits

Set server-only `HOSO_VINCENT_API_URL` to the exact producer origin: HTTPS, or HTTP
on loopback. No URL credentials, base path, query or fragment; no redirects. It has
no default. Missing/invalid config ->503 `DISCOVERY_UNAVAILABLE`; no fixture fallback.
The live producer URL, loaded PostgreSQL data, index and calibration are currently
not supplied. No producer startup, collection, migration or paid call is authorized
by this consumer implementation. Search itself can invoke Vincent's embedding
provider once a live service is supplied; do not call it as an automatic healthcheck.
Chat may invoke his configured model. All implementation tests use labeled fixtures,
with zero live search/chat/provider calls; the prior three-call smoke budget is used.

Errors have `{detail:{code:"STABLE_CODE"}}`; raw provider exceptions/bodies are
never shown. Existing profile/form app.v1 error shapes remain unchanged.

| Status | Code / meaning |
| --- | --- |
| 400 / 413 / 422 | `INVALID_REQUEST` / `REQUEST_TOO_LARGE` / `INVALID_REQUEST` |
| 401 / 403 | `UNAUTHENTICATED` / `ORIGIN_FORBIDDEN` |
| 404 | `DISCOVERY_NOT_FOUND` for missing producer data or non-associated form |
| 409 | `DISCOVERY_NOT_READY`, `WORKFLOW_UNSUPPORTED` or `WORKFLOW_VERSION_MISMATCH` |
| 429 | `RATE_LIMITED`, with Retry-After |
| 502 | `DISCOVERY_INVALID_RESPONSE` for invalid shapes, identity/hash mismatch, unsafe links or redirects |
| 503 | `AUTH_UNAVAILABLE` or `DISCOVERY_UNAVAILABLE` |
| 504 | `DISCOVERY_TIMEOUT` |

Consumer limits: 1 MiB per JSON response, 10 MiB per original, 20-second upstream
timeouts (65 seconds for chat), no automatic retries. Per-user process-local request limiting protects
this single-process checkpoint; it is not a distributed deployment rate limiter.
Limits per60seconds are60 total requests,12 searches and8 chat requests, with at
most1024 live user buckets; each bucket stores only a hashed identity and counters.
LOCAL authentication remains loopback-only and public hosting identity is separate.

Tests will use explicitly synthetic fixtures for found/multiple/not-found,
missing configuration, source errors, association/hash failures and unsupported
workflows. Fixture tests do not establish a working live index or legal currency.
UI-02 ports 3018/8018 and its source checkout remain untouched.
