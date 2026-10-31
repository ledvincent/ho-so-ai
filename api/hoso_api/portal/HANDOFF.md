# AUTH-01 portal consumer handoff

Owner: Kim portal workstream. Status: component implementation prepared; shared
route/storage integration pending. This handoff is the portal's scoped record;
the scaffold owner/manager remains the single writer of `docs/team/status/kim.md`.
No private chat identifiers are included. No push, merge, deployment, official
form approval or live migration is authorized or performed by this delivery.

## Exact delivery received

- Producer APP-01: `dc0ea22265df27210d6375f1bb1a3e6d118d839b`.
- Consumer branch: `codex/kim/auth-01-clerk-portal`.
- Worktree: `.worktrees/kim-portal-clerk`; HEAD matched the producer SHA and the
  worktree was clean before implementation.
- Contract: [app.v1](../../../docs/application-contract.md), generated six-field
  profile, `/api/profile` -> `/v1/profile`, shared verified Clerk subject.
- Acknowledgment: **received; adaptation required**. The exact models and shared
  verification were read and consumed. Production profile routes still return
  501; their owner must inject the service below. This is not an end-to-end
  `tested compatible` acknowledgment or AUTH-01 completion.
- Manager protocol `4c5f28516b70305baf022677ac1ca5789a09ca11` was fetched and read
  via Git, including `protocol.md` and `start-prompt.md`, without merging it.
- Ownership correction `6f14e32d75edcde9ff27b1d5b6337a2f27ff17f0` was fetched
  and read without merging. Son owns voice, conversation sessions and server-side
  tool authorization. Vincent owns document retrieval/search through RAG, sources,
  source review and the procedure-data contract; Son consumes that interface.
  No retrieval implementation is assigned to Kim or duplicated in this workstream.
- The previous `.worktrees/kim-portal` Auth0 draft is preserved locally and must
  not be pushed. Its historical coordination note includes a private chat ID;
  any future publication requires a separately agreed sanitization proposal,
  without rewriting that preserved history or changing another writer's files.

## Implemented within assigned paths

- `web/app/portal/` and `web/components/portal/`: Vietnamese profile editor,
  explicit save, safe error states, revision conflicts, cancellation and session
  reset. Uses existing Clerk integration and same-origin `/api/profile` only.
- `api/hoso_api/portal/`: owner-filtered repository, sanitized service, proposed
  handler adapters and PostgreSQL transaction provider. No router is registered
  by this module and no schema is created at startup.
- `api/tests/portal/` and `web/components/portal/*.test.ts`: synthetic tests.
- Shared auth, `profile.py`, route registration, proxies/types, generated fields,
  manifests, lockfiles, root configuration and forms are unchanged.

The repository takes `AuthenticatedUser` from the shared verifier. No browser
owner or profile ID selects the record. The subject is the existing ownership
key; the random `profile_id` identifies a profile, not a new account mapping.
GET has no creation side effect. PUT replaces all six values, including nulls.
Creation requires `expected_revision=0`; an existing record conflicts. Positive
updates check owner and revision atomically, increment once, return 404 if the
owner has no profile and 409 for an existing stale revision.

Sessions/documents are deliberately not implemented: Son and their producers
must supply identifiers, revisions and ownership contracts first. No invented
document links or competing session registry are supplied.

## Concrete integration proposal for the scaffold owner

Review and implement these shared-file changes in the owner's task; they have
not been applied by the portal workstream:

1. In `create_app`, inject a `ProfileService` into `app.state.profile_service`.
   The production factory is `portal.postgres.build_profile_service(config)`.
   It returns `None` when database/issuer configuration is missing; invalid or
   downgraded connection configuration raises sanitized `StorageUnavailable`.
   Establish application-lifetime engine cleanup in the shared lifecycle before
   deployment. The transaction provider exposes `close()` for disposal.
2. In the two existing `profile.py` handlers, receive `Request` alongside
   `CurrentUser` and call the portal adapters. Local imports in the handlers
   avoid a circular import because the portal consumes the shared profile models:

   ```python
   # Inside the existing GET handler, keeping its route/response_model:
   from .portal.handlers import read_profile
   return read_profile(request, user)

   # Inside the existing PUT handler, keeping validation and CurrentUser:
   from .portal.handlers import write_profile
   return write_profile(request, user, payload)
   ```

   Adapter error proposal: `detail: {code: "PROFILE_NOT_FOUND"}` (404),
   `PROFILE_REVISION_CONFLICT` (409), `PROFILE_UNAVAILABLE` (503). The UI relies
   on status codes and never displays raw upstream content. The owner should
   accept/document these codes and update the existing 501 expectation tests.
3. Keep the generated model, auth dependency, private-response headers and
   same-origin proxy unchanged. No new profile route or frontend token exchange.
4. FORM-02 owns the actual prefill interface: explicitly GET `/api/profile`,
   copy the six values into the form draft, and never PUT profile changes from
   form editing. The APP-01 `/forms/demo` page is a placeholder. The portal links
   there with synthetic labeling; helper-level copy separation is tested, but
   the connected browser prefill journey is pending its separate delivery.
5. The shared web test script currently selects forms tests only. Proposed owner
   change: also select `components/portal/*.test.ts`; no manifest edit made here.
   Python's existing discovery already includes `tests/portal`.

## Proposed storage and security boundaries

`migrations/001_profile.proposed.sql` is review-only. Proposed names
`hoso_portal` and `hoso_portal_runtime` need the scaffold owner's agreement and
must live in a database isolated from forms development. No live/shared database,
Compose project, role or migration was created. The sample Compose provisioning
owner is unsuitable as the runtime login.

