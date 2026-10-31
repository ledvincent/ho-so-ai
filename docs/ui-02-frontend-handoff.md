# UI-02 connected local review checkpoint

Status: **En revue — implementation paused for Kim's test.** The connected
browser acceptance passed on 31 October 2026. Preview and API remain running.
No push, merge, deployment or automatic follow-on polish.

## Open and test

- Entry: http://127.0.0.1:3018/login (the root redirects here).
- Synthetic database account A: `admin` / `admin`.
- Independent account B: `reviewer` / `reviewer-demo`.
- Login first; internal navigation appears only inside the authenticated views.
- The assistant asks one missing NA5 question. Reply with fictional information;
  the server validates the model proposal and the same document updates above
  the conversation. The composer remains at the bottom.
- Use `Sửa trực tiếp` for a correction; choose the field, edit, then `Áp dụng`.
  Changes are visible in the conversation and can be undone.
- `Tài liệu` opens review. The template is still draft; filled-form download is
  locked. Manual signatures/certification remain blank.
- `Đăng xuất` clears protected state and revokes the session. Direct private
  URLs return to login. The review browser is left signed out for Kim.

Only use fictional data. These are real local SQLite accounts/sessions with
password hashing and server authorization, not the earlier React-only demo
session. They are explicitly seeded localhost fixtures, not deployment accounts.
Account A has the synthetic profile marker `Fictional Account A` from the
explicit first-save check; B has no saved profile. Neither contains real PII.

## Exact source and integration

- Branch: `codex/kim/ui-02-guided-portal`.
- Preserved UI-01 checkpoint: `b4a3ebf2d208ad4533b2a50f69aec9462626145c`.
- Final implementation: `da2c9abeaacb3b0c3a8b10f0454565d059322cdd`.
- AUTH-02/CHAT-01 producer code: `21d3988780c4ecc596c80f49e6503b84f2c8c18c`,
  consumed cleanly as `8de13111a1d16a424a25c2799a1ef355c036fad5`.
- Producer evidence: `87993e3d5f5f297a231ca4bc55195016f2d46601`, consumed as
  `b4fd78ec6d5fdf2a10cb668a3dd0a36cfb8034b3`.
- Final producer contract SHA256:
  `1fda31ea423f25f41739478f651f114771e2c4c66d407489a61129172ff927dc`.
- Vincent's source: `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`.
  NA5 `1.001146`, 43 definitions, exact choices/conditional branches and fixed
  `request_type=stay_extension`. Both API and UI workflow snapshots still hash
  `50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3`.
  Original PDF/DOCX fixture bytes were not edited.

The scaffold owns handlers, opaque HttpOnly cookies, database sessions, origin
checks, private-route guards and the model adapter. UI-02 consumes that exact
contract; it adds no competing auth/API or retrieval handlers. Server pages pass
only `identityFrom(...)`'s public user/expiry DTO to the client, never a token.

## Observed combined acceptance

| Scenario | Observed result |
| --- | --- |
| Signed-out entry / incorrect password | Login only, no internal navigation; incorrect password rejected and password cleared |
| Real database login | A enters the protected portal; deterministic empty-message initial guidance asks for full name, without calling the model |
| First profile | GET 404 opens an editable revision-zero state; explicit first save succeeds |
| Live field assistance | One successful real `gpt-4o-mini` call proposes a fictional name; it appears on the same NA5 document and the assistant asks the next missing question |
| Manual correction | Corrected name appears on that document and in the visible change record; no model request |
| Profile separation | A's saved profile remains its original marker after model and manual form edits |
| Draft export gate | Review displays current values and fixed stay_extension; download remains disabled with pending-review status |
| Logout / direct access | Draft and unsent composer disappear; direct workspace returns to login with no private navigation |
| Account B | Empty draft/composer and no saved profile; A's marker and corrected form name are absent |
| HTTP guards | Workspace, portal, research and dotted document URL ->307 /login; session/schema/profile APIs ->401; no-store headers |
| Server revocation | Separate synthetic HTTP session: schema 200 before logout, same revoked token ->401 afterward |
| Responsive view | Desktop 1440x1000 and mobile 390x844; document above chat, compact/collapsible/expanded preview, bottom composer |
| Short focused viewport | At 390x450, focused composer bounds remain inside the visible viewport (bottom 431.34 <450); physical mobile keyboard was not tested |
| Stale/account guards | Offline consumer tests reject wrong request/revision, account change during reply, manual signature proposal and 401; abort/generation checks cover edits/navigation |

