# VOICE-01: public Vietnamese voice dialogue

Owner: Son. Standalone browser integration shell, not the production app. The
procedure contract belongs to Vincent; this package does not define or replace it.
No collector files, root package configuration or collection tests are changed.

## Run locally (PowerShell, repository root)

```powershell
python -m venv son/voice/.venv
son/voice/.venv/Scripts/python.exe -m pip install -e './son/voice[test]'
son/voice/.venv/Scripts/python.exe -m uvicorn voice_app.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000. No API key needed for this routing milestone.

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v
```

Optional browser checks (Node.js, with the server already running):

```powershell
npm --prefix son/voice install --ignore-scripts
# Use an installed Edge browser, or install Playwright Chromium separately.
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/browser_smoke.cjs
```

Screenshots go to ignored `work/voice-qa/` from the repository root. Override
`VOICE_SCREENSHOT_DIR` and `VOICE_TEST_URL` if needed. The browser suite checks
typed dialogue and text fallback, not real acoustic recognition.

Dependencies are isolated under this component; `requirements.lock.txt` pins the
tested environment. For reproduction install `-r son/voice/requirements.lock.txt`
before the editable package command. The root local collector prototype is not a
dependency and must not be staged as part of this task.

## What it does

- Vietnamese speech recognition through the browser Web Speech API, with typed
  input when unavailable. Users check recognized text and press Send.
- Optional browser speech synthesis. No LLM or external realtime vendor configured.
- Conservative deterministic intent routing for registration (`1.004194`) versus
  renewal (`1.002755`), clarification on ambiguity, and explicit unsupported/no-result
  states. These are intent candidates, not reviewed procedure results.
- Public anonymous dialogue state: random HttpOnly cookie, fixed 10-minute TTL,
  restart/end invalidation, maximum 1,000 active dialogues and 60 turns each.
  State transitions are serialized in one process. Raw input is never stored in
  the session store. No personal-data or approval tools exist in this package.
- Intent selection stops at `lookup_pending`. The UI explicitly labels checklist,
  dossier, report and delivery as unavailable; there are no fabricated legal facts.

## Integration dependencies

Vincent: provide the reviewed lookup transport/contract, record and source version,
checklist with provenance/conditions, and explicit not-found/unreviewed/error
behavior. Then implement a consumer adapter here after agreeing the actual format.
Do not treat `/api/voice/turn` as the shared procedure/report schema: it only
describes this dialogue UI, and contains no legal record or checklist.

Kim: embed/replace this standalone page in the application. Application identity,
dossier owner checks and the authenticated consent decision remain Kim's scope.
Agree identity transport with Son before ACCESS-01. Anonymous dialogue cookies
are not user authentication and never authorize personal data. No `/api/dossier`
route is supplied or bypassed. The shared procedure contract is unchanged.

Only after a reviewed lookup is integrated should voice and report reference the
same exact record/version/checklist. This package alone cannot test that scenario.
Current compatibility guidance: keep existing consumers unchanged; there is no
producer schema migration in this task.

## Privacy and deployment limits

Use synthetic demo needs, not real identities. Server state holds only intent,
turn count and an expiry; process restart clears it. Inputs pass transiently through
request memory, but there is no application transcript/audio logging or persistence.
The page shows entered text in DOM memory until restart or close; no localStorage,
IndexedDB, analytics or transcript uploads. Launch with `--no-access-log` as above.

Speech recognition may send audio to the browser vendor's speech service. The page
requires a separate opt-in before enabling the microphone, and text remains usable
without it. Speech synthesis uses available browser/OS voices. Browser/vendor data
retention and Vietnamese voice availability have not been verified; do not use
personal data. See [SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
and [SpeechSynthesis](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis).

Real microphone recognition is browser-dependent and needs a supported browser,
permission and a secure context (localhost or HTTPS). A phone reaching a LAN HTTP
address is not a verified microphone demo. Hosted HTTPS, reverse-proxy origin/host
enforcement, distributed state, global/IP rate limiting, authenticated sessions,
CSRF integration with Kim, and production retention policy are not delivered here.
The local public API rejects missing/unapproved mutation Origins, limits request
bodies, sanitizes validation errors and sends no-store/security headers. These
tests are limited controls, not a production security attestation.

Default allowed Origins: `http://127.0.0.1:8000`, `http://localhost:8000`.
For hosted evaluation, explicitly configure `VOICE_ALLOWED_ORIGINS` (comma-separated
exact origins) and `VOICE_SECURE_COOKIE=1` over HTTPS. Run one worker only until the
session backend is replaced. Never expose this unauthenticated prototype publicly
as an application login/authorization implementation.

## Reproducible manual scenario

1. Start the server, open the page, type `Tôi cần làm tạm trú`: clarification.
2. Type `gia hạn`: intent `1.002755`, with reviewed data explicitly pending.
3. Restart; type `Tôi muốn đăng ký tạm trú`: intent `1.004194`.
4. Type `cần giấy tờ gì`: still pending, no guessed checklist/fees.
5. Type `gia hạn tạm trú cho người nước ngoài`: unsupported.
6. Type `đọc hồ sơ của tôi`: personal access unavailable.
7. Opt into browser speech, allow microphone, say a synthetic need, check the text,
   Send, and optionally enable Read aloud. Repeat with mic denied/text fallback.

Automated tests use handwritten synthetic utterances and no network services.
They do not claim real acoustic recognition, an LLM conversation, reviewed legal
retrieval, authentication, report delivery or full voice-to-report integration.
