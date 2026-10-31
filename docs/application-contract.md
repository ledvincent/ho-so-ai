# Application contract: app.v1

This contract covers Kim's application boundary: account identity, personal profile,
and transient form preparation. It does not define Vincent's procedure-data format,
Son's conversation or authorization service, or a legal mapping to an official form.
`APPLICATION_CONTRACT_VERSION` in `web/lib/contracts.ts` identifies these application
types; it is not currently an HTTP response header.

Implementation references: `web/lib/contracts.ts`, `api/hoso_api/profile.py`,
`api/hoso_api/auth.py`, and `api/hoso_api/forms/{schemas,routes}.py`.
Browser profile fields and bounds are generated from the API model into
`web/lib/profile.generated.ts`. Run `python scripts/export_profile_contract.py`
from the API environment after a coordinated profile-model change; add `--check`
to verify that the two sides have not drifted.

## Transport and identity

The browser uses the same-origin Next application. Clerk owns managed sign-in;
the application does not collect passwords. The server-side profile proxy obtains
the Clerk session token and sends `Authorization: Bearer ...` to FastAPI.
The API ignores browser cookies and accepts Clerk session tokens, not browser-supplied
owner IDs or machine/API-key tokens.

`GET /v1/me` returns `{ "subject": "..." }` after verification. The API verifies the
signature using its configured Clerk public key, checks the exact configured issuer,
authorized frontend parties and required session claims, and optionally checks audience.
Missing credentials return 401; unavailable verification configuration returns 503.
There is no development identity bypass. The scaffold supports one configured issuer;
adding an issuer or moving tenants requires an explicit account-mapping decision.

Local JWT verification does not establish immediate logout/revocation status. AUTH-01
and ACCESS-01 must settle the team's revocation requirement before claiming it works.
Son interoperability, live Clerk sign-in and consent integration are not verified.
All `/v1/` responses and the application proxies disable caching of private responses.

## Personal profile

All six keys appear in a profile response. Missing values are `null`; all keys default
to `null` when omitted from a request. Unknown keys, wrong types and control characters
are rejected. Address alone permits newline and tab characters. Other empty strings
remain strings; an empty birth-date string normalizes to `null`.

| Key | Type | Limit / meaning |
| --- | --- | --- |
| `full_name` | string or null | 120 characters; application text, not verified civil identity |
| `date_of_birth` | string or null | Valid ISO `YYYY-MM-DD`, at most 10 characters |
| `nationality` | string or null | 80 characters |
| `address` | string or null | 300 characters |
| `phone_number` | string or null | 32 characters; does not establish number ownership |
| `email` | string or null | 254 characters; API accepts bounded text, not proof of mailbox ownership |

The form UI may apply additional user-facing format checks. These fields are not
automatically an approved CT01/NA5 mapping or fields to add to Clerk metadata.

```typescript
type ProfileRecord = {
  profile_id: string;
  revision: number; // integer, at least 1
  fields: ProfileFields;
};
type ProfileUpdate = {
  expected_revision: number; // integer, at least 0
  fields: ProfileFields;
};
```

| FastAPI route | Next proxy | Current behavior |
| --- | --- | --- |
| `GET /v1/profile` | `GET /api/profile` | Returns the verified subject's profile; missing record returns 404 |
| `PUT /v1/profile` | `PUT /api/profile` | Explicit creation/update with atomic expected-revision check |

The registered production handlers delegate to the portal service. The repository
resolves ownership from the verified server-side subject on every operation. The
browser supplies neither an owner nor a profile ID. GET has no creation side effect.
PUT replaces the six fields (omitted values become null); `expected_revision: 0`
creates only if absent. A successful create returns revision 1; a positive expected
revision updates only that owner's matching revision and increments once.

| Status | Profile error body | Meaning |
| --- | --- | --- |
| 404 | `{"detail":{"code":"PROFILE_NOT_FOUND"}}` | No profile for the verified subject, including an update with a positive revision |
| 409 | `{"detail":{"code":"PROFILE_REVISION_CONFLICT"}}` | A create already exists or an update's expected revision is stale |
| 503 | `{"detail":{"code":"PROFILE_UNAVAILABLE"}}` | Storage configuration is missing/invalid, or storage fails |

