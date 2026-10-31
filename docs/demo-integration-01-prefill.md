# DEMO-INTEGRATION-01: explicit NA5 prefill compatibility

Implemented: deterministic profile proposals for the exact e162 NA5 document
schema. This document describes a narrow compatibility bridge, not legal
approval, an expanded assistant schema, or successful live integration.

## Frontend request and response

The existing authenticated `POST /api/profile/v2/prefill` request shape is unchanged.
Both `consent` and `applicant_confirmed` must be literal `true`. Keep the current
profile revision, request ID and draft revision; ignore stale responses after an
account, draft, document or schema change. The API does not save/apply proposals.

For the e162 installed document, send exactly:

```json
{
  "procedure_code": "1.001146",
  "form_sha256": "a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751",
  "schema_version": "0ea9956659b50098c275e687533954cfa68f1541eab40ad167cf8627def4014b"
}
```

These are the document-context fields of the existing request, not its full body.
Include the current complete applicable `values` map, with at most 43 known fields.
The response echoes the submitted `schema_version`; do not replace it with a raw
file hash or the legacy workflow version. Unknown procedures, originals and schema
versions remain `409 PREFILL_UNSUPPORTED`. Invalid current draft values remain
`422 PREFILL_INVALID_DRAFT`; a stale profile remains `409 PROFILE_REVISION_CONFLICT`.

The legacy version
`50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3`
continues to behave as before. CHAT-01 still uses only that legacy version. No new
document is inferred from a filename, prose answer or matching original PDF alone.

## Exact compatibility evidence

Producer source is `e16279119281e0d1897f0259ec8f9366e091c90d`, public contract
`docs/contracts/na5-provincial-stay-extension-schema.json`. Its exact bytes are
vendored as `api/hoso_api/chat/assets/na5-document-e162.json` with SHA-256
`ee00fc00c540cd53eca1b762ef8c2e7cdece87122d97f2bb05e97caed78a3e6f`.
The loader verifies this hash and the complete document identity before enabling
the additional version. The installed document ID is
`na5-provincial-stay-extension`, form ID `NA5`, original hash and template version
as above. Revision is `70/2026/TT-BCA`, effective-from metadata `2026-07-01`.

The public schema and legacy workflow have exactly 43 ordered fields and identical
fixed values. A field-by-field deep comparison permits only the new
`applicant_full_name.uppercase: true` flag; all other field properties must match.
The existing proposal mapping already uppercases the applicant name and measures
the transformed value against the field limit. No field is renamed or remapped.

The public schema also adds these exact date-order constraints:

1. `birth_date <= entry_date`
2. `entry_date <= permitted_until`
3. `permitted_until <= extension_until`
4. `extension_until <= passport_expiry`

For the new version, the incoming draft must satisfy each pair when both dates
are present. Partial drafts do not acquire fabricated dates. Individual profile
proposals remain suggestions: the user reviews them, and producer validation and
preview still check the resulting complete form before any final action.

## Gates and verification

This bridge is limited to profile-prefill proposals. It does not modify legacy
workflow bytes, the CHAT-01 schema, profile storage, consent, ownership, CAS,
proposal application, preview tokens or download gates. The producer still marks
this document `draft`, applicability `unresolved`, and final download unavailable.
Fictional previews do not establish legal applicability or approve the template.

Offline verification: `tests/test_profile_prefill.py` and
`tests/test_profile_prefill_compat.py` passed together: **101 passed**. They verify
legacy output remains unchanged, the exact new version is accepted and echoed,
changed identities/fields/bytes and unknown versions fail closed, and only the new
incoming draft receives the added date-order checks. Runtime/tunnel/model
verification is outside these tests. No live model call was made for this bridge.
