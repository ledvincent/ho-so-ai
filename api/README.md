# Application API scaffold

Python 3.12+, FastAPI, Pydantic and the official Clerk Python backend SDK.
The application lazily constructs the portal PostgreSQL service during lifespan.
It creates no schema and runs no migration; the first authenticated profile operation
opens a connection only when storage is configured.
Vincent still owns the procedure-data contract.

From this directory:

```powershell
uv sync --group dev
uv run uvicorn hoso_api.main:app --host 127.0.0.1 --port 8000 --reload
uv run pytest
```

`GET /health` is a process health check, not proof of database/auth readiness.
`GET /v1/me` accepts a Clerk **Bearer session token** and returns only its
verified `subject`. Cookies, machine tokens and client-supplied user IDs do not
establish identity on this API.

All `/v1/` responses use `Cache-Control: no-store`; validation errors return
stable error types without echoing the submitted profile values.

## Authentication configuration

Set these in the process environment using the project's local secret tooling;
the API does not source env files itself:

- `CLERK_JWT_KEY`: the configured Clerk instance's public verification PEM.
  Literal `\n` escapes are supported. This is a public key, not an API secret.
- `CLERK_ISSUER`: the exact expected `iss` from that instance's session tokens.
- `CLERK_AUTHORIZED_PARTIES`: comma-separated exact frontend origins, such as
  `http://localhost:3000`. There is no permissive default.
- `CLERK_AUDIENCE`: optional expected `aud`, if the team configures one.
- `CORS_ALLOWED_ORIGINS`: comma-separated origins; defaults only to
  `http://localhost:3000`. Wildcards and origin paths are rejected.
- `DEMO_FORMS_ENABLED`: `true` or `false`, default `false`. This enables only
  explicitly synthetic form routes, never an official form approval.
- `DATABASE_URL`: isolated PostgreSQL runtime-login URL. The portal provider requires
  verified TLS and an issuer-bound reviewed schema; see
  [the storage test plan](../docs/profile-storage-test-plan.md). The existing Compose
  service has no TLS setup and cannot satisfy this policy as-is.

Missing auth configuration fails closed with 503 on protected routes. Invalid
or missing credentials produce 401. Verification uses Clerk's SDK with a local
public key, explicit authorized parties and session-token restriction, followed
by required issuer/subject/expiry/session-ID checks. No remote-key fallback is
configured. Key rotation therefore requires updating the configured public key.

Clerk's local signature checks do not establish immediate logout/revocation
status; sessions remain subject to their token expiry. The portal/security task
must resolve the team's immediate-revocation requirement before claiming it.

## Profile boundary

`GET /v1/profile` and `PUT /v1/profile` use the verified subject and existing portal
service, response models and private headers. No client owner/profile ID selects a
record. Missing profiles return 404 `PROFILE_NOT_FOUND`; stale writes return 409
`PROFILE_REVISION_CONFLICT`. Missing/invalid storage configuration and storage errors
return 503 `PROFILE_UNAVAILABLE`, with sanitized `detail: {code}` bodies.

PUT shape: `{ "expected_revision": 0, "fields": { ... } }`. Revision 0 creates only
when absent; later writes atomically compare the last received revision. A successful
response is `{ "profile_id": "...", "revision": 1, "fields": { ... } }`. Every PUT
replaces all six values; omitted values become null. GET never creates a record.

Production storage is built in `create_app` lifespan through
`portal.postgres.build_profile_service`. Its public `close()` runs once at shutdown;
explicitly injected services are caller-owned. Missing configuration or sanitized
factory failure leaves storage unavailable, while `/health` still reports process
health. Test clients that check lifecycle behavior must use `with TestClient(app)`.

Profile edits in a form are a local copy: preview/PDF requests do not save the account.
Only an explicit authenticated PUT changes the profile.

App-owned fields are `full_name`, `date_of_birth`, `nationality`, `address`,
`phone_number` and `email`. All six fields appear in the response, with `null`
for missing values. Unknown fields, control characters and oversized text are
rejected. A date is null or a real ISO `YYYY-MM-DD` date; an empty date normalizes
to null. Email/phone remain bounded text;
this scaffold does not establish mailbox/number ownership or legal validity.
These are not an approved official-form field mapping.

Tests use synthetic identities and locally generated signed tokens. They block
outbound HTTP and do not use real Clerk credentials. Unit/API checks do not
establish live sign-in, real PostgreSQL/TLS/RLS, browser sign-in or end-to-end integration.
Production-route tests exercise repository owner predicates and concurrent revisions
with a disposable SQLite fixture; this is separate from PostgreSQL evidence.

References used for the integration:

- [Clerk Python SDK](https://github.com/clerk/clerk-sdk-python)
- [SDK authentication source](https://github.com/clerk/clerk-sdk-python/blob/main/src/clerk_backend_api/security/authenticaterequest.py)
- [SDK verification source](https://github.com/clerk/clerk-sdk-python/blob/main/src/clerk_backend_api/security/verifytoken.py)
- [FastAPI application lifespan](https://fastapi.tiangolo.com/advanced/events/)