The first browser chat attempt failed in the restricted runtime before an HTTP
provider response. An unauthenticated network probe returned ConnectError;
with required network permission it reached OpenAI with 401 (no key/model call).
The API was restarted on the same DB with outbound access. The reserved browser
request then succeeded. Producer: two successful live calls; UI-02: one
successful live call. No automatic provider retries or further live tests.
The retry remains visible as a duplicate user message in the captured transcript.

Browser QA also found the legacy profile controller passed itself as the native
fetch receiver. Wrapping the default fetch invocation fixed the fresh-profile
error. A regression test covers this; existing 404 creation, conflict/revision,
late-response and explicit-save behavior is retained.

## Checks and evidence

- Final production build, including TypeScript, passed with LOCAL config.
- **62 offline frontend tests passed** across auth policy, profile lifecycle,
  form/review models, CT01/NA5 and the guided consumer. No provider calls in tests.
- Focused consumer tests also passed after using the shared identity parser.
- Producer separately reports 247 API tests, 38 helper tests, 20 HTTP checks,
  profile-contract check and actual restart persistence. UI-02 did not rerun the
  full API suite or reset the producer's evidence database.

Local ignored evidence in `output/ui-02/`:

- `frontend-tests.txt`: final 62-test output.
- `http-acceptance.txt`: direct guard and server-revocation checks.
- `live-chat-desktop.jpg`: successful live model proposal and next question.
- `connected-desktop.jpg`, `live-chat-mobile.jpg`: corrected same-document view.
- `login-desktop.jpg`: real connected login entry.

## Running resources and restart

- UI: loopback `3018`, production Next process, tool session `83710`.
- API: loopback `8018`, outbound-enabled Python process, tool session `64550`.
- New ignored DB: `api/tmp/ui02-acceptance.sqlite` in this isolated checkout.
- Runtime Python environment reused read-only from the backend owner's checkout.
- Backend owner's `3016/8016` processes and evidence DB were not stopped/reset.
- Authorized key is loaded into API memory from the original ignored env file.
  No key was copied, printed, placed in client code or committed.

For a deliberate restart, verify owned listeners first; do not run duplicate
processes on these ports. From this checkout's `api/`:

```powershell
& 'C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-auth-chat-checkpoint/api/.venv/Scripts/python.exe' scripts/run_local_checkpoint.py --database 'C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-frontend-integration/api/tmp/ui02-acceptance.sqlite' --origin 'http://127.0.0.1:3018' --port 8018 --demo-seed --key-file 'C:/Users/Kim/Documents/ChatGPT/Hackathon/.env.local'
```

The API process needs authorized outbound HTTPS. From `web/` in another terminal:

```powershell
$env:HOSO_AUTH_PROVIDER='local'
$env:HOSO_PUBLIC_ORIGIN='http://127.0.0.1:3018'
$env:HOSO_API_URL='http://127.0.0.1:8018'
$env:NEXT_TELEMETRY_DISABLED='1'
pnpm build
pnpm exec next start --hostname 127.0.0.1 --port 3018
```

## Limits and stop boundary

This is narrow, stateless **form-field assistance**. The model extracts evidence
for the current field; the server chooses question/guidance text deterministically.
Vincent owns procedure/RAG Q&A (`answer/citations/status/model`), which is not a
field-patch contract. The UI shows procedural questions as unavailable until his
approved runtime is connected. No duplicate RAG or voice implementation was added.

NA5 is an HTML overlay on immutable raster pages, not a connected backend PDF
preview/export. Review is still draft. Profile-to-NA5 prefill is not connected;
nationality/address/identity mappings are not inferred. Profile save is explicit.
Live Clerk, PostgreSQL/RLS/TLS, Son's voice/access adapter, physical mobile keyboard
and public hosting were not accepted by this checkpoint.

See [hosting assessment](ui-02-hosting-assessment.md). Sites currently serves
static branding; this LOCAL auth mode intentionally rejects non-loopback origins.
Render Node/Python services with durable storage are a hosting recommendation
after the backend owner supplies a reviewed hosted identity configuration.
No public jury link can be deployed unchanged from this source today.

Kim's next action: test the local preview. Implementation is paused. Do not
automatically push, deploy, broaden integration or polish before her review.
