# Frontend integration audit: NA5 / 1.001146

Audited 31 October 2026. **The local integration bundle is ready for Kim. A committed/hosted
release has not been delivered.** This document describes the
current working tree. Start with [Kim's handoff guide](kim-start-here.md) and
`output/kim-backend-demo.zip` (source, database snapshot, contracts and file hashes).

## Version and verification

- Branch: `codex/procedure-foundation`.
- Base commit: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`.
- This is the foundation base SHA, not the delivered integration commit. Use the
  commit from the handoff message and its verification report. Database snapshots
  and generated bundles remain separate from Git.
- No reachable HTTPS deployment has been verified or delivered.
- The document changes include regression checks for a second, different schema.
  Earlier unit suite: **151 passed** on the working tree; model calls are mocked there.
- The live demo uses `gpt-6.1-sol`, medium effort. See the [demo walkthrough](assistant-demo.md)
  for the live HTTP suite and result paths. These are dirty-working-tree checks,
  not evidence of a delivered release at the base SHA.
- Server-rendered paragraph citations fix the earlier missing-marker 502.
  Focused source context, document cards and partial form validation are integrated.
- The real NA5 preview contains three pages. The persisted template remains
  `draft`; final download returns **409**. No review gate is mocked.

Reproduce the audit on a configured machine:

```powershell
uv run python -m scripts.check_frontend_handoff --live-assistant
```

This makes one real model request and writes `output/frontend-handoff-smoke.json`,
including source fingerprints, base SHA, dirty-tree status, release metadata and
the actual public-question response. It omits credentials and signed tokens.
It exercises the ASGI application in-process, not portal authentication, CORS or
HTTPS. Without `--live-assistant`, generation is explicitly skipped. A passing
contract check still needs manual review of answer accuracy and language.

The earlier ignored `tmp/refinement/` experiments are not release evidence.
Current checks exercise the real API and saved procedure data.

## Startup and data portability

Requirements: Python 3.12, uv, Docker with Compose. Current local startup:

```powershell
uv sync --locked
# Create .env from .env.example only if .env does not already exist.
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
```

OpenAPI: `GET /openapi.json`; interactive reference: `GET /docs`.
`GET /health` is liveness only. `GET /assistant/setup` reports configuration
presence, index presence and the procedure catalog; it does not validate a key or
prove an answer can be generated.

**These commands alone do not populate a fresh database.** Migrations create
tables. The existing JSON exports have no tested round-trip importer. Rerunning
ingestion fetches live pages and calls extraction models, so it will not recreate
the exact reviewed snapshots, identifiers or embeddings.

The current database serves four procedures from release
`91d293bc-b145-4853-851e-e043d6f395d9`: 205 retrieval items, schema migration
`0009`, BGE-M3 with 1024 dimensions. Its model digest is
`7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab` and its
development routing threshold is `0.7572550427096718`.

| Data | Availability |
| --- | --- |
| Public procedure HTML/JSON, profiles, runs, original forms, blank PDFs, NA5 workflow and bundled filling font | Tracked in Git under `data/` and `api/assets/` |
| RAG code/migrations and scoped evidence review files | Present locally but not yet committed |
| Populated PostgreSQL database, source/profile IDs, review state, vectors, serving pointer | Docker Compose `hoso_pgdata` volume; not in Git |
| BGE-M3 weights | Docker Compose `hoso_models` volume; not in Git |
| `data/_store/` | Ignored; current database/export paths reference this content-addressed HTML store |
| `data/parsed/`, `data/derived/`, `data/inbox/` | Ignored intermediate artifacts; inventory dependencies when packaging |
| `tmp/refinement/`, `output/`, review PDFs and smoke reports | Ignored local experiments/generated outputs |
| `.env` and credentials | Ignored; provision separately |

The simplest exact demo transfer is a PostgreSQL custom-format snapshot plus a
checksum manifest and all referenced local artifacts, including `data/_store/`.
Preserving database IDs also preserves the scoped reviews and release membership.
The bundle is now in `output/kim-backend-demo.zip`. A fresh-database restore on
the existing machine passed all eight smoke checks, including live generation;
see `handoff/restore-smoke.json` inside the ZIP. A separate-machine restore has
not been tested. Restore
into a new empty database, then verify migration, file hashes, release and model
digest. Do not overwrite a teammate's existing database.

For a deliberate rebuild after loading source/profile data, use the
[RAG build/work/publish commands](rag.md). Install the matching model first with
`docker compose exec embeddings ollama pull bge-m3`, then verify its digest;
the tag alone is not a pin. A different model or new ingestion requires a new
release and evaluation. Neither indexing nor restoring a database approves a form.

## Current assistant HTTP contract

`POST /assistant/chat`, `Content-Type: application/json`:

| Request field | Contract |
| --- | --- |
| `message` | Required string, 2–1000 characters after trimming |
| `procedure_code` | Optional/null string matching `^\d\.\d{6}$`; use `1.001146` for the shared demo |
| `history` | Default `[]`; at most 12 `{role, content}` turns; role is `user` or `assistant`, content 1–16000 characters |
| `retrieval_state` | Optional/null signed string, at most 12000 characters |
| `clarification_answer` | Optional/null string, at most 1000 characters; use a returned choice ID |

Unknown request/turn fields are rejected. Client-supplied sources, system prompts,
user IDs, form values or adapter patches are not part of this request schema.

Every successful HTTP 200 response has these fields:

| Response field | Contract |
| --- | --- |
| `status` | `answered`, `needs_clarification`, `insufficient_context`, or `out_of_scope` |
| `answer` | Text, with `[source-id]` markers when citing evidence |
| `citations` | Array of `{id, title, url}`; may be empty |
| `model` | String or null; null when generation was not needed |
| `choices` | Array of `{id, label}`; may be empty |
| `retrieval_state` | Signed string or null |
| `procedure_code` | Selected procedure code or null |
| `documents` | Server-owned document cards with conditions, counts, citation IDs and optional version-bound form actions; see [demo contract](assistant-demo.md) |

Render text safely and resolve citation markers through the returned citation
array. Citation IDs are opaque; do not hard-code them. Display clarification
choices when present, then return `retrieval_state` and the selected
`clarification_answer`. During clarification omit `procedure_code`: an explicit
code starts a new selection and bypasses the pending choice. After selection,
retain state or the selected code for follow-ups. Start without either to change
procedure. Signed clarification state expires after 30 minutes.

Errors use `{"detail":"..."}` except request-validation 422 responses, whose
`detail` is an array of validation errors. Do not parse English error strings as
stable identifiers; machine-readable error codes have not been added.

| HTTP | Meaning/action |
| --- | --- |
| 404 | Procedure context lookup failed |
| 409 | Invalid/expired conversation state, changed release membership, or evidence/index not ready; offer restart or temporary-unavailable guidance |
| 413 | Serialized context exceeds 140000 characters |
| 422 | Invalid request |
| 502 | Provider HTTP failure, refusal, incomplete output, invalid generated schema or citations |
| 503 | Missing generation configuration or retrieval/database unavailable |
| 504 | Provider timed out; configured timeout is 120 seconds |

No automatic generation retries or streaming are implemented. Keep the portal's
upstream timeout longer than the model timeout plus retrieval overhead. Retrieval
can take longer during an embedding cold start.

The smoke's exact example request is:

```json
{
  "message": "How long does procedure 1.001146 take to process? Please answer in English.",
  "procedure_code": "1.001146",
  "history": []
}
```

The captured primary procedure supports up to five working days after receiving
the complete dossier. Expected citation: the source registered for
`https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.001146`.
The live suite checks that the answer cites official evidence and says five working
days from receipt of a complete dossier. Generated wording can vary. Citation IDs
are opaque and must be resolved through the response array.

## NA5 form endpoints

| Endpoint | Request / response |
| --- | --- |
| `GET /documents/na5-provincial-stay-extension/schema` | JSON: procedure/form identity, `template_version`, `template_sha256`, revision, review/download status, `fields`, `fixed_values` |
| `GET /documents/na5-provincial-stay-extension/template` | Verified blank PDF |
| `GET /documents/na5-provincial-stay-extension/template-pages` | Three PNG page data URLs and template version |
| `POST /documents/na5-provincial-stay-extension/validate` | Partial string `values`, optional `template_version`; normalized values, missing fields, preview readiness |
| `POST /documents/na5-provincial-stay-extension/preview-pages` | Same complete values as preview; rendered PNG pages and `X-Review-Token` |
| `GET /documents/na5-provincial-stay-extension/example` | Explicitly fictional example values for local testing |
| `POST /documents/na5-provincial-stay-extension/preview` | `{"values": {"field_id": "text value"}}`; returns PDF bytes, `Cache-Control: no-store`, `X-Review-Token` |
| `POST /documents/na5-provincial-stay-extension/download` | `{"values": {...}, "review_token": "...", "confirmed": true}`; returns PDF attachment when all gates pass |

Schema revision: `70/2026/TT-BCA`, effective `2026-07-01`, **43 field definitions**,
`review_status: "draft"`. The workflow fixes `request_type: "stay_extension"`.
Fields describe IDs, labels, types, ownership/grouping, requiredness, conditional
`when`, choices, length limits, manual areas and PDF placements. Dates use
`YYYY-MM-DD`. All supplied values are strings. Unknown/inapplicable fields,
missing required values, invalid dates/choices and text that cannot fit are
rejected. Manual signature/stamp areas remain manual. The existing fictional
complete example is `tests/fixtures/na5-example.json`.

The preview endpoint currently validates a complete applicable field set. It is
**not** a partial-draft or field-patch endpoint. Kim's adapter must not fabricate
missing values just to obtain a preview. Use `/validate` for incomplete values. Chat now returns form actions. There is
no persisted form draft or patch-storage API. Include `template_version` from the
card/schema in validation, preview and download requests; stale versions return 409.

Preview tokens last 15 minutes and are bound to normalized values plus the
template/spec digest. They are signed, not encrypted, and contain the normalized
values; keep them out of logs and URLs. Changing values requires a new preview.
Download requires the exact token, `confirmed: true`, and an approved template.
These tokens are **not authentication credentials**.

Current downloads return 409 because the template awaits human review.
After approval, unconfirmed/invalid/expired/mismatched preview requests return
422. Successful downloads return `application/pdf` and
`Content-Disposition: attachment; filename="NA5-filled.pdf"`.
Do not bypass this gate for a demo. A preview-only demo is available with
fictional values. See [the human review procedure](na5-workflow.md).
Template placement approval is separate from resolving which form edition the
receiving authority accepts.

## Authentication and service configuration

The current FastAPI service has **no caller authentication, authorization,
rate limiting or CORS middleware**. There is no application bearer-token env var.
Kim's portal login does not protect a directly exposed backend.

Recommended demo routing: the authenticated portal server proxies to this backend
on a private network or loopback on a shared host. The portal checks the user
session; network access restricts the API to that server. If the services cannot
share a private network, add verified service authentication and HTTPS before
exposure. Direct cross-origin browser calls additionally need an explicit origin
allowlist and `X-Review-Token` exposed through CORS. None of this is configured yet.

| Environment variable | Role |
| --- | --- |
| `DATABASE_URL` | PostgreSQL/psycopg connection string; Compose development port is 55432 |
| `ASSISTANT_MODEL` | `gpt-6.1-sol` for the current demo |
| `ASSISTANT_REASONING_EFFORT` | `medium`; set `low` to compare lower-latency reasoning |
| `ASSISTANT_BASE_URL` | Defaults to `https://api.openai.com/v1` |
| `ASSISTANT_API_KEY` | Server-only generation credential |
| `OPENAI_API_KEY` | Ingestion credential; assistant fallback only at the default OpenAI URL |
| `RAG_EMBED_URL` | Ollama HTTP endpoint; local port 11434 |
| `EMBED_MODEL` | `bge-m3`; must match the release's digest |
| `RAG_STATE_SECRET` | Stable server secret shared across workers for clarification state |
| `FORM_REVIEW_SECRET` | Separate stable server secret shared across workers for preview tokens |
| `EMBED_BASE_URL`, `EMBED_API_KEY` | Legacy embedding helper; versioned RAG uses `RAG_EMBED_URL` |
| `FIELD_MAPPING_PROVIDER`, `FIELD_MAPPING_MODEL`, `FIELD_MAPPING_REASONING`, `PROFILE_MODEL`, `PROFILE_REASONING` | Ingestion/public-form analysis only; not needed to refill an already installed template |
| `FORM_FONT_DIR` | Optional licensed fonts directory for document conversion; Windows defaults to `C:/Windows/Fonts`; existing PDF filling uses the bundled font |
| `HOSO_LOAD_DOTENV` | Process-level switch; `0` disables local `.env` loading |

Blank state/review secrets produce process-local random keys. Restarts and
multiple workers then invalidate tokens unpredictably. Provision stable values
for integration. Share credentials through the team's secret channel or hosting
secret manager; never put them in Git, chat, browser configuration or this document.
Compose currently starts only PostgreSQL and Ollama; the API starts separately.

## One conversation UI and delivery work

Keep one visible conversation in Kim's portal:

1. Typed text and Son's finalized voice transcript enter the same conversation
   flow. Son can speak the returned answer; voice does not run a second RAG engine.
2. Procedure questions go to `/assistant/chat`. This service owns retrieval,
   clarification, answers and citations. The portal retains history and selection
   state; no backend conversation ID or chat persistence exists today.
3. In form-entry mode, Kim's adapter proposes field-ID changes against the NA5
   schema. Keep personal form values separate from RAG history. Validate against
   the backend schema/rules; `/validate` accepts partial values and reports missing required fields;
   `/preview` and `/preview-pages` require complete applicable values.
4. The portal displays field updates and the PDF in its existing document panel.
   Preview and explicit confirmation lead to download only when approved.
   A form edit must not be mistaken for a procedure question or automatically
   submitted to both services. Mixed intent needs an explicit routing decision.

Missing integration features are real gaps, not production mocks: portal authentication,
voice transport, persisted conversations/drafts, and public deployment. Photo
upload/storage/embedding and government submission are not implemented. The
existing NA5 preview renderer is real; the old `check_na5_workflow` script mocks
approval only inside a test, while the new handoff smoke does not.

Remaining deployment work:

1. Run the supplied bundle on Kim's machine and verify the pinned embedding model.
   The fresh-database restore and smoke have passed locally.
2. Configure the portal-to-backend access boundary and stable signing secrets.
3. Use the delivered branch/commit and the attached verification report; keep
   deployment changes separate from the shared backend contract.
4. Keep downloads disabled until a person reviews the template. This can be a
   separately stated limitation of a preview-only demo.

The document-specific schema and API examples are ready for adapter integration.
See [Kim's guide](kim-start-here.md); NA5 remains the first installed form, not a
fixed field schema for all procedures.