`create_app` constructs production storage only in application lifespan using
`portal.postgres.build_profile_service(config)`. Missing database/issuer config
or sanitized `StorageUnavailable` leaves the service unavailable; it never selects
another store or downgrades TLS. Engine construction is lazy, without schema creation
or migration. The application closes the factory-owned service through its public
`close()` during shutdown and clears the state reference. An explicitly injected
service is caller-owned and is not closed by the application. `/health` remains only
a process health check. See `profile-storage-test-plan.md` for the isolated database
proposal and outstanding provider review items; no live database is provisioned by
this integration.

Form prefill copies the profile into a local form draft. Editing that draft must not
silently update the saved account profile. Saving a profile is a separate explicit
action through the authenticated profile route. An account-prefill failure must remain
visible; manual entry is still a separate, explicitly synthetic path.

## Synthetic form rendering

The shipped registry contains only template `demo`, version `synthetic-demo-v1`.
Its PDF carries a synthetic warning. It is not an official form. Settings default
`DEMO_FORMS_ENABLED` to false; the local example explicitly opts in for fictional data.
These endpoints are transient and do not create an account-owned document or profile.

| FastAPI route | Next proxy | Successful response |
| --- | --- | --- |
| `GET /v1/forms/demo` | No metadata proxy in this baseline | Field metadata and template version as JSON |
| `POST /v1/forms/demo/preview` | `POST /api/forms/demo/preview` | `image/png`, rasterized from the generated PDF |
| `POST /v1/forms/demo/pdf` | `POST /api/forms/demo/pdf` | `application/pdf`, attachment; requires acknowledgement |

Both POST bodies use this shape:

```typescript
type FormRenderRequest = {
  values: ProfileFields;
  revision: number; // integer, at least 1; local draft correlation
  template_version: string;
  acknowledged: boolean;
};
```

No filesystem path, template upload, owner ID or procedure facts are accepted.
Metadata describes PDF points (1/72 inch), origin at the unrotated page's top-left,
x increasing right and y increasing down, with zero-based page indices. Current
rendering supports one unrotated A4 page. See `forms-rendering.md` for Unicode,
baseline clearance, wrapping and overflow behavior.

The UI must invalidate preview and acknowledgement after edits, clearing or new
prefill. Capture an immutable values/revision snapshot before rendering; ignore a
late response for another revision. Download uses the reviewed snapshot and requires
`acknowledged: true`. The server checks template version. Draft revision is separate
from a stored profile revision and is not an authorization token. The stateless server
cannot establish that someone actually viewed the preview image.

Real templates remain gated by a human review bound to source, converted PDF and
field-mapping SHA-256 hashes, reviewer and review time. Any changed hash invalidates
that review. There is no HTTP auto-approval route and no approved official template
in this registry. Real account documents also require authorized owner/session storage
and download rules before handling personal data.

## Errors and limits

| Status | Current meaning |
| --- | --- |
| 400 | `INVALID_REQUEST_BODY`: malformed UTF-8 or unreadable request stream |
| 401 | Missing or invalid authenticated session on a protected route |
| 403 | Next mutation proxy rejects non-matching origin or non-JSON content type |
| 404 | `PROFILE_NOT_FOUND`, unknown form, or synthetic form disabled |
| 409 | `PROFILE_REVISION_CONFLICT`, `template_version_changed` or `template_not_reviewed` |
| 413 | Next proxy rejects request content larger than its 8192-byte limit |
| 422 | Request validation, missing acknowledgement or field/render validation |
| 503 | Authentication, upstream/profile/renderer, or Unicode font unavailable |

FastAPI request validation returns top-level `code: "VALIDATION_ERROR"`, a generic
detail and sanitized issue locations/types/messages, without submitted field values.
Form rendering errors use `detail: { code, field? }`; examples include `text_overflow`,
`unsupported_glyph`, `single_line_required` and `review_acknowledgement_required`.
Next proxy failures use their own top-level `code` (for example `AUTH_UNAVAILABLE`,
`PROFILE_UNAVAILABLE` or `RENDERER_UNAVAILABLE`). Consumers must handle these shapes
explicitly, and must not display raw upstream errors or imply that a failed request saved.
Mutation checks compare the browser's Origin with configured `HOSO_PUBLIC_ORIGIN`,
not the internal Request URL, which Next/proxies can rewrite. Set the portal's exact
origin to port 3001; do not trust a caller-supplied forwarded-host header.

The browser reaches these endpoints through the same-origin proxies. No model call,
government submission, persistent form-value logging, or official-source validation
is established by this seam. Tests and local synthetic PDF review do not establish
live authentication, PostgreSQL ownership isolation or voice-to-report integration.
