# ACCESS-01 integration review

Review date: 31 October 2026 (Asia/Saigon). This is a dependency/request checklist,
not an implementation of Kim's API or an agreed external contract.

## Current read-adapter delivery

Kim's application source is now published on
`origin/codex/kim/app-01-profile-integration` at
`ae77fa8bd47d590a53d26690b687bcad80692a9b`. The actual application contract,
Clerk configuration, profile model, auth implementation, API composition and
profile service/repository were read. The earlier checkpoint-only source blocker
is superseded for this read adapter.

`ProfileReader` implements only GET profile consumption using Kim's injected
verifier and imported profile models. It compares the verified subject/session
to `ToolContext`, validates the envelope and projects approved fields. Core
dispatch now supplies `auth_session` and preserves allowlisted `ToolFailure`
codes. See README for inputs, outputs, errors and reproduction. No external API,
schema, identity mapping or profile store was added.

Acknowledgement: **received; isolated consumer checks passed; voice/production
adaptation required**. Consumer files remain uncommitted; no consumer commit or
full `tested compatible` declaration is available. Observed: 28 adapter tests,
24 core tests and producer generated-contract check pass. Adapter tests reuse
the pinned producer's actual route/JWT/service/repository fixtures over disposable
SQLite with external HTTP blocked; protocol tests use MockTransport. Next,
live Clerk, PostgreSQL and canonical voice lifecycle are not tested.

## Evidence and acknowledgements

| Dependency | Exact evidence inspected | Acknowledgement |
| --- | --- | --- |
| Shared guidance | `17900c3234add2a8c81c323e10a20d44dde88f1e`: `docs/team/managers/start-prompt.md`, `son.md`, `kim.md`, workflow, decisions and contracts | received; reuse Clerk, `app.v1`, generated profile types and existing profile routes; Vincent owns retrieval/RAG |
| Voice implementation | Local branch `codex/son/voice-01-browser-conversation` at `d934436a3ba692b3fda8876ff3cd888683ded7d0`: `app.py`, `sessions.py`, `realtime.py` | adaptation required; static code review only, not tested compatible |
| Kim checkpoint | `845291a04329324791c6ecf726037577ef8986e1`: published `docs/team/status/kim.md` on `origin/codex/kim/team-05-integration-checkpoint` | received as a status report only; local application commits and test results are producer-reported, not independently reproduced here |
| Kim scaffold/profile | Actual source at `ae77fa8bd47d590a53d26690b687bcad80692a9b`; `app.v1`, application contract/generated types, API model/auth/routes/service/repository | received; 28 isolated read-adapter tests and generated-contract check pass; consumer uncommitted, no production/voice compatibility claim |
| Kim consent/identity transport | No delivered consent contract or Clerk instance/configuration received in this review | blocked for implementation; no production verifier or consent route added |
| Vincent retrieval/procedures | Ownership guidance received; no delivered lookup/schema reviewed here | blocked for actual procedure/report data; no alternate retrieval service or procedure schema |

Missing received evidence is not evidence that another member has not worked.

## Earlier Kim checkpoint: historical proposal, not a copied schema

At the earlier checkpoint, application branches were explicitly not published.
`git ls-tree` at its exact SHA contains none of `docs/application-contract.md`,
`docs/clerk-configuration.md` or `web/lib/profile.generated.ts`. The checkpoint
updated dependency knowledge but did not unblock a consumer at that time.
The entries below preserve that initial proposal. The current implementation and
evidence above supersede the earlier source-availability gap.

