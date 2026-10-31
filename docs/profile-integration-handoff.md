# APP-01 profile integration handoff

## Current consumer acceptance - 31 October 2026

This section supersedes the historical integration evidence below. The earlier
501-test failure and three provider-review findings are resolved by the exact
portal adaptation consumed here. Real PostgreSQL 16/TLS and live Clerk acceptance
remain outstanding; this is not a complete AUTH-01 or browser-flow claim.

| Reference | Exact SHA |
| --- | --- |
| Shared integration producer | `9cacda7320b5d18975a0bc2b62410eb74e45210f` |
| Portal hardening consumed unchanged | `584e1ee9adbb5fd1f0a845c1357e204833202d6f` |
| Portal handoff consumed unchanged | `def58b7d04667d1865e281391dc25ef1723aa0a2` |

The adaptation is a direct child of the shared producer. Both commits were consumed
with `git cherry-pick --ff` on `codex/kim/app-01-profile-integration`, preserving
producer SHAs; no branch merge or edit to another active worktree occurred. The
public cleanup implementation from `812d9e850703482eddfbc0bfbecd8ff0b42e5191`
and shared lifecycle remain unchanged. Read-only review found no additional blocker
to this scoped consumer acceptance.

Acknowledgment: **tested compatible for the registered API/lifespan interface with
synthetic signed identities and isolated storage fixtures**. The root consumer
reran the checks below on its own integration worktree; these are fresh results,
not only the portal owner's reported counts.

| Check | Observed result / boundary |
| --- | --- |
| Full API suite | **147 passed**, no skips/xfail/suppression; one existing Starlette/httpx deprecation warning |
| Generated profile contract | Matches the API model; `app.v1` and all six fields unchanged |
| Disposable SQL policy suite | **54 passed**, no skips; PGlite reports PostgreSQL **17.5**, not real PostgreSQL 16/psycopg/TLS |
| Scope preservation | No diff to shared auth/routes/lifespan/public cleanup, frontend, root manifest or lock from `9cacda7` |
| Existing forms worktree | `feature/kim-form` remains clean at `d00efb1d95557cb1d74dc61dc66638f4f3455f9b` |

Reproduced from the isolated checkout's `api/`, using its own installed virtualenv:

```powershell
$testBase = Join-Path $env:TEMP ('app01-hardened-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -q --tb=short --basetemp $testBase
.\.venv\Scripts\python.exe scripts/export_profile_contract.py --check
$env:AUTH01_PYTHON = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$env:AUTH01_PGLITE_MODULE = (Resolve-Path '..\..\kim-portal\apps\portal\node_modules\@electric-sql\pglite\dist\index.js').Path
node --test --test-concurrency=1 tests/portal/postgres-policy.test.mjs
```

The existing PGlite dependency was read from the preserved draft's installed files;
no dependency was installed, secret copied or manifest edited. API tests use locally
signed synthetic JWTs and disposable SQLite fixtures where storage is needed.
PGlite exercises the actual repository/guard SQL. Connection-option checks intercept
psycopg before a socket is opened. These are separate evidence boundaries.

### Real PostgreSQL 16/TLS prerequisite

The isolated test plan is ready in [profile-storage-test-plan.md](profile-storage-test-plan.md).
The current host does not yet provide a reachable PostgreSQL 16 test runtime. No
native `postgres`, `pg_ctl`, `initdb` or `psql` was found on PATH or standard Windows
PostgreSQL installation paths. Per-user Docker CLI 29.8.0 exists outside PATH; its
local `desktop-linux` daemon is unreachable. The only listed WSL distro is
`docker-desktop`, stopped (WSL2). Docker/WSL was not started because
starting a shared engine can also restart unrelated containers.

Prerequisite: make an isolated local container engine available, or provide local
PostgreSQL 16 server binaries. For the container route, confirm an available PG16
image after the engine is running; image availability was not inferred from CLI
presence. Then prepare a dedicated project/volume, loopback-only port, test CA/server
certificate, separate provisioner/runtime login and fixed synthetic issuer according
to the plan. OpenSSL 3.5.9 is available through Git. Port 55432 was free when inspected;
recheck immediately before startup. Do not use the existing plaintext Compose setup
or weaken verify-full/GSS/TLS policy. No database, role, schema or TLS handshake was
created by this acceptance step.

