# Kim: start integrating here

The backend owns procedure selection, RAG, answers, citations and document
requirements. Kim's adapter proposes form-field changes. Son's finalized voice
transcript enters the same routing as typed text. Do not send form values to chat.

## Files you can use immediately

The checked-in [contracts directory](contracts/README.md) contains:

- `openapi.json`: current request/response schemas and validation errors.
- `chat-request.json` and `chat-response.json`: a public question and a recorded
  Sol answer with citations and document cards. Answer wording can vary.
- `procedure-documents.json`: installed form discovery with document-specific URLs.
- `na5-provincial-stay-extension-schema.json`: NA5's fields, conditions, roles,
  manual areas and PDF placements. Render applicable writable fields; do not
  assume all fields are user-entry fields or reuse this schema for other forms.

The examples omit live signed conversation state (shown as null). In real
responses preserve the opaque `retrieval_state` and return it on follow-ups.
Do not replay fixture choice IDs without the corresponding live state.

## Chat and document flow

`POST /assistant/chat` accepts:

```json
{
  "message": "I'm confused about the paperwork. Can you walk me through what I need and help me with the form?",
  "procedure_code": "1.001146",
  "history": [],
  "retrieval_state": null,
  "clarification_answer": null
}
```

Omit `procedure_code` to help the user choose. The response always contains
`status`, `answer`, `citations`, `model`, `choices`, `retrieval_state`,
`procedure_code`, `documents`. Status is `answered`, `needs_clarification`,
`insufficient_context` or `out_of_scope`. Partial answers can still have useful
documents. Render text safely; resolve citation markers through `citations`.

Each document has `id`, `title`, `kind`, `requirement`, `condition`, `description`,
nullable `originals`/`copies`, `source_ids`, `evidence_status` and optional `form`.
Use `form.schema_url` and the other server-owned URLs; do not parse answer prose.
`form` also exposes template version/revision, review status, applicability and
`download_available`. These are independent of the assistant's response status.

When `choices` is nonempty, send the returned state and selected choice ID as
`clarification_answer`; omit `procedure_code` during clarification. Retain state
for later questions. Conversation history alone does not select a procedure.

The API is document-specific: **never hard-code the NA5 fields or field count**.
Read `documents[].form.document_id` and fetch that action's `schema_url`. For a
procedure's installed forms, use `GET /procedures/{procedure_code}/documents`;
this lists fillable workflows, not the complete required-document checklist.
NA5 is currently the first installed document, with ID
`na5-provincial-stay-extension`. Future documents return different field arrays,
conditions, fixed values and page counts through the same contract.
Supporting documents without a filling workflow have `form: null`.

The generic base path is `/documents/{document_id}`. NA5's old
`/workflows/1.001146/*` routes remain compatibility endpoints only:


| Method / suffix | Use |
| --- | --- |
| GET `/schema` | Field schema and template version |
| GET `/template` | Blank PDF |
| GET `/template-pages` | Blank page images |
| POST `/validate` | Partial `{values, template_version}`; normalized values, missing fields, `ready_for_preview` |
| POST `/preview` | Complete values/version; PDF with `X-Review-Token` |
| POST `/preview-pages` | Same input; `{template_version, pages:[{page_number,image_data_url}]}` and token |
| POST `/download` | `{values, template_version, review_token, confirmed:true}` |

All values are strings, dates `YYYY-MM-DD`. Use field IDs from the schema,
including `applicant_full_name`, `passport_number`, `host_type`, `sponsor_kind`,
`extension_until`. Honour `when`, `manual`, `inactive`, `hidden` and
`fixed_values`; the backend rejects unknown/inapplicable values. Submit the
current merged field map to `/validate`; this endpoint is stateless, not a
stored patch operation. Never invent missing values to make preview succeed.

Preview requires complete applicable fields and checks printed fit. A field
edit invalidates its preview/token. Tokens last 15 minutes, are signed rather
than encrypted, and contain values: keep them out of logs and URLs.

Errors are `{"detail":"..."}` except request-validation 422, which has a detail
array. Chat: 404 missing context; 409 expired state/stale index; 413 oversized
context; 422 input; 502 invalid/provider output; 503 unavailable/configuration;
504 timeout. Model timeout is 120 seconds; use at least 180 seconds upstream.
Forms: 422 invalid values; 409 stale template or download not approved. Inspect
OpenAPI for the full request shapes. Error strings are not stable error codes.

