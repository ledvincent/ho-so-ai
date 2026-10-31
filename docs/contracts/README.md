# Frontend contract examples

Start with [Kim's integration guide](../kim-start-here.md).

`openapi.json` is the complete API contract. `procedure-documents.json` shows
installed document discovery. Each action identifies its own `document_id` and
`schema_url`; use that schema to build the fields. The NA5 schema is an example,
not a universal field list. Unknown/uninstalled documents return 404.

`chat-request.json` and `chat-response.json` are a real public-question example
with Sol medium. `retrieval_state` was removed and replaced with null; obtain a
live signed value from the endpoint for conversation follow-ups. Source answers
reflect captured evidence and relevant uncertainty, not a current-law guarantee.

Regenerate with `python -m scripts.export_frontend_contract` against the local
API after running `scripts.check_assistant_demo`. No credentials or applicant
records belong in these files.
