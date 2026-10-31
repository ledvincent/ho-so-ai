# INTEGRATION-01 — first demo assembly handoff

Owner: Son, for this preparation branch; not a team-wide coordinator appointment.
Branch: `codex/son/integration-01-demo-assembly`.
State: preparation ready for review; applications are not yet combined or merged.
Human request: publish each member's scoped delivery on its own branch, then use
a separate integration branch for the first demo. Main merges stay human-controlled.

## Published inputs

| Owner / task | Fetchable branch | Exact input |
| --- | --- | --- |
| Vincent / procedure foundation | `codex/procedure-foundation` | `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4` |
| Kim / app.v1 backend | `codex/kim/app-01-profile-integration` | `ae77fa8bd47d590a53d26690b687bcad80692a9b` |
| Son / VOICE-01 | `codex/son/voice-01-browser-conversation` | `cad8198107ce7a38269834bf0c73522dad0348ba`; latest functional code `346c013ffea49ff15cc529672bdff446a59be0f5` |
| Son / ACCESS-01 | `codex/son/access-01-tool-authorization` | See the exact published SHA in `integration-demo-01.json` |

These are delivery candidates, not proof of a working combined app. Read each
owner's authoritative contracts/handoffs. Do not copy a second schema or retrieval
implementation. A status-only branch does not substitute for component source.

## Publication rule for every member

Commit and push only the task's explicit paths on its task branch after staged
review. Keep .env, credentials, private data, caches and local prototypes out.
Use `<type>(<scope>): <English action>` and body `Task: <ID>`.
Each handoff supplies owner/task, branch/exact SHA, allowed paths, contract/version,
inputs/outputs/errors, startup and configuration names (no secrets), test commands,
observed results/limits, missing dependencies and next owner. The component may
be incomplete if the missing behavior is explicit and unsafe paths remain gated.

## Messages for Kim and Vincent — repository handoff, not direct chat delivery

Their implementation chats are not accessible on Son's host. This committed
handoff publishes the requests; no direct-message acknowledgement is claimed.
Kim's pause for her preview review is respected; this is not a restart command.

**Kim:** Son's voice and access branches above are now fetchable. Backend app.v1
is received. When your review permits, publish the existing bounded NA5 frontend
branch with its exact UI/backend SHAs, startup, mock/live boundaries and tests.
Keep the one designated frontend owner. Provide the existing Clerk instance's
non-secret verification/origin/transport agreement, and agree the authenticated
approval/refusal/revocation interface with Son before personal tools are enabled.
Do not publish configured credentials. Please acknowledge the exact Son inputs
as received / adaptation required / tested compatible / blocked.

**Vincent:** Your published foundation is received. Preserve its current contract
and provide reproducible empty-clone data initialization or a documented safe
fixture path, startup/configuration names and actual checks. A fresh migration
does not contain your local data. Confirm the profile/context/baseline reference
that Son's voice and Kim's report must preserve for the same reviewed checklist.
Embeddings/calibration and source/form approval remain explicit gates. Please
acknowledge the exact Son consumer delivery and coordinate shared config with Kim.

## Concrete merge obstacles

Read-only calculation executed:

```text
git merge-tree --write-tree origin/codex/procedure-foundation origin/codex/kim/app-01-profile-integration
```

Git reported four content conflicts: `.env.example`, `.gitignore`, `README.md`,
`compose.yaml`. The command did not change a checkout, resolve them or merge branches.
Vincent's branch starts from the early repository baseline; do not blindly pick
one entire side or assume both APIs/databases can use the same port or schema.

| Shared path / seam | Required resolution owner and acceptance |
| --- | --- |
| `.env.example` | Kim + Vincent agree service-scoped variable names, auth/storage settings and secret-free examples; Son consumes them. Preserve both services' required settings. |
| `compose.yaml` | Kim + Vincent agree service names, ports, volumes and database roles. Do not start shared engines or apply live migrations as part of conflict resolution. |
| `.gitignore` | Preserve the union of safe exclusions for all components, without hiding deliverable source/tests. |
| `README.md` | Publish one startup map that identifies each component and separates synthetic demo from real identity/data readiness. |
| `api/` and dependencies | Vincent owns `api/*.py` retrieval; Kim owns `api/hoso_api/` and its package environment. Keep the two dependency manifests/environments explicit until owners agree composition. |
| Son session/consent | Reuse existing voice lifecycle and Kim's verifier/profile store. ACCESS core still needs canonical-session hooks and authenticated consent transport; no second identity/conversation service. |

One writer must own each shared-file resolution after the affected owners agree.
This preparation does not assign their shared configuration to a competing agent.
Existing local servers (including Son's voice/fixture ports 8001/8002) stay intact.

## Assembly and acceptance order

1. Fetch the exact component refs above; do not merge this documentation branch
   merely to read it. The JSON manifest pins the reviewed inputs and verification.
2. Kim reviews/publishes NA5 UI; Kim/Vincent agree the four shared-file resolutions
   and runtime/data map. Record the chosen owner and consumer adaptations here.
3. Bring agreed changes into the isolated integration branch for human review;
   never push directly to main. Preserve all member status/decisions on resolution.
4. Verify Vincent schema/context/assistant and Kim frontend/profile/form separately,
   then connect Son's existing assistant consumer. Default to explicit `1.001146`
   until retrieval readiness is established. Never parse prose as a validated form patch.
5. Bind voice lifecycle, verified Clerk identity and explicit app consent before
   any personal tool. Agree expiry/logout/reset/hangup and revocation semantics.
6. Reproduce the mobile journey and negative cases with exact producer/consumer
   SHAs: no consent, wrong account, expired/replayed decision, revision conflict,
   unavailable profile/retrieval and consistent reviewed checklist/version.

Current bounded first demo: provincial foreign-national stay extension `1.001146`
and NA5. Official form/export remains gated by exact human-reviewed source/PDF/map
hashes. Demo admin is synthetic, not Clerk or permission to call personal APIs.
If live identity or reviewed data is unavailable, show and label the synthetic
path explicitly instead of claiming a secured real-person/legal end-to-end flow.

## Son publication checks reproduced by manager

- Voice: 56 offline Python tests passed at the pinned branch; no paid provider
  call made for publication. The earlier live tool pilot remains reported evidence.
- ACCESS core: 24 synthetic unit tests passed.
- ACCESS app.v1 consumer: 28 contract tests passed against the pinned Kim source,
  actual models/verifier and registered API routes with synthetic JWTs and SQLite.
  Producer `ae77fa8...`; exact consumer commit is pinned in the manifest.
- These checks do not prove live Clerk/PostgreSQL, canonical voice consent,
  microphone behavior or combined voice-to-report correctness. Existing Starlette/
  httpx deprecation warnings remain visible.

No application merge, backend deployment, migration, source/form approval or
monitoring is performed by this preparation branch. Human review is still required.
