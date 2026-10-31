# DEMO-INTEGRATION-01: producer discovery and document adapter

Producer source: `e16279119281e0d1897f0259ec8f9366e091c90d`, specifically
`docs/kim-start-here.md`, `docs/contracts/openapi.json` and its API implementations.
This replaces the old discovery chat wire shape. Existing profile APIs and the
legacy hash-pinned schema route retain their separate contracts.

The root handler owns authentication, same-origin checks, limits, protected proxy
routes and owner-bound preview-token handling. The pure upstream client never
forwards cookies/Bearer credentials, reads keys or invents procedure selection.

## Protected browser paths

Use `/api/discovery/setup`, `/api/discovery/chat`, `/api/discovery/search`,
`/api/discovery/procedures/{code}/documents`, and the corresponding
`/api/discovery/documents/{document_id}/{suffix}` paths below. Existing inspection
paths for a procedure/profile/original remain available. Returned form-action
URLs are checked against exact producer paths and rewritten to these protected
browser paths. They are metadata, never arbitrary fetch targets.

## Chat and procedure selection

`POST /api/discovery/chat` accepts exactly:

```ts
type DiscoveryChatRequest = {
  message: string; // trimmed, 2..1000 Unicode code points
  procedure_code?: string | null;
  history?: {role: 'user' | 'assistant'; content: string}[]; // <=12, content 1..16000
  retrieval_state?: string | null; // opaque, <=12000; preserve exactly
  clarification_answer?: string | null; // <=1000; returned choice ID
};
```

Response fields are `status`, `answer`, `citations`, `model`, `choices`,
`retrieval_state`, `procedure_code`, `documents`. Statuses remain `answered`,
`needs_clarification`, `insufficient_context`, `out_of_scope`. Citation objects
contain `id`, `title`, `url`; choice objects contain `id`, `label`.

Keep signed state in the current authenticated conversation, never URLs/logs.
When choices are returned, send the exact state plus chosen ID as
`clarification_answer`, omitting `procedure_code`. Keep state on later follow-ups.
Never replay a choice from another state or infer a procedure from answer text.
History alone is not procedure selection. Keep applicant/form values out of RAG
messages/history; use the separate form assistant for those.

Render answer text safely and resolve bracket markers against citations. Extra
citations may support document cards without appearing inline; this is valid.
Cards can remain useful for a partial answer. A response status does not approve
a form, resolve applicability or unlock download.

Search preserves `{status,release_id,results,degraded}` with candidates
`{code,name,score,matched_by}`. There is **no `similarity` field**. An explicit
choice/confirmation remains a UI operation; GET requests do not store it.

`setup()` reads only `/assistant/setup`: `generation_configured`, `index_ready`,
`procedures:[{code,name,name_en}]`, `model`, `reasoning_effort`. It does not run
search, ingestion or a paid health-check question.

## Document cards and generic forms

Each card preserves `id,title,kind,requirement,condition,description,originals,
copies,source_ids,evidence_status,form`. Supporting cards may have `form:null`.
`GET /procedures/{code}/documents` returns `{documents: FormAction[]}` for installed
fillable workflows, not the complete checklist.

`FormAction` contains `document_id,form_id,procedure_code,template_sha256,
template_version,revision,review_status,applicability,download_available`, plus
`schema_url,template_url,template_pages_url,validate_url,preview_url,
preview_pages_url,download_url`. Use its actual document ID. Do not hard-code NA5,
43 fields or three pages.

`GET .../documents/{id}/schema` returns the producer's `DocumentSchema`: identity,
revision/review/applicability/download metadata, template version/original hash,
page count, dynamic `fields`, `fixed_values`, `date_order`. Preserve field
conditions, roles, manual/inactive/hidden flags and extra placement metadata.
Unknown documents fail 404. Draft schema/preview is inspectable; final download
requires the producer's reviewed/download gate and the authenticated owner's token.

All form mutation bodies include `{values: Record<string,string>,
template_version: string}` with the exact lower-hex64 current version. Validation
is a whole merged snapshot, not a stored patch. Download additionally requires
`review_token` and `confirmed:true`. Never flatten, invent or truncate answers.

| Client method | Producer operation | Result to root handler |
| --- | --- | --- |
| `setup()` | GET `/assistant/setup` | JSON |
| `documents(code)` | GET `/procedures/{code}/documents` | JSON actions, protected URLs |
| `documentSchema(id)` | GET `/documents/{id}/schema` | Dynamic schema JSON |
| `documentTemplate(id)` | GET `/documents/{id}/template` | `{bytes,contentType,filename}` PDF |
| `documentPages(id)` | GET `/documents/{id}/template-pages` | `{template_version,pages}` JSON |
| `documentValidate(id,body)` | POST `/documents/{id}/validate` | `{values,missing_fields,ready_for_preview,template_version,note}` |
| `documentPreview(id,body,false)` | POST `/documents/{id}/preview` | `{bytes,contentType,reviewToken}` |
| `documentPreview(id,body,true)` | POST `/documents/{id}/preview-pages` | `{data,contentType,reviewToken}` |
| `documentDownload(id,body)` | POST `/documents/{id}/download` | `{bytes,contentType,filename}` PDF |

Page objects are `{page_number,image_data_url}`, numbering starts at one. Only
bounded PNG data URLs are accepted. The handler forwards `reviewToken` exclusively
as `X-Review-Token`, keeping the producer JSON body unchanged. Tokens contain
personal values and expire after 15 minutes; do not decode them, store them in
URLs, log them, or treat them as caller authentication. On any edit/account or
document/version change invalidate the preview/token. The root additionally binds
token hashes to the authenticated owner before download.

## Bounds and verification

Client endpoints are fixed origin plus allowlisted code/hash/document-ID paths.
HTTPS is required except real loopback HTTP; redirects, URL credentials, arbitrary
returned URLs and automatic retries are forbidden. No inbound authentication is
sent upstream. Regular calls time out after 20 seconds; chat after 180 seconds
(producer generation can take 120 seconds). Chat request limit is 1 MiB to permit
the producer's 12 Unicode history turns. Normal JSON is capped at 1 MiB, PDF/original
bytes at 10 MiB, image-page JSON at 16 MiB. Limits are enforced while streaming.

Errors remain stable adapter codes, not raw producer bodies. Producer 409 stays
an explicit not-ready/stale gate; 422 stays a safe invalid-request response.
No field values, signed state or review tokens appear in errors. Implementation
tests use synthetic fixtures and checked-in public contract examples; they do not
run live retrieval, models, generation or database mutations.
