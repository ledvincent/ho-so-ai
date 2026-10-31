# Kim — application integration checkpoint

Owner: Kim; consolidated by Kim's local manager.
Updated: 2026-10-31 12:43 Asia/Saigon (UTC+07:00); evidence snapshot.
Task: TEAM-05 — publish the APP-01, AUTH-01, FORM-02 and UI-01 integration checkpoint.
State: Local components and synthetic integration are in review; the first combined
UI mock is in progress. Live authentication/storage and team integration are not complete.

## What teammates can access

This checkpoint changes only `docs/team/status/kim.md` on
`codex/kim/team-05-integration-checkpoint`, based on live-verified main
`60cb3be26e928cbef71cb636b8662e3a6cde693f`. The English manager protocol remains
separate on `codex/kim/team-03-manager-protocol`, exact published commit
`17900c3234add2a8c81c323e10a20d44dde88f1e`, in
[PR #3](https://github.com/ledvincent/ho-so-ai/pull/3). That PR is not changed by
this checkpoint.

**The application commits below are verified locally, but application branches
have not been published by this workstream.** A SHA in this status does not make
its code available on GitHub. The application contracts and handoff paths below
refer to those local implementation commits, not this documentation branch.
The next application publication must provide accessible producer branches and
exact source commits before Son or Vincent can test them.

No application merge into main is claimed. The latest remote main observed by
the manager was `60cb3be26e928cbef71cb636b8662e3a6cde693f`; local remote refs and
unpublished work are not treated as current remote state. This checkpoint does
not edit Son's or Vincent's status or appoint a team-wide coordinator.

## Product direction and ownership

Kim's requested flow is **Login -> personal workspace with chatbot -> document
filling**, with manual-research, documents and profile tabs. On mobile the live
document preview sits above chat; the recommended wide-screen layout keeps the
document left and chat right. Chat answers and direct field corrections update
the same document draft. Highlight changes, clarify ambiguous answers, show
missing values, and require final review before export. Document edits must not
silently save changes to the user's profile.

- One designated frontend workstream owns all pages, components, layout, styling
  and branding. Sites supplies visual design; the working UI remains in the
  existing Next.js/Clerk application. Other Kim workstreams have stopped UI edits.
- Scaffold owns shared auth, profile route/lifespan wiring, generated contracts,
  server proxies and coordinated manifests/configuration.
- Portal owns profile repository/service/storage and scoped backend tests.
- Kim owns the user/profile backend and application/form/report integration.
  Vincent will supply document/procedure retrieval, search through RAG, sources
  and the authoritative procedure-data contract. UI-only mocks are explicitly
  synthetic and do not become a replacement production service or shared contract.
- Son owns the voice/conversation component and server-side tool authorization.
  The current mock chat does not establish Son integration or connected AI.

## Exact local deliveries

| Task / local branch | Code and evidence | Delivered scope |
| --- | --- | --- |
| APP-01 / `feature/kim-form` | Code `dc0ea22265df27210d6375f1bb1a3e6d118d839b` | Existing Next/FastAPI application, Clerk boundaries, server proxies, generated six-field `app.v1` profile contract and synthetic PDF seam. |
| FORM-02 / `feature/kim-form` | Code `9fd812891bce0a0f421871be76b6b2f40d6f4f30`; evidence `d00efb1d95557cb1d74dc61dc66638f4f3455f9b` | Manual form input, editable account-profile copy, review, preview and export invalidation. |
| AUTH-01 / `codex/kim/auth-01-clerk-portal` | Code `56ba98f244fa0533c2e000dc7683a47b946e8798`; evidence `82e61585dd97f599f5dce506cbd6dfe3e3464223` | Profile service/repository, owner checks, revision handling and PostgreSQL provider. Preserved UI is handed to the sole frontend owner. |
| AUTH-01 cleanup | Code `812d9e850703482eddfbc0bfbecd8ff0b42e5191`; evidence `c4cba561c8d3e1c11a5736219c0c8a97db712a3c` | Public `ProfileService.close()` lifecycle, consumed by shared integration. |
| APP-01 / `codex/kim/app-01-profile-integration` | Wiring `9cacda7320b5d18975a0bc2b62410eb74e45210f` | Actual profile routes and application lifespan use the portal service. |
| AUTH-01 / `codex/kim/auth-01-storage-hardening` | Code `584e1ee9adbb5fd1f0a845c1357e204833202d6f`; evidence `def58b7d04667d1865e281391dc25ef1723aa0a2` | Registered-route tests, issuer-marker and role/column privilege guards, trusted TLS/GSS connection policy. |
| APP-01 consumer acceptance | Evidence HEAD `b07e28e74b4b9174979b7922ad3576d0562c778a` on `codex/kim/app-01-profile-integration` | Consumed the hardening and handoff commits with their original SHAs and reran the integrated checks. |
| UI-01 / `codex/kim/ui-01-site-design-integration` | Base `9cacda7320b5d18975a0bc2b62410eb74e45210f`; FORM-02 import `626ebc81fc2ee92c9b2a2f7504877fd1cdb54c59`; design source `9905bc008f0f373eed9ba2cb8e7c3aa12f0ce6b9` | The responsive workspace, mock chat/research and visual integration are uncommitted at this snapshot. No final UI delivery SHA or combined acceptance is claimed. |

The code and handoff commits were read directly from isolated local branches.
No active implementation checkout was edited to prepare this status. The old
authentication prototype remains preserved locally and is not part of publication.

## Contracts and verification

The authoritative application reference is `docs/application-contract.md` at the
application commits, version `app.v1`; generated web profile types are in
`web/lib/profile.generated.ts`. The profile has six fields and uses
`expected_revision`. Same-origin Next proxies forward a server-obtained Clerk
token to the API; a browser-supplied owner/profile identifier is not the owner key.
GET does not create a profile. Creation uses revision 0; stale updates return 409,
missing profiles 404 and unavailable storage 503, with private/no-store behavior.
These are summaries of Kim's contract, not a replacement for it or Vincent's contract.

| Evidence | Result and limitation |
| --- | --- |
| `api/hoso_api/portal/HANDOFF.md` at `def58b7d...` | Portal owner reports 147 API tests, generated-contract match and 54 SQL/guard checks. |
| `docs/profile-integration-handoff.md` at `b07e28e...` | Scaffold consumer independently reran 147 API tests and 54 SQL/guard checks; all passed without skips/xfail/suppression. One existing Starlette/httpx deprecation warning remains. |
| SQL/guard engine | PGlite 0.3.16 reports PostgreSQL 17.5. These are disposable SQL/RLS/privilege tests, not PostgreSQL 16 wire/TLS tests. |
| API fixtures | Locally signed synthetic JWTs and disposable SQLite where storage is required; real registered routes/lifespan are exercised. Connection-policy tests intercept psycopg before a socket opens. |
| Earlier FORM-02 evidence at `d00efb1...` | Owner reports 62 API tests, 16 web tests, TypeScript/production build and 9 browser checks, including mobile, corrections and synthetic PDF. These results are historical component evidence, not a rerun of the new UI. |
| Manager verification | Read-only commit, scope and handoff review. The manager did not rerun the above application suites for this status publication. |

Reproduction commands are recorded in the exact handoffs: from `api/`, run the
owner's isolated Python environment with `-m pytest -q --tb=short --basetemp <fresh-test-dir>`,
then `scripts/export_profile_contract.py --check`; the disposable SQL suite is
`node --test --test-concurrency=1 tests/portal/postgres-policy.test.mjs` with the
documented dependency paths. No current UI URL is certified by this checkpoint;
the frontend owner must deliver a runnable mock and fresh browser evidence.

## Official blank form used only for testing

Kim requested a real online blank form as a UI test fixture. Research identified
CT01, **Tờ khai thay đổi thông tin cư trú**, edition 53/2025/TT-BCA dated 1 July 2025,
in [the official Gazette PDF](https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/7/45606/57795-1-2025981-98255-2021-tt-bca.pdf),
PDF pages 7–8. The blank form and instructions were extracted and visually checked;
there are no AcroForm fields, so overlays need filled-output layout validation.

- Source SHA256: `d7d587ff9a6a3bf1bb213e77f309f15a613c7eb17a63b69a79eb6c04bb70a098`.
- Two-page fixture SHA256: `ba72c63d656c2b3b0702faaef3f7a51c0356847631f16b47e7c354b8f5965444`.
- Research mapping SHA256: `8e15dbfcf082078182ce8d4f6aab55a7810e2bcf4bf25e93588f2f8c5e5b452a`.

Only synthetic answers may populate this demo. The research fixture is local and
is not yet a delivered UI asset. This is not production template approval, a
reviewed procedure record, a legal submission, or an activated official form in
the production registry. Preview and export must represent the same draft.

## Dependencies and acknowledgements

| Producer -> consumer | Exact references / acknowledgement | Next action |
| --- | --- | --- |
| APP-01 routes -> AUTH-01 adaptation | Producer `9cacda7320b5d18975a0bc2b62410eb74e45210f`; consumer `584e1ee9adbb5fd1f0a845c1357e204833202d6f`; **tested compatible** for registered API/lifespan with synthetic identities/storage only | Preserve the unchanged contract; verify real storage separately. |
| AUTH-01 hardening -> APP-01 integration | Producer `584e1ee9adbb5fd1f0a845c1357e204833202d6f`; consumer evidence `b07e28e74b4b9174979b7922ad3576d0562c778a`; **tested compatible** within the same synthetic boundary | Deliver the exact combined backend reference to the frontend owner. |
| APP-01/FORM-02/design -> UI-01 | Exact inputs listed above; **received; adaptation required** | Sole frontend owner finishes the mock, reconciles the hardened backend input and returns code SHA, screenshots and browser results. |
| Son's manager checkpoint -> Kim manager | Published `codex/son/team-04-manager-checkpoint`, `bad14859eebd9189d2df780b9fe1981e92a6fbd1`; **received** | Read status only. It acknowledges TEAM-03 and correct ownership; it is not published voice/access implementation or team coordinator appointment. |
| Son voice/access -> Kim application | No published implementation received for testing | Later provide exact producer branch/SHA, session/consent/tool boundaries and verification instructions. Son reports local voice code and authorization work; absence of publication is not inactivity. |
| Vincent retrieval/procedure contract -> Kim application | No exact implementation/contract delivery received for testing | Later provide authoritative path/version, producer SHA, reviewed example/provenance, lookup/errors and test instructions. Continue explicit UI mocks meanwhile. |

## Concrete prerequisites and next actions

1. Frontend owner: deliver the first visible integrated mock, desktop/mobile
   evidence, chat-to-field correction and matching preview/export behavior. Keep
   mocks clear and product UI under one writer. Kim's manager reviews the result.
2. Kim's manager: publish this status so teammates can see progress; prepare a
   separately reviewed application handoff with accessible code branches. Status
   publication alone does not unblock code consumption on another machine.
3. Real PostgreSQL acceptance needs an isolated PostgreSQL 16 runtime. Scaffold
   found no native server binaries; the Docker CLI exists but its local daemon
   is unreachable and the Docker WSL distro is stopped. No shared engine,
   database, schema or migration was started. Use the recorded TLS test plan
   without weakening `verify-full` or the runtime-role policy.
4. Live Clerk acceptance needs the agreed existing development instance and
   consistent issuer, authorized parties, optional audience and origins. Secrets
   belong in local configuration, never this status. Configuration names and the
   transport boundary are in `docs/clerk-configuration.md`. No real sign-in,
   account switch/revocation or two-account browser proof is claimed.
5. First verify Kim's actual frontend -> Clerk/session -> proxy -> real profile
   service/storage -> save/reload -> editable form copy -> preview/export journey.
   Check two-account isolation, owner injection, revision conflicts, failure and
   logout/stale-response handling, and no implicit profile save from document edits.
   Then integrate Son's voice/access and Vincent's retrieval using exact published
   interfaces and the same reviewed procedure version/checklist across components.

The UI mock milestone can proceed before real-provider acceptance. Neither the
visual Site, a clean Git calculation nor passing component tests proves the full
application or three-person integration. Human review still controls merges.
