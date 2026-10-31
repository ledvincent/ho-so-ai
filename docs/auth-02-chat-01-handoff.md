# AUTH-02 / CHAT-01 checkpoint handoff

Responsable : Kim. Etat : **En revue**, implementation paused after the bounded
checkpoint on 2026-10-31. No push, merge, deployment or shared database migration.

## Delivery and integration boundary

- Branch: `codex/kim/auth-02-local-chat`.
- Implementation commit: `21d3988780c4ecc596c80f49e6503b84f2c8c18c`.
- Base: `b07e28e74b4b9174979b7922ad3576d0562c778a`.
- Worktree: `C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint`.
- Author: `BobLemon68 <tessierkim3@gmail.com>` (Kim supplied).
- Original `feature/kim-form` checkout remains clean at
  `d00efb1d95557cb1d74dc61dc66638f4f3455f9b`.
- Published app.v1/Clerk delivery remains
  `ae77fa8bd47d590a53d26690b687bcad80692a9b`; this checkpoint does not rewrite it.
- HTTP consumer contract: [auth-02-chat-01-contract.md](auth-02-chat-01-contract.md).
- UI-02 delivery reported by the manager:
  `1cec3f08c11b42a9ff30ce1d4ae29d00943b67de`. Combined browser acceptance remains
  pending; this document does not certify that UI against the backend.

This adds explicit, disabled-by-default LOCAL login with salted password hashes,
opaque expiring/revocable sessions, database-backed throttling and owner-scoped
SQLite profiles through the existing app.v1 repository/service. Next validates
the server session for protected pages and APIs. Clerk remains the default.

The stateless assistant proposes validated values for one active NA5 field from
fictional user input; it cannot save the profile, generate signatures or approve
an official template. Schema: procedure `1.001146`, all 43 fields, fixed
`request_type=stay_extension`, conditional sponsor branches, draft review status.
Vincent source reference: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`,
`data/forms/NA5/workflow.json`. The copied source snapshot has SHA256
`50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3`.
`.gitattributes` preserves those exact bytes across checkout platforms; its
staged Git blob was verified against the expected hash before commit.

Son still owns voice, conversation sessions and tool authorization. LOCAL is a
proposed adapter boundary, not an accepted team-wide identity decision. Vincent
owns retrieval/procedure answers: `procedure_question` currently fails explicitly
with `RETRIEVAL_UNAVAILABLE`, without calling a competing retrieval service.
Manager owns `docs/team/status/kim.md`; this task did not edit that status file.

## Running resources and ownership

These are this backend chat's processes, left alive for the next review:

| Resource | Address / path | Ownership at handoff |
| --- | --- | --- |
| FastAPI | `http://127.0.0.1:8016` | Listener PID 42824; tool session 52984 |
| Next production server | `http://127.0.0.1:3016` | Listener PID 41348; tool session 95716 |
| Durable SQLite | `C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint\api\tmp\auth02-checkpoint.sqlite` | Dedicated ignored synthetic checkpoint database |

PIDs are observations, not stable identifiers; recheck the listener and command
before stopping anything. Ports 3014/8014 and the occupied 3015 were not stopped.
The backend baseline does not contain UI-02's LOCAL `/login` screen. Port 3016 is
the tested HTTP/BFF runtime, not a completed combined interactive product demo.

The two explicitly seeded synthetic accounts are `admin/admin` and
`reviewer/reviewer-demo`. Seeding is opt-in, loopback-only and idempotent: it does
not reset existing profiles or passwords. Do not use this seed for deployment.
Profile A and B currently contain synthetic acceptance data at revision 2.

## Restart commands

Use two PowerShell terminals, only after verifying the existing task listeners
have been stopped by their owner. Keep host spelling and origin/port identical.
Do not start duplicate servers against the same ports. The current environments
are already installed. For a new checkout, use the locked dependencies first:
`pnpm install --frozen-lockfile` from the root, then `uv sync --frozen --group dev`
from `api/` (Python >=3.12; pinned pnpm 11.25.0).

Terminal A:

```powershell
Set-Location 'C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint\api'
.\.venv\Scripts\python.exe scripts/run_local_checkpoint.py `
  --database 'C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint\api\tmp\auth02-checkpoint.sqlite' `
  --origin 'http://127.0.0.1:3016' --port 8016 --demo-seed `
  --key-file 'C:\Users\Kim\Documents\ChatGPT\Hackathon\.env.local'