| Reported by Kim | Initial proposed consumer mapping | Required at that earlier checkpoint (historical) |
| --- | --- | --- |
| Six-field `app.v1` with generated profile types | Derive allowed field names/subsets from the delivered authoritative types; no field list or profile model copied into ACCESS-01 | Publish source schema/types and read envelope/nullability/nested-content rules; confirm partial-read support |
| Same-origin Next proxy obtains a Clerk token server-side and forwards it to the API | Reuse this trust path and the existing owner derivation. The public voice cookie and a browser/model owner ID remain insufficient | Exact published proxy/auth code, Clerk configuration reference and agreed transport from the voice host to that boundary, including session/revocation checks |
| GET does not create profiles; absent profile returns 404 | Treat absence as absence. Do not create/seed a profile during a read or fall back to synthetic data | Exact missing-profile response/error contract and approved UI handling |
| Creation uses revision 0; updates use `expected_revision`; stale writes return 409 | Keep optimistic concurrency distinct from consent. No personal write adapter is registered here; do not automatically retry a conflict with a newer revision or silently save a document edit to the profile | Exact revision type/response envelope, write semantics and explicit action/field consent before any later write adapter |
| Unavailable storage returns 503 | Surface an unavailable outcome through the agreed host contract; never invent a successful profile result | Published error shapes and timeout/retry policy. Current core collapses callback exceptions into generic `AccessDenied`; a future adapter/error mapping needs review before claiming these statuses are preserved |
| Private/no-store profile responses | Preserve private response handling and keep credentials/personal payloads out of logs/cache | Exact proxy/service headers and tests, including denied/error responses |

Revision/error metadata must not be guessed into `Scope.fields` or smuggled into
a permissive profile object. The core currently requires exactly the requested
top-level field keys; handling the real profile envelope and revision metadata
was an adaptation question. The implemented reader now validates Kim's full
envelope and returns only requested fields, dropping profile ID/revision. It maps
documented 404 and 503 to safe internal failures; 409 on GET is unexpected and
rejected. No PUT/write adapter or public HTTP status mapping is provided.

## Existing voice lifecycle and required adaptation

At the inspected voice commit:

- `POST /api/voice/session` closes the previous realtime call and calls
  `PublicSessions.create(old_token, language)`. It sets the HttpOnly
  `hoso_public_voice` cookie scoped to `/api/voice`. That cookie is public dialogue
  state, not a Clerk identity. Its raw value must not be sent to consent UI as an
  identifier or used as proof of account ownership.
- `PublicSessions` owns a 600-second absolute expiry, reset/end and capacity.
  `remaining(token)` checks liveness. It has no account binding, consent metadata,
  public conversation identifier or invalidation subscriber.
- `POST /api/voice/realtime` uses the existing public session. `RealtimeCalls`
  leases a call for `min(180 seconds, session remaining)`; `_expire`, `end` and
  `close` stop provider calls. `DELETE /api/voice/realtime` ends the call but leaves
  the public session alive. `DELETE /api/voice/session` ends both.
- `call_configuration()` has `tools=[]`, `tool_choice='none'`; personal tools are
  disabled in health/capabilities. Audio opt-in is not personal-data consent.

The following lifecycle changes belong to a later, agreed Son integration patch.
They are not implemented by the isolated profile reader:

| Current ACCESS-01 gap | Concrete impact | Required integration change |
| --- | --- | --- |
| `Authorization.start()` creates another random conversation ID and its own lifetime | Calling it alongside `PublicSessions.create()` would create two independently live conversations | Reuse the canonical voice session/lifecycle. Keep only authorization metadata keyed to its server-owned binding; expose a non-secret conversation reference only through the agreed host interface. Do not add a parallel conversation service or reinterpret the public cookie as identity |
| Core has no liveness source for `PublicSessions` or `RealtimeCalls` | An approval could remain valid after hangup/reset/lease expiry if the caller only uses the core | Check canonical conversation/call liveness on each personal tool call and invalidate grants on reset, session end/expiry, realtime hangup/lease expiry and shutdown. Provider hangup failure must not preserve local authorization |
| `end()` requires a currently verified user credential | Timer/shutdown cleanup has no user request; cleanup after logout may be denied | Agree an internal trusted lifecycle invalidation hook with the voice owner. It must act only on server-owned bindings; never expose an unauthenticated revocation endpoint. Ongoing identity checks still deny logged-out sessions |
| Procedure is mandatory and fixed at `start()` | Voice starts before clarifying registration vs renewal | Attach procedure-scoped authorization only after the canonical conversation has a selected supported procedure. Changing that procedure must invalidate pending requests/grants; a candidate intent is not a reviewed record |
| Same subject and exact `auth_session` are required by all methods | Approval from another login/device is refused; a refreshed token may have different expiry semantics | Reuse verified Clerk identity/session semantics agreed with Kim. Specify refresh, logout and cross-device approval behavior explicitly; do not invent a second local account ID mapping |
| Verifier and tool callback are synchronous under a global lock | Network verification/profile reads can block concurrent calls and an async event loop | Agree the host execution model, timeout bounds and atomicity. Do not simply await network I/O under this thread lock or deploy independent workers with separate grant stores |

