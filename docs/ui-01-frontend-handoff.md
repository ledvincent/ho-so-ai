# UI-01 intermediary review checkpoint

Status: paused at Kim's requested review checkpoint. No further integration,
provider setup, publication or polish is queued for automatic continuation.

## Try the local preview

- Entry: http://127.0.0.1:3014/demo/login
- Demo username: `admin`; demo password: `admin`.
- Successful entry opens `/demo/workspace`, the CT01 document-and-chat mock.
- Choose `Dùng mẫu`, answer a selected field in chat, or click a highlighted
  document region to correct the same draft. `Xem cả trang` expands the paper;
  the second page tab shows the original instructions.
- `Rà soát bản in` captures the current three values. Acknowledgment enables
  browser Print / Save as PDF. Actual native printing remains unverified here.
- `Đăng xuất demo` clears the session, draft, review snapshot and unsent answer.

The demo session exists only in React memory under `/demo/`. Refresh, page-cache
restoration or leaving that route layout ends it. It is a UI demonstration,
not an identity, authorization mechanism or saved profile. No cookie, token,
local/session storage, Clerk request or profile API request is created by login.
The existing `/sign-in`, `/workspace` and `/portal` retain real Clerk behavior.
The public `/demo/ct01` route remains an explicitly synthetic fixture preview.
Research and profile navigation outside `/demo/` leaves the demo session.

## Exact code and dependencies

- Branch: `codex/kim/ui-01-site-design-integration`, isolated local clone.
- Integration base: `9cacda7320b5d18975a0bc2b62410eb74e45210f`.
- FORM-02 producer `9fd812891bce0a0f421871be76b6b2f40d6f4f30` was consumed
  as `626ebc81fc2ee92c9b2a2f7504877fd1cdb54c59` (four UI files).
- Main UI checkpoint: `f666b633c70b3f65df3813efc42d3ddce58fc8be`.
- Demo login checkpoint: `d41ceaa970c7d9019bc04443649be923567efe23`.
- Manager protocol read separately: `17900c3234add2a8c81c323e10a20d44dde88f1e`.
- Site design/brand source: `9905bc008f0f373eed9ba2cb8e7c3aa12f0ce6b9`.

The following exact dependency commits had already been reconciled before the
pause instruction arrived. They were cherry-picked cleanly into this branch;
there was no shared/main merge or push:

| Producer | Local consumer | Scope |
| --- | --- | --- |
| `584e1ee9adbb5fd1f0a845c1357e204833202d6f` | `7c6b96904bf76ddc695230109c476fe27fe966c9` | Profile storage guards and tests |
| `def58b7d04667d1865e281391dc25ef1723aa0a2` | `aeac1d55f5172e7b5c56f0b88de1e87075df060e` | Producer handoff evidence |
| `b07e28e74b4b9174979b7922ad3576d0562c778a` | `7437b00a045c1d8ab473ae4c030f27ddd4ed6310` | Scaffold acceptance evidence |

The producer reported 147 API and 54 PGlite checks passing. UI-01 did not rerun
those backend suites. Real PostgreSQL, Clerk and TLS acceptance remain pending.
The optional API preview process was started before these dependency picks;
it is not evidence of the new storage guards running against a live database.

## Changed behavior and scope

- Folded-H brand, burgundy/jade palette, Vietnamese shell, landing and account
  states reuse the existing Next app. No new app, manifest or dependency.
- Compact desktop document-left/chat-right workspace. Mobile shows the active
  document region above chat with the composer pinned to the bottom.
- Both six-field synthetic forms and the CT01 fixture use one canonical draft
  per view. Manual correction and deterministic chat apply to that same state.
- Profile save remains explicit. Form prefill is GET/copy only, through the
  existing validated boundary. The generated six-field app.v1 schema is intact.
- Session/account transitions, 401, pagehide and restored pageshow clear old
  draft content. Generation/revision guards reject late prefill/render replies.
- `/research` filters three local app-usage guides. It has no procedure retrieval,
  legal advice, source search or Vincent service integration.
- CT01 has only name, ISO birth date and a document-local 12-digit ID. IDs retain
  leading zeroes. Other fields and signatures are blank; no completeness or
  legal/form approval is implied. No production registry entry was changed.
