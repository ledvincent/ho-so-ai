# UI-01 intermediary review checkpoint — NA5

Status: paused for Kim's review. This supersedes the earlier CT01-first
checkpoint. No further integration, provider setup, publication or polish is
queued for automatic continuation.

## Try the local preview

- Entry: http://127.0.0.1:3014/demo/login
- Demo username: `admin`; demo password: `admin`.
- Successful entry opens `/demo/workspace`: **NA5**, procedure **1.001146**,
  Gia hạn tạm trú cho người nước ngoài (cấp tỉnh).
- Choose `Dùng mẫu` for Vincent's fictional example, answer the selected field
  in chat, or click a document region to correct the same draft. The name,
  birth date, passport and sponsor selectors are immediately available.
- `host_type` is exactly `organisation` or `family`; the appropriate conditional
  fields appear. `sponsor_kind=foreign_resident` adds residence-card fields.
- `Rà soát bản nháp NA5` captures normalized current values after validation.
  Editing invalidates the snapshot and acknowledgment. Final download remains
  locked because the template is `draft` and no backend review token exists.
- `Hỏi về thủ tục` returns a labeled mock `insufficient_context` response.
  Its answer/citations/status/model response cannot patch the draft.
- `/demo/research` filters the four exact delivered procedure codes. Only
  `1.001146` opens this NA5 flow. CT01 is a separate secondary test view.
- `Đăng xuất demo` clears the session, draft, review and unsent answer. Reload,
  leaving the demo layout or page-cache restoration also ends the session.
  Navigating from the workspace to another view discards the local draft.

The demo session exists solely in React memory under `/demo/`. It creates no
identity, token, cookie, persisted session, Clerk or profile API request. It
cannot authorize the real `/workspace` or `/portal`. Use fictional values only.
The original real-auth routes and profile-save boundary are retained.

## Exact implementation and producer contract

