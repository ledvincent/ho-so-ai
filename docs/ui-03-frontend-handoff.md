# UI-03 chat-first discovery review checkpoint

Status: **En revue — implementation paused for Kim.** UI-03 preview/API remain
running on 3020/8020. UI-02's 3018/8018 processes, source checkout and tested
checkpoint were preserved. UI-03 was not pushed or deployed.

## Review entry points

- Real route: http://127.0.0.1:3020/login
- Test accounts: `admin/admin`, `reviewer/reviewer-demo` (real local SQLite
  sessions, explicitly seeded fictional accounts).
- Labeled UI scenarios, after login: http://127.0.0.1:3020/workspace/scenarios
- The real route starts with **“Bạn cần hỗ trợ thủ tục gì?”**, a white canvas
  and bottom composer. No selected procedure, document, name/passport question
  or form-schema request on entry.
- A new-visa request on the real route currently returns explicit unavailable
  retrieval and keeps chat usable. It does not fall back to stay extension.
- Scenarios are manually selected synthetic fixtures. They demonstrate ambiguity,
  no match, unavailable service, unsupported/read-only visa, and a supported NA5
  association. They are not Vincent search results or legal advice.
- In the supported scenario: send a test query, inspect the candidate, explicitly
  select its form, then confirm. Only then does the matching NA5 viewer/editor open.
- Page controls, fit-page/fit-width, zoom and expansion expose the whole document.
  Manual edits and deterministic fixture replies update the same draft. “Đổi thủ
  tục” asks before discarding; cancel preserves the draft, confirm clears it.

## Exact sources and isolation

- Worktree: `C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-ui03-chat-first`.
- Branch: `codex/kim/ui-03-chat-first-discovery`.
- Base preserved: UI-02 `edb3c1cd4d41a5ac1ae8b0125e84c197862145a5`.
- UI implementation: `2865c96d8a1cb31fb82f8d32fd2d6c3c56f9b8c5`.
- DISCOVERY-01 producer code: `d0b2caa0ca128cc470bf9413eff54bfbfd447265`,
  consumed as `fc8f8490ffe975acd5282455aac2eebf6d80e680`.
- Producer evidence: `6c57d04b321eb3314220006f1d836629170a0999`, consumed as
  `2d54cb4aede620e0c37bdaa52b0705628849772f` (integrated code checkpoint).
- Final discovery contract Git-blob SHA256:
  `a9c67a9a72c78b0906fffbf39021e065d54c576a3f16767d827a6040d3a504c6`.
  Windows markdown checkout line endings differ; the committed blob was checked.
- Vincent producer remains `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`.
  Both immutable UI/API NA5 workflow snapshots still hash
  `50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3`.

This worktree has separate `.next`, runtime and ignored SQLite paths. Installed
dependencies are referenced read-only from UI-02; no dependency/lockfile changes.
Use direct Node CLI commands below: pnpm's automatic dependency check refuses
cross-worktree module junctions. That refusal did not modify UI-02 dependencies.
The UI-02 source checkout was verified clean at its preserved commit.

## Trusted selection boundary

The existing authenticated DISCOVERY-01 proxies own upstream access. UI-03 maps
Vincent's exact chat/search/procedure/form/schema responses. It adds no backend,
RAG pipeline, identity handler or credential storage.

- Grounded chat answers/citations are displayed as text/safe links. They never
  become procedure IDs, selected forms or field patches.
- Only structured search candidates can be inspected. Even one result needs
  explicit confirmation; raw scores are not shown as legal confidence.
- The user chooses an actual associated form. Filling requires the exact
  procedure/form tuple, facts_ready, the association-scoped discovery schema and
  the pinned field-assistance schema. Other selections remain read-only originals.
- Original attachments may be DOCX; an original download is not an inline PDF.
  The pinned NA5 raster/PDF viewer is used only for its confirmed matching tuple.