### Next owner handoff

The frontend owner can consume the same app.v1 seam for Login -> personal workspace/
chatbot -> search/documents/profile tabs, while integrating FORM-02 as assigned.
This backend task supplies no document/procedure/search service or UI mock; those
real interfaces remain Vincent-owned, and UI-only mocks belong to the frontend owner.
Shared layout/dependency/test-command changes still require frontend coordination.

Next backend acceptance is real PostgreSQL 16/psycopg/TLS, followed by live Clerk
and the combined account-profile -> editable form copy -> synthetic preview/PDF
browser journey. Backend fixes remain with the portal owner. No frontend/build
rerun is claimed for this backend-only consumption; prior frontend results below
remain tied to the earlier integration. No push, deployment, shared/live migration,
team-status edit or cross-chat reply was performed.

## Historical integration evidence at 9cacda7 (preserved)

Owner: Kim shared backend/scaffold. Date: 2026-10-31 (Asia/Saigon).
Status: shared wiring implemented; portal adaptation and real-storage acceptance
remain pending. This is not a complete AUTH-01 or browser compatibility claim.
The local manager remains the sole writer of `docs/team/status/kim.md`.

## Exact inputs and preserved work

- APP-01 baseline: `dc0ea22265df27210d6375f1bb1a3e6d118d839b`.
- Portal implementation: `56ba98f244fa0533c2e000dc7683a47b946e8798`.
- Portal evidence / worktree starting point: `82e61585dd97f599f5dce506cbd6dfe3e3464223`.
- Public cleanup consumed unchanged: `812d9e850703482eddfbc0bfbecd8ff0b42e5191`.
  Its parent is the exact starting point; `git cherry-pick --ff` retained this
  producer SHA. No branch merge or source-worktree edit was performed.
- Cleanup handoff read separately: `c4cba561c8d3e1c11a5736219c0c8a97db712a3c`.
- Integration branch: `codex/kim/app-01-profile-integration`.
- Isolated worktree: `.worktrees/kim-profile-integration`.
- Preserved FORM-02 UI: `9fd812891bce0a0f421871be76b6b2f40d6f4f30`;
  forms evidence: `d00efb1d95557cb1d74dc61dc66638f4f3455f9b` on
  `feature/kim-form`. FORM-02 is not combined into this branch.

Kim's designated frontend workstream now owns pages, components, layout, styles,
branding and account/form UI. This integration changes none of those paths.
It supplies the existing same-origin profile contract as the frontend seam.
Son owns voice, sessions and server-side tool authorization. Vincent owns document
retrieval/RAG, sources and the procedure-data contract. No parallel retrieval is added.

## Shared changes

- `api/hoso_api/profile.py`: existing GET/PUT receive `Request` and `CurrentUser`,
  and call portal handlers through local imports. Response models, generated types,
  auth dependency and private-response middleware are preserved.
- `api/hoso_api/main.py`: lifespan builds the portal service lazily, exposes it
  through app state, clears the reference and invokes public cleanup at shutdown.
  An injected fixture service is caller-owned; no private resource traversal.
- `api/tests/test_profile.py`: absent storage is now a truthful503 instead of501.
- `api/tests/test_profile_integration.py`: actual registered routes, real local JWT
  verification, real service/repository SQL and isolated synthetic SQLite fixtures.
- `api/tests/test_profile_lifespan.py`: allocation timing, ownership, unavailable
  configuration, failure sanitization, shutdown and real-factory cleanup probe.
- `api/README.md`, `docs/application-contract.md`, `docs/shared-scaffold.md`,
  this handoff and `docs/profile-storage-test-plan.md`: behavior and evidence limits.

Accepted errors use `detail: {code}`:404 `PROFILE_NOT_FOUND`,409
`PROFILE_REVISION_CONFLICT`,503 `PROFILE_UNAVAILABLE`. GET has no creation effect.
PUT0 creates when absent; positive revisions atomically compare/update only the
verified subject. Edits to a copied form and preview requests do not save the profile.
Missing/invalid storage does not select a fallback or downgrade TLS. `/health` is
process health only. No schema is created by startup.

