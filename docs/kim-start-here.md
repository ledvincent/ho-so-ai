# Kim: start integrating here

The backend owns procedure selection, RAG, answers, citations and document
requirements. Kim's adapter proposes form-field changes. Son's finalized voice
transcript enters the same routing as typed text. Do not send form values to chat.

## Files you can use immediately

- `openapi.json`: exact current HTTP schemas, including validation/error shapes.
- `chat-request.json`: working public question for the shared provincial demo.
- `chat-documents-response.json`: actual Sol answer, citations and document cards.
- `chat-processing-response.json`: actual sourced processing-time answer.
- `chat-clarification-response.json`: natural clarification and choice IDs.
- `na5-schema.json`: the NA5 example's 43 logical field definitions, types, conditions, required
  flags, choices, roles/manual areas and PDF placements. Render applicable
  writable fields; do not assume all 43 are user-entry fields.
- `na5-fields.csv`: a flat field inventory for quick adapter implementation.
- `fictional-values.json`: explicitly fictional complete example for previews.
- `live-smoke.json`: 10/10 passing live cases, no mocked model or template approval.
- `restore-smoke.json`: 8/8 checks passed after restoring the dump into a separate
  fresh database, including a real Sol answer and the actual preview/download gate.
  This restore used the existing machine and model service, not a second computer.
- `manifest.json`: exact file hashes, model/effort, base branch/SHA and snapshot status.

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

## Run the full backend bundle

The source/API contract is on branch `codex/procedure-foundation`. Fetch and
check out the delivered commit (see the handoff message). The checked-in
`docs/contracts/` directory contains OpenAPI, a real example response and the
current document schema. A Git clone does not include the populated database.

Unzip `kim-backend-demo.zip` into a new folder for the public procedure artifacts
(including ignored `data/_store`) and `handoff/procedure-db.dump`, preserving the
reviewed index and source IDs. Use the pushed source commit with this data; the
archive manifest identifies its own source snapshot. No credentials are included.

Requires Python 3.12+, uv and Docker Desktop. Use a Git checkout for the latest
source, and copy only the database/public data from the earlier bundle:

```powershell
git clone --branch codex/procedure-foundation https://github.com/ledvincent/ho-so-ai.git
cd ho-so-ai
# Copy handoff/procedure-db.dump, data/_store/ and data/archive/raw/ from
# the supplied ZIP into matching paths here. Keep the checked-out source
# and data/forms/ workflow definitions; do not replace them with older ZIP files.
```

Then run from the checkout root:

```powershell
uv sync --locked
Copy-Item .env.example .env
docker compose up -d --wait
docker compose exec -T db createdb -U hoso hoso_kim_demo
docker compose cp handoff/procedure-db.dump db:/tmp/hoso-demo.dump
docker compose exec -T db pg_restore -U hoso -d hoso_kim_demo --no-owner --no-acl --exit-on-error /tmp/hoso-demo.dump
docker compose exec embeddings ollama pull bge-m3
```

The restore command intentionally targets a newly created database. Do not run
it over an existing database. Set these values in the new local `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://hoso:hoso_local@localhost:55432/hoso_kim_demo
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
Do not send keys through Git or chat. Ollama model weights are not in the ZIP.
The saved index expects BGE-M3 digest
`7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`; check
`docker compose exec embeddings ollama list` (the ID is its prefix). A mismatch
requires the matching model or an evaluated rebuild, not a silent substitution.

```powershell
uv run alembic current
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001
# In another shell:
uv run python -m scripts.check_assistant_demo --output output/kim-smoke
```

Expected migration: `0009`. Local UI: `http://127.0.0.1:8001/assistant`.
OpenAPI: `http://127.0.0.1:8001/docs`. No HTTPS server is deployed. A localhost
URL on Tanguy's machine is not accessible remotely; run this bundle locally.

## Integration boundaries and remaining limits

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
is implemented. Answers, RAG, validation and PDF previews are real. Example
applicant values are the only intentionally fictional data.

## Adding another document

Add its own PDF and workflow definition, then an entry in
`data/forms/registry.json` with a unique `document_id`, `procedure_code`, `form_id`,
name, `spec_path`, optional fictional `example_path`, and applicability status.
The workflow defines its own `fields`, `fixed_values`, optional `date_order`,
field-level `uppercase`, placements, PDF hash and review status. Draft ingestion
results must be validated before installation; downloads still require review.
No frontend field list or new document-specific route is needed. Unknown document
IDs return 404. Versions and preview tokens are bound to document identity as well
as its template, rules and values, so one form cannot reuse another's token.
