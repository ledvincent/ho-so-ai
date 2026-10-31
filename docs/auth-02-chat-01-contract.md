# AUTH-02 / CHAT-01 local checkpoint HTTP contract

Draft consumer seam, 2026-10-31; backend owner Kim, UI owner UI-02. Based on
`b07e28e74b4b9174979b7922ad3576d0562c778a`. Published app.v1/Clerk remains unchanged.
This branch adds an explicit LOCAL identity provider for a single-machine SQLite
checkpoint. It is a proposal for Son's future adapter, not accepted team-wide auth.
No UI pages/components/styles are owned by this task. No public deployment.

## Browser routes (Next same-origin proxies)

All responses are `Cache-Control: no-store`. Auth/chat errors use
`{"detail":{"code":"STABLE_CODE"}}` (validation may also include safe issue
locations). Existing profile and synthetic-form proxies preserve app.v1 behavior:
proxy failures can use top-level `{"code":"STABLE_CODE"}`, including
`REQUEST_REJECTED` for origin failures, while upstream API errors use `detail`.
Consumers must handle both existing shapes. Never display raw upstream/provider
errors. Mutation requests require JSON and exact configured Origin.
Use `credentials: "same-origin"`.

| Method / browser route | Request | Success |
| --- | --- | --- |
| POST `/api/auth/login` | `{username:string,password:string}` | 200 `{user:{id,username,identity_provider:"local"},expires_at:number}` + HttpOnly cookie |
| GET `/api/auth/session` | No body | 200 same user/expiry shape; 401 if absent/expired/revoked |
| POST `/api/auth/logout` | `{}` | 200 `{ok:true}`; revoke server session and clear cookie |
| GET/PUT `/api/profile` | Existing app.v1 | Existing six fields/owner/revision/error semantics, unchanged |
| GET `/api/chat/schema` | No body | 200 `{procedure_code:"1.001146",schema_version:string,review_status:"draft",fixed_values,fields:[43 original definitions]}` |
| POST `/api/chat/assist` | Shape below | 200 validated proposal, never an implicit form/profile write |

API equivalents are `/v1/auth/*`, `/v1/profile`, `/v1/chat/schema`, `/v1/chat/assist`.
Next sends opaque session credentials only server-to-server in Bearer headers.
API login additionally returns `session_token` to the Next server; Next MUST strip
it from browser JSON and set `hoso_local_session` with HttpOnly, SameSite=Lax,
Path=/ and Secure on HTTPS. No localStorage/sessionStorage token. Missing auth401;
invalid login401 `INVALID_CREDENTIALS`; invalid origin403 `ORIGIN_FORBIDDEN`;
throttle429 `RATE_LIMITED` + Retry-After; unconfigured503 `AUTH_UNAVAILABLE`.

```json
{
  "request_id": "client-generated-unique-id",
  "draft_revision": 3,
  "procedure_code": "1.001146",
  "intent": "form_answer",
  "message": "My full name is Synthetic Nguyen",
  "focus_field": "applicant_full_name",
  "values": {"request_type":"stay_extension"}
}
```

`request_id`: 1..80 safe ASCII characters; `draft_revision`: nonnegative integer;
message <=2000 characters, values only the exact NA5 schema keys. `focus_field`
may be null for initial guidance; empty message requests the next question without
a model call. `intent` is `form_answer` or `procedure_question`.

```json
{
  "request_id":"client-generated-unique-id",
  "draft_revision":3,
  "procedure_code":"1.001146",
  "schema_version":"sha256-of-exact-workflow",
  "status":"proposed",
  "assistant_text":"Please review the proposed name. What is your sex?",
  "proposed_changes":[{"field_id":"applicant_full_name","value":"Synthetic Nguyen"}],
  "next_field":"sex",
  "review_status":"draft"
}
```

Statuses: `proposed`, `needs_clarification`, `question`, `complete`. A proposal is
data, not trusted HTML and not a saved profile. UI MUST accept it only if both
request_id and draft_revision still match its active request/current draft and
the same authenticated user is still active. On every edit/account transition,
abort pending work and advance revision; discard late responses. Applying a
proposal advances the local draft revision. Profile save remains explicit PUT.

The server validates structured output against active fields, source evidence,
type/choice/date/length rules and fixed/manual exclusions; invalid output502
`ASSISTANT_INVALID_OUTPUT`, unavailable provider503 `ASSISTANT_UNAVAILABLE`,
timeout504 `ASSISTANT_TIMEOUT`. Ambiguity yields no changes and one clarification.
No signature/stamp or fixed request_type may be generated. Inactive sponsor
branches cannot receive values. Changing a selector requires clearing its now
inactive dependent fields locally before the next request. No field truncation.
`assistant_text` and the next question are generated deterministically by the
server from the schema; model prose is never displayed as application guidance.

`procedure_question` uses Vincent's separate `/assistant/chat` contract when an
approved runtime is supplied; this checkpoint returns503 `RETRIEVAL_UNAVAILABLE`
until then. Procedural prose is never parsed as a form patch; no fabricated citations
or second RAG pipeline. Son owns voice/conversations; this narrow stateless text-form
adapter can be replaced by his consumer through this boundary.

## Identity, storage and runtime

LOCAL subjects contain an immutable database namespace plus random user ID and
cannot be Clerk subjects. Passwords use scrypt; opaque expiring sessions are stored
hashed in SQLite and revoked at logout. The existing ProfileRepository/Service is
used through an explicit SQLite transaction adapter; no competing profile schema
or owner/revision implementation. SQLite is not PostgreSQL/RLS.

Local checkpoint config is explicit, default disabled: `HOSO_AUTH_PROVIDER=local`,
`HOSO_LOCAL_DB_PATH=<ignored absolute SQLite path>`,
`HOSO_PUBLIC_ORIGIN=http://127.0.0.1:3016`, API loopback8016. Test/demo seed
admin/admin requires a separate loopback/test opt-in; never a deployment default.
Second synthetic account is provided for isolation acceptance, not public signup.

Frontend paths `/portal`, `/workspace`, `/chat`, `/forms`, `/research`, `/documents`
and `/demo` (including descendants and dotted document paths) verify the server
session. `/login`, `/demo/login` and sign-in paths remain public. Protected APIs
verify independently. Unauthenticated private page requests redirect to `/login`;
unconfigured authentication fails closed with503. Existing UI-01 preview3014/API8014
stays untouched. UI-02 supplies the actual LOCAL `/login` page and account views;
this backend-only baseline does not provide that interactive screen.

Logout clears the browser cookie even if upstream revocation cannot be confirmed,
returning503 `LOGOUT_UNCONFIRMED` in that case. The UI must surface that failure;
cookie removal alone is not evidence that all copies of a session were revoked.

NA5 source: Vincent `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`, exact
`data/forms/NA5/workflow.json` (43 fields). Preserve all definitions, fixed
stay_extension and conditional branches; template remains draft. This checkpoint
does not approve or unlock an official download. Model defaults to `gpt-4o-mini`;
server loads the authorized existing OPENAI_API_KEY in memory from its original
ignored env file, never copies it or exposes it to the client. At most three short
fictional live smoke calls, no automatic retries; all other tests mock the provider.

Next owner acknowledgement: UI-02 should consume these routes/shapes and report
any mismatch before implementing competing handlers. Backend owns proxies/auth
middleware/shared configuration; UI owns views only. Manager owns Kim's status.