- The real root ClerkProvider, server verification, proxies, contracts and
  profile save implementation are retained. Native Clerk components now use
  `/workspace` as their fallback destination; live Clerk was not exercised.

## CT01 fixture and print boundary

The unchanged blank PDF and both raster pages live under
`web/public/test-fixtures/ct01/`. The adjacent README records source URL,
coordinates, image hashes, limits and provenance.

- Blank PDF SHA-256:
  `ba72c63d656c2b3b0702faaef3f7a51c0356847631f16b47e7c354b8f5965444`.
- UI mapping SHA-256:
  `16fd8e3db04f4e1b7dec8eb7043f11a7e174b1cc642af7ce2005240ec6552fc5`.
- The print portal uses an acknowledged immutable snapshot and both pages,
  with a visible test stamp. Any edit invalidates acknowledgment and snapshot.
- Printing is browser Print / Save as PDF, not a direct download or fillable PDF.
  The in-app browser did not provide a usable native print dialog. Loaded images
  and compiled print CSS were inspected, but printed output is **unverified**.
- The separate `/forms/demo` endpoint still downloads its clearly synthetic
  PDF. CT01 never downloads that unrelated file.

## Verification observed in UI-01

- 41 scoped frontend tests passed: forms, profile controller/page lifecycle,
  six-field chat adapter and CT01 snapshot/validation model.
- `pnpm typecheck` passed before the demo addition; the final `pnpm build`
  completed its TypeScript check and production compilation with demo routes.
- Production preview at 3014: wrong demo password stayed on login with an error;
  `admin/admin` entered CT01; logout removed the editor; re-entry showed blank
  values and composer. Direct entry without a demo session showed the entry gate.
- CT01 browser checks: chat name/date/ID update overlays, ambiguous date asks for
  clarification, leading zeroes remain, and manual name correction appears in
  the review snapshot. Desktop/mobile layout inspected at 1440x1000 and 390x844.
- Real synthetic API preview and PDF download succeeded at `/forms/demo`.
  A subsequent manual edit disabled old acknowledgment and PDF download.
- Isolated harness rendering actual components: valid prefill; malformed 200,
  404 and 503 preserve edits; 401 clears values/composer; account/session changes
  clear; synthetic pagehide/pageshow clear; forced late replies after account
  change or edit are ignored. Loading removes the editor; sign-out resets to
  an empty manual-only form. These are mocked auth/fetch states, not live Clerk.
- Research filter showed zero matching guides, then restored all three on clear.
- Independent code review found a print CSS scope issue; it was fixed by requiring
  the CT01 print portal before hiding body children. Final production build passed.
- No real mobile keyboard, native print output or live identity/storage proof.

Commands used from `web/`:

```powershell
pnpm exec tsx --test lib/forms/*.test.ts components/portal/*.test.ts components/forms/demo-answer.test.ts components/ct01-demo/model.test.ts
pnpm typecheck
$env:NEXT_TELEMETRY_DISABLED='1'
pnpm build
pnpm start --port 3014
```

The test runner required scoped sandbox escalation because tsx could not start
under the restricted native runtime. No dependency versions or lockfiles changed.

## Local evidence and running preview

Screenshots are local ignored artifacts in `output/ui-01/`:

- `ct01-demo-desktop.jpg`: final desktop CT01 with demo session and fake values.
- `ct01-demo-mobile.jpg`: final mobile CT01 and pinned composer.
- `demo-login-desktop.jpg`: demo entry.
- `forms-compact-desktop.jpg`, `forms-compact-mobile.jpg`: six-field workspace.
- `auth-harness-evidence.txt`: observed synthetic guard scenarios.

Next production preview runs on loopback port 3014, using a build with Clerk
configuration absent. Optional synthetic form API runs on loopback 8014 with
demo forms enabled and no database/Clerk configuration. CT01/demo login need
neither backend nor real identity. The test-only harness used port 3015 and is
not a production route. No source deployment, migration, publication or push
was performed for UI-01. The original Sites logo comparison remains separate.

Next handoff: Kim reviews this intermediary mock. Wait for her direction.
