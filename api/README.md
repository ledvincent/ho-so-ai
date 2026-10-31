# Application API scaffold

Python 3.12+, FastAPI, Pydantic and the official Clerk Python backend SDK.
The database driver/SQLAlchemy dependencies prepare the accepted PostgreSQL
stack; this scaffold opens no database connections and creates no schema.
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
- `DATABASE_URL`: reserved for the profile repository; unused by this scaffold.

Missing auth configuration fails closed with 503 on protected routes. Invalid
or missing credentials produce 401. Verification uses Clerk's SDK with a local
public key, explicit authorized parties and session-token restriction, followed
by required issuer/subject/expiry/session-ID checks. No remote-key fallback is
configured. Key rotation therefore requires updating the configured public key.

Clerk's local signature checks do not establish immediate logout/revocation
status; sessions remain subject to their token expiry. The portal/security task
must resolve the team's immediate-revocation requirement before claiming it.

## Profile boundary

`GET /v1/profile` and `PUT /v1/profile` authenticate, then return **501** because
storage and server-side owner checks are assigned to the portal task. No fake
save or profile lookup is represented as persistence.

PUT shape: `{ "expected_revision": 0, "fields": { ... } }`. Revision 0 means first
creation; later writes compare the last received revision. The eventual response
is `{ "profile_id": "...", "revision": 1, "fields": { ... } }`. The portal task
will implement 404 for no profile and 409 for a compare-and-swap conflict.

App-owned fields are `full_name`, `date_of_birth`, `nationality`, `address`,
`phone_number` and `email`. All six fields appear in the response, with `null`
for missing values. Unknown fields, control characters and oversized text are
rejected. A date is null or a real ISO `YYYY-MM-DD` date; an empty date normalizes
to null. Email/phone remain bounded text;
this scaffold does not establish mailbox/number ownership or legal validity.
These are not an approved official-form field mapping.

Tests use synthetic identities and locally generated signed tokens. They block
outbound HTTP and do not use real Clerk credentials. Unit/API checks do not
establish live sign-in, profile isolation, database RLS or end-to-end integration.

References used for the integration:

- [Clerk Python SDK](https://github.com/clerk/clerk-sdk-python)
- [SDK authentication source](https://github.com/clerk/clerk-sdk-python/blob/main/src/clerk_backend_api/security/authenticaterequest.py)
- [SDK verification source](https://github.com/clerk/clerk-sdk-python/blob/main/src/clerk_backend_api/security/verifytoken.py)
