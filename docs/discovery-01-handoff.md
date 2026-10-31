# DISCOVERY-01 adapter handoff

Responsable : Kim. Etat : **En revue**, paused on 2026-10-31 after the bounded
backend delivery. No push, deployment, merge or database migration.

## Exact delivery

- Code commit: `d0b2caa0ca128cc470bf9413eff54bfbfd447265`.
- Branch: `codex/kim/discovery-01-vincent-adapter`.
- Worktree: `C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-discovery-adapter`.
- Base UI-02: `edb3c1cd4d41a5ac1ae8b0125e84c197862145a5`.
- Vincent producer audited read-only: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`.
- [Consumer contract](discovery-01-contract.md), final working-file SHA256:
  `a9c67a9a72c78b0906fffbf39021e065d54c576a3f16767d827a6040d3a504c6`.
- Author: `BobLemon68 <tessierkim3@gmail.com>`.

Only seven files comprise the code delivery: the contract, the discovery API
route, its server composition wrapper, route policy and upstream adapter, and
their two fixture test files. No existing views/components, auth provider,
field-assist routes, dependencies, manifests, database code or team status changed.

General procedure chat now has a thin authenticated consumer route:
`POST /api/discovery/chat` forwards Vincent's exact bounded
`message/procedure_code/history` request. It returns his validated
`status/answer/citations/model` response without interpreting prose as routing.
`POST /api/discovery/search` provides structured candidates. Confirmation remains
explicit in the UI; subsequent chat retains the confirmed code. No default visa
procedure, new retrieval pipeline, model SDK or conversation store was added.

Procedure/profile/original/analysis/schema routes verify the requested code,
snapshot/form associations, profile head identity and document hashes. Original
bytes are returned as protected attachments with a safe deterministic filename;
DOCX is not represented as an inline PDF. Unsupported workflows stay read-only.
The supported NA5 schema additionally requires procedure facts readiness and the
pinned form/mapping/version; draft state cannot unlock official downloads.

## Consumer configuration and integration

The sole frontend owner can consume the code commit on its new integration branch;
the UI-02 base and running preview must remain preserved. The existing server-side
session and `HOSO_PUBLIC_ORIGIN` / `HOSO_API_URL` configuration are reused. There is
no new authentication store and no cookie/Bearer credential forwarded to Vincent.

The only new configuration is server-only `HOSO_VINCENT_API_URL`. Supply Vincent's
confirmed producer origin (HTTPS or loopback HTTP, no credentials/query/fragment
or API path). Never use a browser-supplied URL or `NEXT_PUBLIC_` variable. It is
currently **unset**, deliberately returning503 `DISCOVERY_UNAVAILABLE`. No fixture
or synthesized answer is substituted. Build normally with `pnpm --dir web build`;
restart the integrating Next process after configuration changes.

Still needed from Vincent: actual reachable origin, loaded procedure/form data,
PostgreSQL/index readiness, search calibration and configured assistant runtime.
His search can call an embedding provider and his chat can call a model. Do not
use either as a healthcheck or run them under the exhausted prior smoke budget.
No live producer, embedding or model request was made by this task.

The UI owner still implements general chat first, explicit candidate confirmation,
matched document selection and supported-schema entry. Render answer/source text
as text, safe citation links separately, and clear/discard stale responses on
selection/account changes. `/assistant/chat` has no selected-procedure/form/version
output. `field_schema_ref` is metadata, not an HTTP endpoint. Full route, error
and limit details are in the contract; no new canonical procedure schema is claimed.

## Verification actually executed

- **61 new synthetic tests passed**: 37 route-policy tests and24 adapter tests.
  Covered session failure, origin/query/body/role limits, found/multiple/not-found,
  exact producer chat statuses, safe URLs, no credential forwarding, missing
  configuration, source errors, hash/association/head mismatch, bounded streaming,
  unsupported workflow, blocked readiness and pinned draft mapping.
- **62 existing frontend tests passed**, including profile isolation/save semantics,
  guided form response handling, stale revisions and draft export gates.
- Final **production build passed**, including TypeScript. The first build found
  a test-fixture union annotation error; it was corrected before the successful build.
- **11 real production HTTP checks passed** through a separate Next server and
  real LOCAL authentication API: signed-out protection; login; chat/search/procedure
 503 without producer configuration; hostile origin; invalid chat role; forbidden
  query parameter; logout and subsequent401. No saved profile was created.
- Explicit staged scope, whitespace check and credential-shaped string scan passed.

Offline test reproduction from the worktree root:

```powershell
pnpm --dir web exec tsx --test lib/forms/*.test.ts lib/local-auth-policy.test.ts lib/discovery/*.test.ts components/*/*.test.ts
pnpm --dir web build
```

The observed123 tests ran in two disjoint groups (100+23); the command above covers
their same file set. No API production code changed, so the prior247-test API suite
was not rerun or represented as new acceptance. Fixture checks establish consumer
behavior, not live producer compatibility, retrieval quality or legal correctness.

## Resource preservation and stop boundary

Observed preserved listeners: UI-02 `3018` PID41788 / API `8018` PID41832;
concurrent `3020` PID41452 / `8020` PID42868 were also left untouched. The UI-02
publication checkout remained clean at its exact base commit above.

Scratch validation used only `3032` (Next session37943) and `8032` (API session81720),
with a new ignored `api/tmp/discovery-http.sqlite` in this worktree. The scratch
API had no OpenAI key; Next had no Vincent URL. Both scratch processes were stopped
after HTTP acceptance. The synthetic database is ignored and retained; no existing
database was reset, copied or migrated. No new task server is left running.

Remaining acceptance: UI-03 integration and confirmed live Vincent runtime/data,
then a separately authorized end-to-end conversation -> search -> confirmation ->
matched document journey. LOCAL remains loopback-only; public hosting identity,
Son's voice/access integration, legal/form review and production PII readiness are
separate work. Manager alone writes Kim's status. Implementation is paused here.