```

The launcher reads only the authorized existing `OPENAI_API_KEY` into process
memory. It never copies the env file or prints the key; the browser receives no
API key. Access logs and trusted proxy headers are disabled. Default model is
`gpt-4o-mini`. For offline operation, omit `--key-file` and ensure
`OPENAI_API_KEY` is absent from the process environment.

Terminal B:

```powershell
Set-Location 'C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint'
$env:HOSO_AUTH_PROVIDER = 'local'
$env:HOSO_PUBLIC_ORIGIN = 'http://127.0.0.1:3016'
$env:HOSO_API_URL = 'http://127.0.0.1:8016'
$env:NEXT_TELEMETRY_DISABLED = '1'
pnpm --dir web build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
pnpm --dir web start --port 3016
```

These commands reproduce the backend baseline. To test UI-02, the integration
owner must first combine its exact delivery with the implementation commit in
an isolated checkout, then build that combined source. Coordinate origins/ports
with this API owner if changing the frontend address; its allowlist is exact.

## Observed verification

All verification below ran against this task's source and synthetic data.
Documentation and Git asset attributes were finalized afterward; the asset bytes
and application source were unchanged by that finalization.

| Check | Result and scope |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q --tb=short --basetemp <unique-work-temp>` from `api/` | 247 passed: baseline 147, chat 66, LOCAL auth 34. Two warnings: existing Starlette/httpx deprecation and pytest cache permissions. |
| `pnpm --dir web exec tsx --test lib/forms/*.test.ts components/portal/*.test.ts lib/local-auth-policy.test.ts` | 38 passed. |
| `pnpm --dir web typecheck` and final `pnpm --dir web build` | Passed, including TypeScript compilation. |
| `python scripts/export_profile_contract.py --check` from API env | Passed; generated app.v1 schema unchanged. |
| `python scripts/check_local_http.py --web-origin http://127.0.0.1:3016 --api-origin http://127.0.0.1:8016 --check-unavailable-retrieval` | 20 production HTTP checks passed: login/cookie secrecy, origin/body constraints, private routes including dotted paths, independent A/B profiles, revision conflicts, owner injection rejection, draft schema, unavailable retrieval and logout revocation. |
| Targeted HTTP after final build | Invalid UTF-8 login ->400; over-limit login ->413; private no-store headers verified. |
| `python scripts/check_live_assistant.py --web-origin http://127.0.0.1:3016 --allow-live` | Already executed once: exactly two successful model calls, initial fictional full name and correction; no retries; validated proposals, correlation, draft status and next question. |
| Persistence | HTTP checks saved revision-2 synthetic profiles; API process was stopped and restarted using the same file; subsequent live smoke asserted the exact saved profile/revision survived and was unchanged by both assistant calls. |
| Git review | Explicit staged paths, clean whitespace check, expected NA5 blob hash, no existing API credential in staged contents; env/database/generated outputs excluded. |

The full HTTP script intentionally requires absent profiles before its first run.
Do not rerun it on the retained database or reset/delete this evidence to make it
pass. Use a separate newly named synthetic database and coordinated isolated ports
if a future owner needs a fresh run.

**Live request budget: 2 of 3 used; 1 remains for UI-02's combined browser proof.**
Do not rerun the two-call smoke script under that remaining budget. No automatic
model requests on page load, initial empty-message guidance, retries or errors.

## Remaining acceptance and limits

The manager/UI owner should verify the combined browser flow: real login and
logout; direct private URLs; account A/B separation; explicit profile save;
manual/account-prefilled form editing; one bounded fictional assistant proposal;
late-response discard on edit/account switch; preview/export invalidation and
draft official-document gating. Existing `/demo` fixtures remain historical
fixtures; they are not proof of the primary authenticated product flow.

No combined authenticated browser journey, live Clerk, PostgreSQL RLS/TLS, Son
voice authorization, Vincent retrieval runtime or reviewed official PDF download
was validated by this checkpoint. UI ownership is unchanged; no page, component,
branding, stylesheet, package manifest or lockfile was modified here.

SQLite stores profile values without application-level encryption at rest. This
is synthetic local evidence, not production PII readiness. Deployment still needs
reviewed identity integration, real credential provisioning without demo seeds,
HTTPS, database access/encryption/backup/retention controls and relevant shared
authorization acceptance. Signup, password reset and MFA are outside this bounded
checkpoint. The next step is review and combined acceptance, not automatic rollout.