- Branch: `codex/kim/ui-01-site-design-integration`, isolated local clone.
- NA5 implementation: `a8dd757c9a80a4a466b1f0257c9a790891a4c6b7`.
- Producer: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`,
  `codex/procedure-foundation`; inspected in a separate read-only checkout.
- No whole-branch merge, shared/root configuration replacement or backend
  implementation was needed for this NA5 checkpoint.
- Exact catalog codes: `1.003326`, `1.001146`, `1.003342`, `1.000771`.
  None is mapped to CT01.

The immutable fixture is under `web/public/test-fixtures/na5/`; its README
records source locations and rendering provenance.

| Artifact | SHA-256 |
| --- | --- |
| `workflow.json` | `50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3` |
| Active blank PDF | `7415719c6a301bc1340b10041afd48b70ff00d4cd9ec27d0b36536128d8680af` |
| Immutable original DOCX | `a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751` |

All 43 field definitions in `schema.json` were compared against the immutable
workflow and match, including required/when/options/manual/inactive/placements.
Fixed `request_type=stay_extension` is preserved. Manual signatures,
certification and seals remain blank. Birth and current nationality are distinct;
no generic profile address is mapped into the temporary residential address.

`components/na5-demo/transport.ts` records these exact wire shapes, but uses no
HTTP transport at this checkpoint:

- `GET /workflows/1.001146/schema` returns the delivered schema structure.
- `POST /workflows/1.001146/preview` body: `{ values }`; the real response must
  be `application/pdf` plus `X-Review-Token`.
- `POST /workflows/1.001146/download` body: `{ values, review_token, confirmed }`.
  Draft templates remain blocked. A future integration must keep backend
  validation, template review, current-values token binding and acknowledgment.
- `POST /assistant/chat` body: `{ message, procedure_code, history }`;
  response: `{ status, answer, citations, model }`, never form-field patches.

The visible draft is an HTML overlay using Arial on three rendered blank PDF
pages. It is **not** the backend PDF renderer or an approval of the mapping.
Local overflow blocks review. Template/source revision and dates are inherited
from the delivery, not independently verified as current legal requirements.

## Verification observed

- Five focused NA5 contract tests pass: exact definitions/fixed value,
  conditional sponsor branches, date/chronology checks, distinct nationalities,
  immutable/stale review gates and producer wire shapes without assistant patches.
- `pnpm typecheck` and final `pnpm build` passed; production build includes
  `/demo/login`, `/demo/workspace`, `/demo/research` and secondary `/demo/ct01`.
- Browser: wrong password rejected; `admin/admin` enters NA5; logout removes
  editor and unsent answer; re-entry is blank. Direct reload shows session gate.
- Chat name/date/passport populate matching fields; manual name correction
  changes the same draft. Organisation/family and foreign-resident branches
  show the exact conditional choices. No automatic sponsor identity mapping.
- Producer example validates. Review plus acknowledgment still leaves download
  disabled. Mock question response leaves document content unchanged.
- Catalog displays all four codes; filtering `1.001146` opens the matching NA5.
- Desktop 1440x1000 and mobile 390x844 inspected. Mobile selected-field crop
  corrected; opening manual input hides the fixed chat composer. Original
  three raster pages and filled second-page/manual-signature areas inspected.
- No real mobile keyboard, live Clerk, NA5 HTTP service, provider call,
  persistent profile/database integration or filled NA5 PDF download was tested.

Commands from `web/`:

```powershell
pnpm exec tsx --test components/na5-demo/model.test.ts
pnpm typecheck
$env:NEXT_TELEMETRY_DISABLED='1'
pnpm build
pnpm exec next start --hostname 127.0.0.1 --port 3014
```

The test runner required scoped sandbox escalation because tsx could not start
under the restricted native runtime. No manifests, dependency versions or
lockfiles changed for this checkpoint.

## Earlier work retained, not repeated as NA5 evidence

- Integration base: `9cacda7320b5d18975a0bc2b62410eb74e45210f`.
- FORM-02 producer `9fd812891bce0a0f421871be76b6b2f40d6f4f30` consumed
  as `626ebc81fc2ee92c9b2a2f7504877fd1cdb54c59` (four UI files).
- Main UI: `f666b633c70b3f65df3813efc42d3ddce58fc8be`.
- Demo login: `d41ceaa970c7d9019bc04443649be923567efe23`.
- Manager protocol read separately: `17900c3234add2a8c81c323e10a20d44dde88f1e`.
- Site design source: `9905bc008f0f373eed9ba2cb8e7c3aa12f0ce6b9`.

Previously verified: 41 frontend tests covering six-field forms, profile
controller/lifecycle, deterministic chat and CT01 review. The synthetic forms
API generated its own preview/PDF; mocked actual-component auth/fetch checks
covered prefill failures, 401 clearing, account/session transitions and late
response guards. These are not live Clerk or NA5 backend proof.

CT01 keeps its separate original two-page fixture, three local fields and
acknowledged browser-print snapshot. Native Print / Save as PDF output remains
unverified; no printing work was expanded for this checkpoint.

These backend dependency commits were already picked before the review pause:

| Producer | Local consumer | Scope |
| --- | --- | --- |
| `584e1ee9adbb5fd1f0a845c1357e204833202d6f` | `7c6b96904bf76ddc695230109c476fe27fe966c9` | Profile storage guards/tests |
| `def58b7d04667d1865e281391dc25ef1723aa0a2` | `aeac1d55f5172e7b5c56f0b88de1e87075df060e` | Producer evidence |
| `b07e28e74b4b9174979b7922ad3576d0562c778a` | `7437b00a045c1d8ab473ae4c030f27ddd4ed6310` | Scaffold evidence |

The producer reported 147 API and 54 PGlite checks; UI-01 did not rerun them.
Real PostgreSQL, Clerk and TLS acceptance remain pending. The optional synthetic
API process predates those picks and is not runtime proof of the new guards.

## Local evidence and review boundary

Local ignored screenshots in `output/ui-01/`:

- `na5-demo-desktop.jpg`: production NA5 document/chat with fictional example.
- `na5-demo-mobile.jpg`: production selected-field crop and pinned composer.
- `na5-page2-review.jpg`: second page and blank manual signature areas.
- Prior `ct01-demo-*`, `forms-compact-*` and `auth-harness-evidence.txt` remain
  historical evidence of the separate earlier views.

The production preview is running on loopback 3014 with Clerk configuration
absent. NA5 needs neither API nor identity service. An optional synthetic forms
API on 8014 is unrelated to the NA5 mock. No source deployment, migration,
publication, push or main merge was performed for UI-01. The original published
Sites logo comparison remains separate.

Next action belongs to Kim: review this bounded intermediary checkpoint.
Wait for direction; do not automatically continue integration or polish.
