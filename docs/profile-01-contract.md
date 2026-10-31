# PROFILE-01 richer profile and consented prefill

Consumer seam, 2026-10-31. Backend: Kim; frontend owns all views and draft
application. Base UI-03: `1825f5e15cf84fc6259004c56cec7185799ae12c`.
Vincent NA5 source: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`.
Manager alone writes Kim's status. No provider, retrieval or voice call is involved.

## Versioned own-profile API

Existing `/api/profile` -> `/v1/profile` remains strict app.v1 with exactly its six
fields, unchanged identity and error semantics. It continues to accept old clients.
New `/api/profile/v2` -> `/v2/profile` supports authenticated GET and explicit PUT.
Both versions use the SAME owner-bound row, profile ID and monotonically increasing
revision. There is no separate details revision or identity system.

GET response:

```json
{
  "schema_version":"profile.v2", "profile_id":"server-owned-id", "revision":1,
  "details": {
    "basics":{"full_legal_name":null,"date_of_birth":null,"sex_as_on_document":null,"nationality_at_birth":null,"current_nationality":null,"occupation":null},
    "contact":{"phone_number":null,"email":null},
    "passport":{"document_number":null,"document_type":null,"issue_date":null,"expiry_date":null,"issuing_authority":null},
    "residence":{"temporary_address_in_vietnam":null,"permanent_address":null}
  },
  "legacy":{"nationality":null,"address":null}
}
```

All details are optional nullable strings. `full_legal_name`, DOB, phone and email
are versioned aliases of the existing `full_name`, `date_of_birth`, `phone_number`
and `email` columns, not duplicate sources. Existing names are not asserted to be
verified legal names: the UI must ask the user to review them. Generic legacy
nationality/address remain visible separately and are NEVER automatically migrated
to the explicit new fields or prefilled. `legacy` is read-only in v2.

PUT is exactly `{expected_revision:integer,details:<the grouped object above>}`.
It replaces the v2-editable snapshot; omitted optional values become null. Send
the complete edited details object to preserve untouched values. The four groups
are required, extra keys forbidden. Expected revision0 creates only if absent;
positive revisions update only an existing matching row. Missing404
`PROFILE_NOT_FOUND`, conflict409 `PROFILE_REVISION_CONFLICT`, unavailable503
`PROFILE_UNAVAILABLE`; validation422 contains safe locations, no submitted values.
v1 PUT updates only its six columns and PRESERVES all extension data. v2 PUT
preserves both ambiguous legacy columns. A write through either API invalidates
the other API's old revision, so consumers reload on conflict rather than merge
silently. Saving the profile is always separate from copying into a form.

Limits: full name120, DOB10, sex `M|F|X|unspecified|null`, explicit nationalities80,
occupation120; phone32/email254; document number64, type80, issue/expiry10,
issuing authority160; each explicit address500. Dates must be real complete ISO
dates; passport expiry cannot precede its issue date. New text fields reject
control/format characters (addresses allow line breaks). Shared v1-backed fields
retain v1 validation semantics so existing valid v1 rows remain readable.
No travel purpose/dates, sponsor, organization, family or signature defaults.

## Read-only prefill proposals

POST `/api/profile/v2/prefill` -> `/v2/profile/prefill` requires the current session,
same-origin JSON and BOTH explicit consent and applicant confirmation:

```json
{
  "consent":true,"applicant_confirmed":true,
  "expected_revision":1,"request_id":"ui-generation-unique-id","draft_revision":4,
  "procedure_code":"1.001146",
  "form_sha256":"a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751",
  "schema_version":"50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3",
  "values":{"request_type":"stay_extension"}
}
```

Do not call this endpoint before the user agrees to inspect saved information for
the selected document and confirms they are its applicant. A manual-only path
requires no profile request. Expected profile revision must still match; no owner
or client-supplied profile data is accepted. The server reads only this session's
profile and performs deterministic local mapping. It never writes a profile or
form draft, invokes retrieval/model tools, or grants Son ACCESS-01 authorization.

Response echoes request_id, draft_revision, procedure_code, form_sha256 and
schema_version, and includes profile_id, profile_revision, `review_status:"draft"`,
`proposals` and `unmapped`. Each proposal has `proposal_id`, `source_fields`,
`source_values`, `target_field`, `value`, `mapping`, `existing_value`, and
`requires_overwrite`. `unmapped` entries contain `source_field` and a static reason.
No source values appear in errors. Unsupported form/schema409
`PREFILL_UNSUPPORTED`; profile revision conflicts use the existing409 code.

Only explicit same-meaning fields map: legal name -> applicant_full_name
(uppercase, then100-character limit); DOB -> birth_date; M/F -> male/female;
separate birth/current nationality, occupation, travel-document number/type/
authority/expiry, and explicit temporary Vietnam address. No truncation, guessed
date, flattened multiline address or sex coercion. X/unspecified stay unresolved.
Issue date and permanent address have no matching applicant target. Generic
legacy nationality/address never map. Passport proposals refer to ONE saved
travel document; the user must confirm it is the document used for this application.

For NA5's combined `contact`, offer separate phone-only and email-only proposals
and, if both fit, an explicitly previewed `phone + " / " + email` proposal. These
are alternatives for ONE target: the UI must select at most one, never silently
join values or apply competing proposals. Each target must be active/editable in
the exact43-field schema; signatures, fixed fields and sponsor branches are excluded.
Values that fail target bounds are listed as unmapped, never shortened.

The frontend must bind a pending preview to its authenticated account and profile
ID/revision, request generation, draft revision, procedure, original form hash and
schema. Discard on ANY change or logout. Show source -> target and exact proposed
value; require per-field apply/skip. Existing nonempty draft values are preserved
unless the user explicitly chooses replacement. Apply the chosen copies as ONE
undoable draft edit, increment revision and invalidate review/export; ask remaining
questions normally. This task does not implement the UI's apply/undo controller.
Prefill consent does not authorize sending saved profile data to any model.

## Storage and bounded verification

Optional extensions use one JSON column on the existing profile row. New isolated
SQLite databases can initialize it; existing/shared databases are not automatically
migrated. An explicit offline upgrade tool will require a named database and
confirmation for an isolated test copy. PostgreSQL DDL remains a review-only
proposal; no live migration is run. Legacy v1 remains usable without the column;
v2 fails explicitly unavailable until its additive schema is provisioned.

Generated browser types/schema will live in `web/lib/profile-v2.generated.ts`.
Backend owns generation, API models, persistence, prefill mapping and proxies;
frontend owns views. Tests use synthetic data only: v1 compatibility/no field loss,
CAS conflicts, account isolation, optional-field validation and deterministic mapping.
Existing UI-02/UI-03 source and3020/8020 runtimes are preserved. Public authentication
and production PII storage readiness are unchanged by this bounded checkpoint.
