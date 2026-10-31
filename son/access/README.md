# Agent access authorization — ACCESS-01

Independent Python 3.12+ core owned by Son. The core has no runtime dependencies.
The optional `profile_adapter` consumes Kim's installed application dependencies.
No HTTP server, login implementation, database or application UI is provided.
The default core identity verifier denies every operation; the profile reader
requires an injected Kim verifier and trusted API client.

Run the offline synthetic tests from the repository root:

```powershell
python -m unittest discover -s son/access/tests -v
```

For server imports, add `son/access/src` to the host's Python module search path.
There is no dependency on the unmerged `son/voice` package.

## Integration review status

**Current delivery:** read-only `ProfileReader` now consumes Kim's actual published
`app.v1` models and `ClerkSessionVerifier` interface at
`ae77fa8bd47d590a53d26690b687bcad80692a9b` on
`origin/codex/kim/app-01-profile-integration`. The earlier missing-source blocker
is superseded for isolated profile-consumer development. See
[INTEGRATION.md](INTEGRATION.md) for remaining lifecycle/identity dependencies.

`ProfileReader.read(credential, context)` takes a credential for this call only,
checks it using the injected existing Kim verifier, compares both verified
subject and session ID to the trusted dispatch context, and performs one
`GET /v1/profile` through an injected API-origin HTTP client. It never sends a
client-selected owner or profile ID and never creates/updates a profile. No
credential is stored on the adapter. The dedicated client must use the agreed
trusted API origin, verify TLS in deployment, and have no credential/body logging
or untrusted response hooks. The host owns/cleans up the client and verifier.

Response validation imports `ProfileFields` and `ProfileResponse` from `hoso_api`;
there is no copied schema. All actual response fields and metadata are validated,
then only the approved field values are returned. Profile ID/revision and other
personal fields do not reach the tool result. Null values are preserved. The
current API returns a full profile to the trusted adapter; field minimization is
at the model boundary, not an assertion of upstream partial-read support.

`ToolContext` now also includes the verified `auth_session`, populated by core
dispatch. Internal callers constructing it directly must supply that fifth field;
never create it from client/model input. The adapter is invoked only within
authorization dispatch, with a matching credential for the current server request.
It is not itself an approval endpoint. The test-only credential closure is not
a production credential store or a lifecycle integration.

`ToolFailure` allows four value-free outcomes through dispatch:
`PROFILE_NOT_FOUND`, `PROFILE_UNAVAILABLE`, `PROFILE_RESPONSE_INVALID`, and
`AUTH_UNAVAILABLE`. Invalid credentials/account/session remain `AccessDenied`.
The reader accepts the documented 404 body; rejects redirects, missing `no-store`,
invalid JSON/types/fields/envelopes and unexpected statuses; bounds response
validation to 16 KiB and supplies a configurable five-second request timeout.
It performs no retry. A GET returning 409 is a protocol failure; `expected_revision`
belongs to explicit PUT and is not implemented here. Error bodies/exception
details are not echoed. These internal outcomes are not new public HTTP routes.

The HTTP client buffers before the size check and its timeout is not a total
operation deadline. Configure transport/payload limits in the host as well.
Kim's local JWT verifier explicitly does not prove immediate session revocation;
live logout handling and canonical voice-session integration remain unverified.

### Reproduce isolated contract tests

The tested producer is pinned, not the moving branch head. Export its existing
source into ignored `work/` (no code/schema is vendored into this component):

```powershell
git fetch origin
New-Item -ItemType Directory -Force work/access-app-v1 | Out-Null
git archive --format=zip --output=work/access-app-v1/source.zip ae77fa8bd47d590a53d26690b687bcad80692a9b api docs/application-contract.md docs/clerk-configuration.md docs/profile-integration-handoff.md web/lib/contracts.ts web/lib/profile.generated.ts
python -m zipfile -e work/access-app-v1/source.zip work/access-app-v1/source
uv sync --project work/access-app-v1/source/api --frozen
$env:PYTHONPATH = "$((Resolve-Path son/access/src).Path);$((Resolve-Path work/access-app-v1/source/api).Path)"
work/access-app-v1/source/api/.venv/Scripts/python.exe -m pytest son/access/contract_tests -q
python -m unittest discover -s son/access/tests -v
```

On this machine uv is installed only in ignored `work/access-adapter-env`; replace
`uv` with `work/access-adapter-env/Scripts/uv.exe` for the command above. The tests
reuse the pinned producer's fixtures (actual registered routes, local Clerk JWT
verification and actual profile service/repository over disposable SQLite). Keys,
tokens and data are synthetic and never persisted in tracked files. Source-pin
checks compare imported producer files to the exact Git commit. External HTTP is
blocked. Protocol failure tests use `httpx.MockTransport`. These checks do not
exercise Next/browser, live Clerk, PostgreSQL, RLS or the voice lifecycle.

### Earlier integration review and remaining scope

The voice lifecycle remains **adaptation required**, not a production-ready integration.
See [INTEGRATION.md](INTEGRATION.md) for the exact reviewed voice commit, lifecycle
gaps and required Kim interfaces. Reuse Kim's existing Clerk setup, `app.v1`
profile types and `/api/profile` -> `/v1/profile` path. The producer contract is now
received at the pinned application commit above; deployed interoperability is pending.
No second profile store, identity mapping, auth server or conversation lifecycle
may be introduced. In particular, the current `start()` mints an independent ID;
it must be adapted to the canonical voice lifecycle before a personal tool is
enabled. The methods below describe today's isolated core, not an accepted wire
contract. No production integration is implemented in this package.

## Server integration boundary (proposal, not agreed with Kim)

