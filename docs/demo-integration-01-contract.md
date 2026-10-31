# DEMO-INTEGRATION-01 runtime and ownership contract

Producer pinned at `e16279119281e0d1897f0259ec8f9366e091c90d`.
Consumer base: `6ffec8e0270ff52bd27ceca9d4c4b57105c0cb54`.
Worktree: `work/kim-demo-integration`, branch `codex/kim/demo-integration-01-jury`.

## Ownership and integration order

- Backend owner: `web/lib/discovery/**`, `web/lib/server/discovery-proxy.ts`,
  discovery API route, auth policy/server wiring, `api/hoso_api/**` hosted boundary,
  and startup scripts. Frontend owner consumes these contracts and owns UI only.
- Producer transport/types are being upgraded to the pinned OpenAPI. The adapter
  retains opaque `retrieval_state`, choices, selected `procedure_code`, document
  metadata and draft/review gates. No new retrieval implementation or ingestion.
- Discovery routes remain authenticated under `/api/discovery`. Added setup,
  procedure document listing and document-specific actions follow Vincent's
  route suffixes. Server-owned URLs are rewritten to this same-origin prefix.
- Profile v1/v2 and existing pinned form/prefill contracts remain unchanged.
  A new document schema is not automatically compatible with existing prefill.

## Hosted demo contract

Dedicated ports: Next `3030`, application API `8030`, Vincent `8001`;
the launcher must fail on an occupied port. Manager owns the Quick Tunnel and
provides its exact HTTPS origin before startup. No existing listeners reused.

Both Next and application API require:

```dotenv
HOSO_AUTH_PROVIDER=local
HOSO_DEPLOYMENT_MODE=hosted-demo
HOSO_PUBLIC_ORIGIN=https://dans-timer-miami-davis.trycloudflare.com
HOSO_LOCAL_DEMO_SEED=false
```

Next additionally uses `HOSO_API_URL=http://127.0.0.1:8030` and
`HOSO_VINCENT_API_URL=http://127.0.0.1:8001`. API gets one absolute fresh persistent
SQLite path through `HOSO_LOCAL_DB_PATH`; it binds only `127.0.0.1`, with forwarded
headers disabled. HTTPS public origin does not permit remote API peers.
Cookies remain host-only, Secure, HttpOnly and SameSite=Lax. Mutations require
the exact configured Origin and JSON; every protected operation verifies the
session and profile owner. Hosted mode rejects weak demo seeding.

Two nondefault fictional jury accounts must be created through secure local
input/generated credentials, outside Git/logs/chat. The key is loaded into the
private API process memory from the already authorized ignored file only.
The external link depends on this computer and the tunnel staying running.

## Runtime dependencies and paid-call ledger

Observed missing: populated `handoff/procedure-db.dump`, `data/_store/`,
and a verified matching BGE-M3 weights/index runtime. `data/archive/raw/` is
present in the producer checkout; matching bundle contents remain unverified. Vincent is supplying
the data; do not rebuild ingestion/RAG. Source checkout alone cannot serve real
retrieval. `/assistant/setup` exposes catalog/generation/index readiness.

Shared budget: at most 6 short fictional live model requests across owners.
Used by this backend task: **0**. No retries or smoke calls until allocation is
coordinated. Unit/contract tests use explicit synthetic fixtures.

Implementation is checkpointed and paused at the user's request; this is not a claim
that hosting, data restore, retrieval, or the jury scenario has passed.