- Query edits, detail close, reset/logout and session changes abort/invalidate
  requests. An opened editor holds a captured confirmed context, independent of
  later inspected candidates. Canceling reset does not unmount that editor.
- Review/download gates, fixed stay_extension, manual signatures and distinct
  nationality/address/identity fields remain unchanged.

## Verification and evidence

- **130 offline tests pass**, including 7 new consumer/fixture checks and the
  delivered discovery tests. Typecheck and integrated production build pass.
- Browser: initial no form/identity prompt; real new-visa request -> unavailable,
  no candidates/form, enabled composer; fixture ambiguity -> explicit choice;
  unsupported visa remains read-only; single NA5 candidate does not auto-open;
  explicit candidate/form confirmation opens only the matching viewer.
- Fixture form replies are local/deterministic and tested with HTTP disabled.
  Their adapter cannot call the real field-assist provider. No Vincent search,
  embedding or live model calls were made in UI-03.
- Viewer: complete-page bounds checked, all three pages reachable, 200% zoom
  increases natural scroll width, expand/return retains draft. Desktop 1440x1000
  and mobile 390x844 inspected. At 390x450 the preview collapses rather than
  cropping a strip; composer bottom431.34 remains inside visible height450.
  Physical mobile keyboard behavior was not tested.
- Reset: cancel retains fictional field edits; confirmation removes the form and
  restores the general greeting. Logout returns to login; a second database
  account opens a fresh general chat with no previous form. Existing auth/session
  clearing and stale-response checks remain in the retained offline suite.
- Read-only review caught two races (query edit and closing pending confirmation);
  both were fixed before the final build. Opened form context is now captured and
  query edits invalidate outstanding work. Short-viewport composer issue was
  corrected and checked in the browser.
- Manager independently reports six production HTTP checks: signed-out401,
  database login200, session200, discovery chat503 DISCOVERY_UNAVAILABLE,
  logout200 and logged-out discovery401, with no-store headers and zero providers.
  Manager evidence: `work/manager-monitor/ui03-manager-http.json`.

Local ignored artifacts under `output/ui-03/`: `frontend-tests.txt`,
`chat-first-desktop.jpg`, `chat-first-mobile.jpg`,
`discovery-unavailable-mobile.jpg`, `full-page-desktop.jpg`,
`full-page-mobile.jpg`, `document-above-chat.jpg`. Viewer/scenario evidence is
synthetic selection/filling, using unchanged pinned document bytes.

## Runtime and restart

UI: http://127.0.0.1:3020 (production Node tool session55847).
API: http://127.0.0.1:8020 (Python tool session37210).
DB: this worktree's ignored `api/tmp/ui03-preview.sqlite`.

After verifying owned listeners before any deliberate restart, from `api/`:

```powershell
$env:OPENAI_API_KEY=''
& 'C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-auth-chat-checkpoint/api/.venv/Scripts/python.exe' scripts/run_local_checkpoint.py --database 'C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-ui03-chat-first/api/tmp/ui03-preview.sqlite' --origin 'http://127.0.0.1:3020' --port 8020 --demo-seed
```

From `web/`, using the existing read-only dependency references:

```powershell
$env:HOSO_AUTH_PROVIDER='local'
$env:HOSO_PUBLIC_ORIGIN='http://127.0.0.1:3020'
$env:HOSO_API_URL='http://127.0.0.1:8020'
$env:HOSO_VINCENT_API_URL=''
$env:NEXT_TELEMETRY_DISABLED='1'
node node_modules/next/dist/bin/next build --webpack
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3020
```

Vincent's runtime URL/data/index/calibration are not supplied. The real proxies
therefore fail explicitly with503 and no fixture fallback. No key is loaded in
the UI-03 API; real field-model assistance is also unavailable here. UI-02 retains
its separately tested connected field-assistance runtime. Local-auth loopback,
draft-template and public-hosting limits still apply.

Next action: Kim reviews UI-03. No further implementation, design polish,
provider calls, push or deployment is queued. Leave 3020/8020 running.