Create one `Authorization` instance per server process. Only trusted server code
configures the `verifier` and `tools`. Do not expose its Python constructors or
register callbacks from browser/model input. Do not register tools with Realtime
until the server dispatcher and authenticated transport have been integrated.

The verifier accepts the host's opaque request credential and returns
`VerifiedIdentity(subject, auth_session, expires_at)`. It must verify the actual
authenticated session on **every call**, including logout/revocation, signature,
issuer, audience and expiry as applicable to the chosen provider. Failures raise
an exception and are denied. Client-supplied account IDs, voice cookies, telephone
numbers, transcripts and the `VerifiedIdentity` class itself are not credentials.
Never reuse an auth-session identifier after logout. Verifier output expiry uses
the same monotonic clock as this service; convert provider epoch expiry using the
remaining verified lifetime. Do not serialize monotonic timestamps as wall dates.

The method sequence is:

1. `start(credential, procedure=...)` creates a random conversation ID bound to the
   verified account, exact login session and server-allowlisted procedure. Connect
   its lifetime to the voice conversation: hangup/reset must call `end` while the
   authenticated session is still valid. Expired or logged-out credentials always
   block further operations even if cleanup has not run.
2. `request(credential, conversation_id, scope=Scope(tool, frozenset(fields)))`
   creates an unpredictable approval request. The server's tool policy limits
   fields by procedure. A new request revokes older pending/approved requests in
   that conversation; currently only one grant is active at a time.
3. `inspect(...)` gives Kim's authenticated approval UI the procedure, conversation,
   fields, state and expiry. The host must use trusted display labels and convert
   expiry to remaining seconds. These are sensitive responses: `Cache-Control:
   no-store`, no request/response-body logging, no credentials or IDs in URLs.
4. `decide(..., approve=True/False)` consumes a pending request exactly once.
   Decision is bound to the same account **and login session**. Only an explicit
   authenticated UI decision calls this method. Never map a model/spoken response
   to `decide`. Concurrent decisions have one winner; replay is denied.
5. `dispatch(..., scope=...)` checks the live identity and grant on every tool call,
   then executes only the registered callback with a server-derived owner. There
   is no client-selected record owner, model-provided callback or unrestricted
   tool argument dictionary. Tool and fields must be a subset of the approval.
6. `revoke(...)` cancels the request/grant; `end(...)` invalidates the conversation
   and all its grants. Refused, revoked or expired requests cannot be approved
   again. To ask again, create a new approval request visible in the UI.

`AccessDenied` has a generic message. Allowlisted `ToolFailure` outcomes from the
profile reader pass through dispatch; unexpected adapter errors are sanitized. Hosts
must also return generic validation errors and avoid echoing credentials/input.
`CapacityReached` indicates a local capacity limit, not an account-existence check.

No HTTP routes are exposed. Kim's application commit and configuration manifest
are received. Live Clerk instance settings, immediate-revocation behavior and
consent/voice transport still require agreement; no deployment values are guessed.
Those checks must wrap **all** future routes, including approval/inspection and
tool dispatch. Never accept an unverified subject header or JSON principal.
Public procedure lookup remains separate: it does not need personal consent, but
still requires Vincent's reviewed-data gates. This module defines no procedure
record schema and makes no legal eligibility decisions.

## Callback requirements

`Tool.allowed` maps procedure identifiers to immutable allowed field names. The
tool name identifies the action (separate read/write actions require separate
tools). These policies are server-owned and have no production defaults here.
`Tool.run(context)` receives the authenticated owner, conversation, procedure and
requested fields. The dossier/report service must independently verify ownership
and authenticate interservice requests; this check does not replace Kim's checks.

Callbacks must return a mapping with exactly the requested top-level field keys.
Additional/missing keys are rejected before anything is returned to the caller.
Adapters must constrain nested content too; the top-level check cannot establish
that an arbitrary nested object contains only permitted personal information.
Never return a whole dossier under one permissive field name.

Dispatch and revocation share one lock. A synchronous callback admitted before
revocation may complete; revocation cannot undo an existing read or transmission.
Callbacks must complete quickly, set I/O timeouts, and never call back into this
service (the lock is non-reentrant). This implementation deliberately serializes
calls; it is not an async/distributed execution engine. An error after a write
cannot roll back its side effects. Write adapters need their own idempotency and
transaction design before registration. There are no write adapters here.

## Limits and defaults

- Conversation: 600 seconds at most, also bounded by initial login expiry.
- Pending approval: 120 seconds, bounded by conversation/login expiry.
- Approved grant: 600 seconds from decision, bounded by conversation/login expiry.
- Defaults configurable pending agreement with Kim; approval does not extend the
  conversation. Credential refresh does not extend its initial bound either.
- At most 1,000 conversations per instance, four per login session and 20 approval
  requests per conversation. Expired conversations are removed lazily on access.
  These are memory bounds, not deployment-wide abuse/rate protection.
- Memory only, no transcripts/dossiers/credential retention or built-in logging.
  Account/session IDs and approval metadata exist in private process memory until
  conversation end/expiry cleanup. Restart loses all grants and denies old IDs.
- Single process only: do not deploy multiple independent workers. A shared store
  with atomic transitions and a verified revocation mechanism is required first.
- Synthetic tests cover the core, not provider verification, HTTP/CSRF, browser
  login, actual logout delivery, Kim's dossier owner checks or voice-to-report.

Integration order: receive Kim's exact scaffold/app.v1 contract and agreed Clerk
configuration -> adapt authorization metadata to the existing voice lifecycle ->
implement the agreed verifier and protected server adapters -> wire tools -> run
SECURITY-01 with two synthetic accounts -> verify voice/report version agreement
when Vincent's reviewed records and Kim's report are available.
