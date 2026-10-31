# Frontend contract examples

Start with [Kim's integration guide](../kim-start-here.md).

`openapi.json` is the complete API contract. `procedure-documents.json` shows
installed document discovery. Each action identifies its own `document_id` and
`schema_url`; use that schema to build the fields. The NA5 schema is an example,
not a universal field list. Unknown/uninstalled documents return 404.
`ct01-1-004194-schema.json` and `marriage-declaration-1-000894-schema.json`
illustrate actual additional documents with different fields and manual sections.

Chat responses now include `answer_basis` (`sources`, `general_guidance`, `mixed`).
Render returned choices even when status is `answered`: a comparison can answer
the user's question while leaving procedure selection pending. Empty retrieval
and ambiguous selection use model-generated guidance rather than a canned reply.

`chat-request.json` and `chat-response.json` are a real public-question example
with Sol medium. `retrieval_state` was removed and replaced with null; obtain a
live signed value from the endpoint for conversation follow-ups. Source answers
reflect captured evidence and relevant uncertainty, not a current-law guarantee.

Fetch `/openapi.json`, `/procedures/1.001146/documents` and each action's
`schema_url` to refresh the structural contracts. Check the response example
against the current `ChatResponse` schema when the API changes. No credentials,
signed tokens or applicant records belong in these files.