## Executed verification

Run from `api/` using this worktree's independent `.venv`:

```powershell
# Use a fresh task-owned temp path to avoid shared Windows pytest temp ownership.
$testBase = Join-Path $env:TEMP ('app01-pytest-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -q --tb=short --basetemp $testBase
.\.venv\Scripts\python.exe scripts/export_profile_contract.py --check
```

Observed on the shared wiring plus cleanup commit: **140 passed, 1 failed**.
The sole failure is portal-owned
`tests/portal/test_handlers.py::test_production_baseline_is_still_501` (line72):
it expects501 where the integrated unconfigured service correctly returns503.
This failure was not suppressed, marked xfail or edited in the portal owner's paths.
An earlier full run hit Windows shared pytest-temp permissions; a fresh isolated
`--basetemp` resolved those setup errors. One upstream Starlette/httpx deprecation
warning remains. The generated profile contract check passes.

The new registered-route subset passed **37/37**: absent/invalid auth on GET/PUT,
A/B predicates and malicious browser IDs, missing404, create0, updates, stale409,
two simultaneous creates/updates with one winner, sanitized503 and rollback,
private headers, null replacement and explicit save versus form-copy/preview.
Shared and portal lifecycle checks passed **14/14**, including the real factory
with an offline engine probe. These counts are subsets, not additional full-suite
passes. No production router or auth dependency was replaced in route tests.

Frontend checks: all **30 existing tests** passed, and `pnpm typecheck` passed.
The test selection is:

```powershell
# From web/; no dependency or UI change is needed.
pnpm exec tsx --test lib/forms/*.test.ts components/portal/*.test.ts
pnpm typecheck
```

The proposed shared `web/package.json` test command is
`tsx --test lib/forms/*.test.ts components/portal/*.test.ts`. It was tested as a
local draft, then restored to the baseline command to respect the new frontend
ownership instruction. Coordinate that one-line manifest change with the designated
frontend owner before committing it. No manifest/lock/dependency change is delivered
by this backend integration.

## Concrete portal adaptation

1. On the portal owner's branch, replace/rename the old production501 assertion
   in `api/tests/portal/test_handlers.py` with a503 `PROFILE_UNAVAILABLE` expectation
   for absent storage, checking `no-store`; run it against this integration's exact
   SHA. Its test-only replacement-router tests remain helper evidence, while the new
   shared suite covers registered production routes. Keep these evidence types distinct.
2. Harden `portal/postgres.py` for marker mutation grants, reachable custom-role
   mutation privileges and forced TLS when GSSAPI is available. The exact findings,
   official references and negative cases are in `profile-storage-test-plan.md`.
   No provider-owned security code was rewritten by this integration.
3. Deliver exact owner commits, then rerun the full suite and isolated PostgreSQL
   wire/TLS acceptance. Do not treat SQLite or previous PGlite passes as that proof.

## Runtime and remaining acceptance

Dependencies were installed independently from caches:39 Python packages,62 pnpm
packages; frozen offline installs, no secrets copied. No `.env` was configured here.
API8002 and web3002 were free when inspected, but no server was started/reserved.
Proposed database port55432 must be checked immediately before any isolated setup.
Existing forms/portal runtimes and worktrees were not stopped or edited.

The current Compose service lacks the TLS required by the provider. An isolated
PostgreSQL16 instance with test CA, separate provisioner/runtime login and a fixed
synthetic issuer is only a plan. No shared/live database, role, migration or TLS
handshake was created or tested. Schema names `hoso_portal` / `hoso_portal_runtime`
are acceptable isolated-test candidates, not authorization for a shared deployment.

Still unverified: real PostgreSQL/psycopg/TLS/RLS, live Clerk login/two real accounts,
immediate revocation, combined browser account-to-form flow, Son authorization,
Vincent retrieval consumers and an approved official CT01. The frontend owner
combines its UI and FORM-02 reference after the shared and portal adaptations;
record both exact commits before claiming tested compatibility. Nothing pushed,
published, deployed or merged; manager consolidates status separately.
