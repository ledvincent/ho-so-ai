# Shared application scaffold

APP-01 establishes the application seams for the stack Kim confirmed in this chat:
Next.js with TypeScript and Tailwind, FastAPI/Pydantic, PostgreSQL, and Clerk.
This records Kim's application choice; Son interoperability is not yet verified.
Vincent still defines the procedure-data contract. No procedure schema or collector
is supplied by this scaffold.

The fetched team guidance is preserved. Kim explicitly keeps `feature/kim-form`.
The root workstream owns shared dependencies, configuration and application interfaces;
the separate Clerk portal starts from the exact shared commit before FORM-02 UI work.
See `team/portal-handoff.md`. Publication, merges and live authentication must be
reported separately from local code or tests.
The non-secret instance/origin/variable agreement is in `clerk-configuration.md`;
the actual Clerk instance and issuer remain unset.

## Layout and current seams

| Path | Purpose / limit |
| --- | --- |
| `web/` | One Next application, Clerk integration, same-origin API proxies and shared application types |
| `web/lib/contracts.ts` | `app.v1` profile and transient form request types |
| `api/hoso_api/auth.py` | Clerk Bearer-session verification using a configured local public key |
| `api/hoso_api/profile.py` | Nullable profile schema and authenticated portal-service handlers |
| `api/hoso_api/forms/` | Explicitly synthetic, feature-gated PNG/PDF renderer; no official template |
| `compose.yaml` | Optional local PostgreSQL provisioning; no schema or migration is applied |
| `docs/application-contract.md` | App-owned identity/profile/forms transport and error behavior |
| `docs/team/contracts.md` | Vincent's procedure-contract ownership, unchanged |

`GET /health` checks the API process only. It does not check Clerk, database readiness,
legal sources or integration. APP-01 now wires the portal service with lifecycle
cleanup; production-route tests use isolated synthetic repository fixtures. Real
PostgreSQL/TLS, live Clerk, conversation authorization and voice-to-report integration
remain separate verification tasks. See `profile-integration-handoff.md`.
Docker was unavailable in the scaffold setup environment; no database startup or
migration is established. No configured Clerk credential or live sign-in result is
included. FORM-02 supplies the polished form UI as a separate change from this baseline.

## Local setup

Prerequisites: Python 3.12+, uv, Node.js 22+, and the pnpm version in `package.json`.
The current Compose file lacks the TLS required by the portal provider; do not
point the application at its plaintext/provisioner configuration. Review
`profile-storage-test-plan.md` before preparing an isolated database. Each worktree
needs its own ignored local configuration and any installed dependencies.

From the repository root, install the web workspace and copy its blank configuration
only when a local file does not already exist:

```powershell
pnpm install
if (-not (Test-Path -LiteralPath 'web/.env.local')) {
    Copy-Item -LiteralPath 'web/.env.example' -Destination 'web/.env.local'
}
```

Configure Clerk through the local files/environment; keep configured keys out of Git
and logs. An unconfigured app shows a setup state rather than a fake signed-in account.
The server-only `HOSO_API_URL` points to FastAPI; it is not a browser credential.
Frontend authorized parties and backend issuer/key/origin settings must refer to the
same Clerk instance and the actual frontend origin/port.

In an API terminal:

```powershell
Set-Location api
uv sync --group dev
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
uv run --env-file .env uvicorn hoso_api.main:app --host 127.0.0.1 --port 8000 --reload
```

`uv sync` creates/manages the API virtual environment. FastAPI itself does not source
env files; `uv run --env-file .env` supplies those process values. The example's demo
flag explicitly enables fictional form rendering; the application setting defaults
to false. `CLERK_JWT_KEY` is the public verification PEM, with escaped newlines
supported; it is not the server API secret. See `api/README.md` for required identity
settings and the local-key rotation/revocation limits.

In a separate terminal at the repository root:

```powershell
pnpm dev
```

Use the frontend origin allowed in both configurations. If another worktree is running,
choose distinct ports and update those exact origins and `HOSO_API_URL` together.
Do not assume a worktree isolates runtime ports or database contents.

To prepare PostgreSQL later, copy the root `.env.example` to an ignored `.env` only
if absent and configure a local password. `docker compose up -d postgres` provisions
the database; it does not implement the profile repository. Give concurrent worktrees
distinct Compose project names, database/ports and volumes. The provisioning owner is
not the eventual restricted runtime role. AUTH-01 must coordinate that role and its
application migration before personal data is stored.

## Verification and evidence

From the root for the web; from `api/` for Python:

```powershell
pnpm typecheck
pnpm test
pnpm build
```

```powershell
uv run --env-file .env pytest
uv run python scripts/export_profile_contract.py --check
```

The Python tests use synthetic identities and generated local tokens, with external
requests blocked. The synthetic renderer tests produce actual PDFs/PNGs and check
Unicode, fit, baselines and review/version gates. Final combined checks and browser
QA are recorded by the implementing workstream after they run. A passing unit suite
does not establish Clerk sign-in, PostgreSQL ownership/RLS or the full team journey.
Visual review of a synthetic PDF does not approve an official CT01 edition or mapping.

The original prototype under `prototypes/forms/` remains separate historical work.
The new portal must extend the shared app and contract, not import the unpublished
Auth0 draft or create another application/package/schema.
