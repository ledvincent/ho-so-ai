# VOICE-01: public Vietnamese / English voice dialogue

Owner: Son (backend/dialogue). Kim owns the product UI, including the voice screen
and microphone controls. The static page in this package is a development/test
harness only; its design is frozen and does not prescribe Kim's UI. The
procedure contract belongs to Vincent; this package does not define or replace it.
No collector files, root package configuration or collection tests are changed.

## Run locally (PowerShell, repository root)

```powershell
python -m venv son/voice/.venv
son/voice/.venv/Scripts/python.exe -m pip install -e './son/voice[test]'
son/voice/.venv/Scripts/python.exe -m uvicorn voice_app.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000. The frozen test page remains Vietnamese; Kim owns
the bilingual product UI. The backend supports both languages without an API key.

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v
```

Optional browser checks (Node.js, with the server already running):

```powershell
npm --prefix son/voice install --ignore-scripts
# Use an installed Edge browser, or install Playwright Chromium separately.
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/browser_smoke.cjs
node son/voice/tests/audio_client_smoke.cjs
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
- Bilingual backend: `POST /api/voice/session?language=en` (default `vi`), then
  `POST /api/voice/turn` with `{ "text": "renew" }`. A turn may specify
  `language: "vi"` or `"en"` to change reply language without losing intent.
  Replies add `language` and `speech_language`; legacy Vietnamese requests work.
  These are canned dialogue translations, not translations of official facts.
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

Kim: build the product UI against the backend; do not copy this test page as a
requirement. Current endpoint behavior and open integration choices are documented
in `docs/team/handoffs/VOICE-01.md` (repository root), pending Kim's review.
Application identity,
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

## Optional server audio adapter and headless client

For private local activation without saving a key or placing it in a shell
command, open an interactive terminal at the repository root:

```powershell
son/voice/.venv/Scripts/python.exe -m pip install -e './son/voice[audio,test]'
son/voice/.venv/Scripts/python.exe -m voice_app.launch
```

The launcher asks for a hidden key (or uses an existing process `OPENAI_API_KEY`),
then runs only on `127.0.0.1:8001`, leaving the offline port-8000 demo untouched.
No audio API call is made at startup; model access is not validated by launching.
The typed key is kept only by the server process, not written to `.env`, shell
history or a new environment variable. Unsafe echoed-input fallback is refused.
Stop with Ctrl+C. Key validity, model access, actual billing and speech quality
still need a real, synthetic-audio smoke test after the user enters the key.
The default test UI remains browser-speech based. An explicit diagnostic mode
uses the server adapter without adding a second product UI:

- Vietnamese: http://127.0.0.1:8001/?audio=openai&language=vi
- English: http://127.0.0.1:8001/?audio=openai&language=en

Accept the audio-processing/AI-voice disclosure, then check **Read aloud**
(`Đọc câu trả lời`) to hear the greeting. Nothing plays or calls the paid audio
provider on page load. **Record with OpenAI** starts the microphone; press **Stop
recording**, check the recognized text, then **Send**. Read aloud stays on for
subsequent replies. Switching it off or recording interrupts playback. No restart
is needed after static test-harness assets change; reload the diagnostic URL.
Product UI design/integration still belongs to Kim.

The new audio path is speech recognition -> user-confirmed text -> deterministic
dialogue -> synthesis of the latest server-owned reply. It does not forward
unverified model-generated legal answers to audio. An unrestricted realtime
speech-to-speech conversation is not implemented.

OpenAI audio is an optional adapter, not an agreed team vendor. Documentation
checked on 31 October 2026: [voice pipelines](https://developers.openai.com/api/docs/guides/voice-agents),
[transcription](https://developers.openai.com/api/docs/guides/speech-to-text),
[speech synthesis](https://developers.openai.com/api/docs/guides/text-to-speech).
Default adapter models: `gpt-4o-mini-transcribe`, `gpt-4o-mini-tts`. Models are
configurable; live account access and VI/EN acoustic quality are unverified.

Activation is deliberately explicit. Install the audio extra, supply a key privately
as the server process's `OPENAI_API_KEY`, set `VOICE_ENABLE_AUDIO_API=1`, then
restart. Never place the key in frontend code, Git, a URL or a chat. The app does
not load `.env` files automatically. No key or flag means audio calls return 503;
text dialogue and the existing browser test adapter remain available.

```powershell
son/voice/.venv/Scripts/python.exe -m pip install -e './son/voice[audio,test]'
# After setting OPENAI_API_KEY privately in the server environment:
$env:VOICE_ENABLE_AUDIO_API='1'
# Optional: VOICE_TRANSCRIBE_MODEL / VOICE_TTS_MODEL
```

Only synthetic demo audio is intended until identity, consent integration and
provider retention settings have been reviewed. Audio and transcript cross to
OpenAI for transcription; only server-owned canned replies cross for synthesis.
No provider key or ephemeral credential is sent to the browser. There is no
claim of zero retention by the provider. HTTP failures are sanitized, no retries
are automatic, and no live API requests ran during implementation.

### Backend additions for Kim

- `GET /api/voice/capabilities`: supported language/speech-locale map, audio
  availability, byte limit, disclosure and transcript-confirmation requirements.
- `POST /api/voice/transcribe`: raw audio body with its MIME type; existing dialogue
  cookie and `X-Audio-Consent: 1` required. Up to 2 MiB; WebM, Ogg, WAV, MP4, MP3
  container signatures checked, not full codec validation. Returns `text`,
  `language`, `requires_confirmation: true`; it never advances the dialogue.
- `POST /api/voice/speech`: empty body, same cookie/consent requirement; reads only
  the last server reply and returns MP3 with `X-AI-Generated-Audio: true`. Arbitrary
  client synthesis text is rejected. UI must disclose AI-generated audio first.
- 20 audio-operation attempts per dialogue, one in flight at once, 20-second
  upstream timeout, 4 MiB output cap. Invalid/failed operations also use budget.
  These are local demo limits, not authenticated billing/abuse protection.
- End/expiry during an upstream operation discards its response; already uploaded
  audio cannot be retracted. Global quotas/distributed limits are not implemented.

`/audio-client.js` exports `VoiceAudioClient`, a **headless integration adapter**:

```javascript
import { VoiceAudioClient } from '/audio-client.js';
const voice = new VoiceAudioClient({
  onState: state => { /* Kim updates her UI */ },
  onTranscript: transcript => { /* show/edit text, ask user to confirm */ }
});
const welcome = await voice.startSession('en'); // or 'vi'
// After UI disclosure of upload to OpenAI and AI-generated audio:
voice.setAudioConsent(true);
await voice.startRecording();
voice.stopRecording(); // automatic limit: 20 seconds, browser-side only
// Only after the user checks the returned transcript:
const reply = await voice.turn('I want to renew temporary residence');
await voice.readReply();
voice.interrupt(); // stop output/recording, release tracks, abort pending fetch
await voice.endSession();
```

No UI markup/styles or redesign is included. The adapter can interrupt playback
when starting a new recording, but is not full-duplex realtime/VAD. It enforces a
20-second recording limit client-side; the server enforces bytes, not duration.
Cancellation of fetch does not guarantee cancellation of provider billing. Kim's
UI must handle rejected promises, playback policy, errors, consent and transcript
confirmation. Error states: `recording_error`, `audio_too_large`,
`transcription_error`, `speech_error`, `playback_error`; methods may reject with
`voice_http_<status>`, permission errors or `AbortError`. Text fallback remains an
application responsibility. UI/identity integration and phone acoustic testing
remain unverified.

Migration: existing Vietnamese endpoints stay valid; response fields are additive.
Kim can adopt language selection and the headless adapter independently. No
Vincent procedure/report schema changed, and no legal content is translated.
Keep the same origin and `/api/voice` paths until proxy/cookie transport is agreed.

Diagnostic-page wiring test (mocked audio; no paid calls):

```powershell
node son/voice/tests/openai_harness_smoke.cjs
```