The public voice flow can remain public. Personal access must require a verified
Clerk session bound to the canonical conversation. No profile copy/store is
needed. The profile owner is derived from the delivered verified identity, not
from model text, a JSON account ID or a client-selected profile identifier.

## Exact inputs needed from Kim

Kim remains owner of her implementation and wire contract. These are requested
artifacts/decisions, not invented endpoints or field names:

1. **Delivery reference received:** the reader pins
   `ae77fa8bd47d590a53d26690b687bcad80692a9b`, including the actual contract,
   generated types, Clerk configuration and integration handoff. Kim should
   identify a changed authoritative producer SHA before consumer migration.
   Source publication no longer blocks this isolated read implementation.
2. **One Clerk setup:** integration-test instance/issuer, authoritative key
   discovery/configuration source, authorized parties, audience if used, allowed
   browser/service origins, token transport and intended service recipient.
   Supply secret values through the existing private environment mechanism,
   never Git or chat. Do not create a separate Clerk application for ACCESS-01.
3. **Verified identity boundary:** which trusted component validates credentials,
   which verified claims identify the existing profile owner and login session,
   how current revocation/logout is checked and how token refresh/expiry is
   represented. Any cross-service identity envelope needs an agreed authenticated
   channel; unsigned subject/session headers are insufficient.
4. **Profile consumer contract:** authoritative request/response and errors for
   the existing `/api/profile` -> `/v1/profile` path, owner enforcement, permitted
   field names/partial reads, nested-data minimization, service authentication
   and timeout behavior. If partial reads are unavailable, agree an adapter with
   Kim rather than inventing another route or copying profiles. `app.v1` is a
   profile contract version, not a procedure/checklist version. Confirm the
   checkpoint's six fields, `expected_revision`, creation revision 0, GET without
   creation and 404/409/503 against the actual schema/code. Supply exact envelope,
   revision and error types rather than another prose schema maintained here.
5. **Consent UI/decision contract:** how Kim receives the server-created request
   reference, canonical conversation reference, procedure, named action/fields,
   expiry and state; how explicit approve/deny/revoke is authenticated and bound
   to that exact request/account/session. Specify request/response schemas,
   replay/conflict/error behavior and CSRF/origin requirements. No URI, HTTP
   method or JSON spelling is assigned by this review.
6. **Lifecycle/security test contract:** logout notification or current-session
   verification behavior, account switching, refresh and whether approval is
   confined to the same login session. Provide two synthetic accounts/profiles
   and expected ownership/consent failures, without committing their credentials.

## Exact inputs/actions needed from Son

- Voice owner confirms the inspected voice commit or provides the newer exact
  delivery SHA; agrees the canonical conversation reference, account binding,
  liveness query and lifecycle invalidation hooks in `PublicSessions`/Realtime.
  Reuse that owner’s files; this review does not modify `son/voice/`.
- Agree whether a fresh call on the same public session always requires new
  consent. Safe target: end/hangup invalidates personal grants, and reconnect
  never silently restores them. Preserve public dialogue behavior separately.
- Implement only the agreed server verifier/transport after receipt of Kim's
  artifacts. Model/browser code cannot register tools or supply trusted identity.
- Map allowed tool actions/fields to the received `app.v1` types and approved
  scope; keep personal Realtime tools disabled until server dispatch is enforced.
- Coordinate the host's process model, origins, timeout/rate limits and secret
  loading with the existing application owner. No new server, port or shared
  dependency/configuration change is part of this review.
- With Kim, test valid approval, direct access without approval, wrong account,
  wrong login/conversation/procedure, denied/expired/revoked requests, replay,
  logout/refresh, hangup/reset/lease expiry and concurrent decision/invalidation.
  Require no callback after invalidation and no extra/nested profile leakage.
- Consume Vincent's delivered reviewed procedure/version/checklist separately;
  preserve that exact version into Kim's report. Do not derive legal facts from
  `app.v1` profile fields or generated voice text.

Acceptance requires exact producer/consumer SHAs and actual combined checks.
An inspected reference, a message or the isolated 24 tests is not `tested compatible`.