The proposal gives a separate nonprivileged login inherited runtime grants,
enables/forces RLS and prevents owner/profile-ID updates. Runtime checks reject
superuser/BYPASSRLS, role/database administration, table/schema owner powers,
unsafe predefined-role memberships, schema creation and excess mutation grants.
The SQLAlchemy provider uses the verified subject in transaction-local context
on the same connection as the queries. Context clears on commit/rollback; RLS
is additional enforcement of a trusted server assertion, not JWT verification.

An immutable-to-runtime `identity_namespace` row binds the database to the
agreed configured issuer. Provisioning must insert that issuer using a bound
parameter; an empty or mismatched row fails closed. Merely editing this marker
is NOT a tenant migration: account/subject reassignment needs an explicitly
reviewed identity migration. No independent `(issuer, subject)` account table.

The PostgreSQL provider requires `sslmode=verify-full`, TLS >=1.2, bounded
connection/lock/statement timeouts, parameter-hidden SQL and no query logging.
No plaintext local fallback is provided. No network TLS handshake has been
verified here. Database/disk/backup encryption, key lifecycle, retention, deletion
and immediate token revocation remain operational design and verification inputs.
Stored legal profile fields remain PII; neither the opaque profile ID nor RLS
anonymizes them. Do not use real PII in this development slice.

One shared development Clerk instance, issuer, authorized parties, optional
audience and identity transport remain to be confirmed with the scaffold owner
and Son. Existing transport is server-obtained Clerk Bearer token -> API verifier;
this workstream does not create another instance, copy keys or change ignored
local environments. Existing portal configuration was checked without displaying
secrets: origin3001/upstream8001 matched, Clerk key pair absent. Live keys do not
block independent code or synthetic tests; live login and revocation proof wait
for the agreed configuration.

## Observed checks and limitations

Run from `api/` with its existing virtual environment:

```text
python -m pytest -q
python scripts/export_profile_contract.py --check
```

Observed: 90 tests pass (28 new portal checks); generated profile contract matches.
One existing Starlette/httpx deprecation warning remains; no dependency changed.
Repository tests run actual repository SQL against disposable SQLite, including
two concurrent creators/updaters and A/B predicates. The test-only API composition
uses the real Clerk verifier with locally signed synthetic tokens. It is not the
production route wiring; a separate check confirms the real baseline remains501.

Run from `web/` using the installed Node tooling:

```text
node node_modules/tsx/dist/cli.mjs --test lib/forms/*.test.ts components/portal/*.test.ts
node node_modules/next/dist/bin/next build --webpack
```

Observed: 30 frontend tests pass (14 portal +16 existing); production build and
TypeScript pass. Tests cover status/error handling, no implicit save, stale
responses, logout reset, account transitions, page-cache lifecycle clearing and
form-copy separation. The editor clears on pagehide and rechecks the API after a
persisted pageshow. These synthetic event checks do not prove real browser bfcache
behavior, an authenticated browser session, mobile rendering or live logout.

Local preview is running on `http://127.0.0.1:3001/portal` using the existing
ignored configuration. `node components/portal/http-smoke.mjs` from `web/`
passes two actual HTTP checks: `/portal` returns200 with an explicit login-unavailable
state, and `/api/profile` returns503 `AUTH_UNAVAILABLE`; both include `no-store`.
This exercises only the unconfigured path, without any authentication bypass.

Optional PostgreSQL-engine check from `api/`:

```text
# Set AUTH01_PGLITE_MODULE to an installed @electric-sql/pglite/dist/index.js.
# Set AUTH01_PYTHON only if the API .venv Python is at a different path.
node --test --test-concurrency=1 tests/portal/postgres-policy.test.mjs
```

Observed: 12 pass using existing PGlite0.3.16 from the preserved draft's installed
test dependency, read-only. The script imports the actual Python repository SQL
and guard statements, applies the proposed DDL only to a disposable in-memory
engine and uses an isolated synthetic login with inherited runtime membership.
It checks both A/B directions, direct RLS denials, revisions, absent context,
commit/rollback cleanup and elevated-role rejection. No shared manifest changed;
the owner must choose a maintained integration-test dependency or isolated real
PostgreSQL test environment before making this a portable CI check.

PGlite evidence does not establish SQLAlchemy/psycopg wire integration, PostgreSQL
multi-connection races, production routes, TLS, encrypted storage, live Clerk or
two real accounts. No session/document ownership or Son authorization tests are
claimed. No consumer commit is named until it actually exists; a subsequent
evidence update can reference it without inventing its own commit hash.

## Next handoff

Scaffold owner: review schema/role proposal and handler injection, assign the
single shared-file writer, accept error codes/test-command integration and deliver
an exact integration SHA. FORM-02 owner: deliver the form-prefill consumer at its
own exact SHA. Portal then retests production routes and A/B storage against those
deliveries; record producer/consumer SHAs before claiming tested compatibility.
Manager consolidates Kim's status. Son/scaffold agree live Clerk and revocation
behavior; sessions/documents and consent remain separate coordinated interfaces.
Document lookup/RAG/search or procedure-contract questions go to Vincent; voice,
conversation and identity-tool questions go to Son. The exact APP-01 baseline and
AUTH-01 scope remain unchanged by the documentation-only ownership correction.

Design references: [PostgreSQL INSERT](https://www.postgresql.org/docs/current/sql-insert.html),
[row policies](https://www.postgresql.org/docs/current/sql-createpolicy.html),
[predefined roles](https://www.postgresql.org/docs/16/predefined-roles.html),
[libpq TLS](https://www.postgresql.org/docs/current/libpq-connect.html),
[Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
