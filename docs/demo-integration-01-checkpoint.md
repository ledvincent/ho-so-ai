# DEMO-INTEGRATION-01 — WIP publication checkpoint

Paused at Kim's request to publish current work before further implementation.
Branch: `codex/kim/demo-integration-01-jury`; base UI commit:
`6ffec8e0270ff52bd27ceca9d4c4b57105c0cb54`.
Producer contract pinned at `e16279119281e0d1897f0259ec8f9366e091c90d`.
No main merge. No live model calls used by this task (0 of the shared 6).

## Implemented in this checkpoint

- Explicit `HOSO_DEPLOYMENT_MODE=hosted-demo`, exact canonical public HTTPS origin,
  secure session-cookie policy, private loopback API boundary and weak-account
  refusal in both the runtime factory and launcher. Default local/Clerk behavior
  remains separately configured.
- Fresh jury account provisioning with random or hidden-input passwords, exclusive
  SQLite creation, owner-readable files and private parent directory. Credentials
  are never printed or committed.
- Private API and Next production launch scripts with dedicated port checks,
  API-only provider-key handling, no forwarded-client trust, owned child cleanup.
- Updated discovery transport for signed conversation state, choices, selected
  procedure, document cards, setup readiness and score/matched_by search. Chat
  timeout is 180 seconds; returned document URLs use protected same-origin paths.
- Generic document proxy actions with strict request/version bounds and owner,
  document, version and values bound preview-token hashes. Draft/review/download
  gates remain enforced by the producer; no legal approval is inferred.

## Verification completed

- API hosted/local auth, Clerk auth and PostgreSQL configuration: **122 passed**.
- TypeScript auth/request-origin policy: **15 passed**.
- Discovery handler: **42 passed**, including new generic routes, state envelope,
  hosted Origin checks and stale/cross-owner review-token rejection.
- Upstream transport existing regression suite: **24 passed** with updated wire
  fixtures. New generic upstream document methods lack dedicated tests at pause.
- Fresh private smoke account/database provisioning succeeded twice. No secrets
  printed; no model requests or public traffic used for this check.
- `pnpm typecheck` passed at checkpoint. No production build or actual hosted
  startup was completed here.

## Unfinished and not established

- Vincent's populated dump/store and matching embedding runtime are still needed;
  no ingestion/rebuild or data restore was performed by this task.
- New frontend consumers/UI changes are owned by the separate frontend branch and
  are not included here. This backend commit alone does not complete the journey.
- The new NA5 document template version is **not** accepted by the older profile
  prefill seam. Legacy schema/prefill/CHAT contracts remain unchanged and fail
  closed on the new version. Read the runtime report for the exact hash/diff evidence.
- No live retrieval, full form PDF render, external HTTPS authentication, cookie
  round-trip, two-account hosted scenario, or end-to-end jury acceptance passed.
- The launcher requires a production build and a fresh jury database. There is no
  production build in this checkout at pause. The launcher is source-reviewed and
  its provisioning CLI smoke-tested; its complete process lifecycle is unverified.
- Preview binding state is single-process/in-memory. Restart requires a new
  preview; this is appropriate only to the dedicated one-process demo.

## Launcher handoff for the manager

Use Python with the existing API dependencies. From this checkout:

```powershell
# Choose an absolute, NEW path inside this checkout's ignored .runtime directory.
python api/scripts/provision_jury_accounts.py --database <absolute-new-.runtime-jury.sqlite3> --credentials-file <absolute-new-.runtime-jury-credentials.json>
pnpm build
python scripts/run_hosted_demo.py --origin https://dans-timer-miami-davis.trycloudflare.com --database <same-absolute-jury.sqlite3> --key-file <already-authorized-ignored-env-file> --web-port 3030 --api-port 8030 --vincent-url http://127.0.0.1:8001 --pid-file <absolute-.runtime-pids.json>
```

Keep the launcher running, preferably as a hidden managed child. Only the manager's
separate Quick Tunnel targets Next 3030. No API tunnel. Verify protected routes
and cookie/owner/logout behavior before sharing the temporary laptop-dependent
URL. Read credentials only through the private local file; do not paste into Git,
logs or chat. Existing preview processes were not stopped or changed by this task.

All implementation subagents are paused. Resume only on a new user instruction.