## Run the backend on your machine

The backend and its tested data are on branch `codex/procedure-foundation`.
The [checked-in snapshot](../data/bootstrap/README.md) contains **only the four
initial tested procedures**, their required source files and the published
205-item RAG index. No separate ZIP transfer or hosted service is required.
The 15 newer procedures are deliberately excluded from this handoff.

Requires Python 3.12+, uv and Docker Desktop. Merge/pull the backend branch into
the shared repository, then run from its root:

```powershell
uv sync --locked
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --wait
uv run python -m scripts.restore_backend_data --database hoso_integration
docker compose exec embeddings ollama pull bge-m3
```

The restore command verifies the archive and each source file, restores the
schema/data/index in one transaction, and refuses to overwrite a populated
database or differing source files. No new ingestion or embedding rebuild is
needed. It does not read or change `.env`.

Set these values in your local `.env` before starting the API:

```dotenv
DATABASE_URL=postgresql+psycopg://hoso:hoso_local@localhost:55432/hoso_integration
ASSISTANT_BASE_URL=https://api.openai.com/v1
ASSISTANT_MODEL=gpt-6.1-sol
ASSISTANT_REASONING_EFFORT=medium
ASSISTANT_API_KEY=<provision privately>
RAG_EMBED_URL=http://localhost:11434
EMBED_MODEL=bge-m3
RAG_STATE_SECRET=<generate privately>
FORM_REVIEW_SECRET=<generate a different value privately>
```

For each signing secret, `uv run python -c "import secrets; print(secrets.token_hex(32))"`
generates a value locally. Neither signing token is caller authentication.
Do not send keys through Git or chat. Credentials and Ollama model weights are not in Git.
The saved index expects BGE-M3 digest
`7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`; check
`docker compose exec embeddings ollama list` (the ID is its prefix). A mismatch
requires the matching model or an evaluated rebuild, not a silent substitution.

```powershell
uv run alembic upgrade head
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001
# In another shell:
uv run python -m scripts.check_frontend_handoff --live-assistant
```

Expected migration: `0009`. **API base URL on Kim's PC: `http://127.0.0.1:8001`.**
OpenAPI: `http://127.0.0.1:8001/docs`; chat: `POST /assistant/chat`.
This URL becomes available when the startup command is running on his machine.
The smoke command exercises the app directly, including one paid model request;
its report records the exact commit, working-tree status and checks. A fresh
ingestion or changed embedding model requires rebuilding and evaluating the
index using [the RAG workflow](rag.md). No HTTPS server is deployed.

## Integration boundaries and remaining limits

Backend and frontend belong to the same repository and run on the same host.
Use the portal's existing backend connection; no person-specific API URL or
remote service is required. With a same-origin server proxy, browser CORS is
unnecessary. Proxy these routes under the authenticated portal and forward
PDF bytes, content type, status codes and `X-Review-Token` without altering them.

Use one authenticated portal UI. Procedure questions call chat. In form mode,
Kim's adapter proposes field changes and the portal calls validation/preview.
Route a mixed request explicitly; personal values must not enter RAG history.
Voice is an input/output layer over that same conversation, not a second RAG.

The backend currently has no authentication, CORS, rate limits or chat/draft
persistence. Put it behind Kim's authenticated server on a private network;
do not expose this development server publicly. Direct cross-origin calls need
an explicit origin allowlist and `X-Review-Token` exposed via CORS.

NA5 revision `70/2026/TT-BCA` is **draft**. Preview works; final download returns
409 until human template review. Accepted-edition applicability is also unresolved
in the captured sources. No photo upload, voice service or government submission
is implemented. Answers, RAG, validation and PDF previews are real. Tests use
fictional applicant values; the API does not supply prefilled applicant data.

## Adding another document

Add its own PDF and workflow definition, then an entry in
`data/forms/registry.json` with a unique `document_id`, `procedure_code`, `form_id`,
name, `spec_path`, and applicability status.
The workflow defines its own `fields`, `fixed_values`, optional `date_order`,
field-level `uppercase`, placements, PDF hash and review status. Draft ingestion
results must be validated before installation; downloads still require review.
No frontend field list or new document-specific route is needed. Unknown document
IDs return 404. Versions and preview tokens are bound to document identity as well
as its template, rules and values, so one form cannot reuse another's token.
