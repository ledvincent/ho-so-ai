# VOICE-01: public Vietnamese / English voice dialogue

## Current first-test scope: foreigner temporary-stay extension

Son explicitly chose alignment with Vincent's published catalog for the first
test. Realtime now uses `ho-so-ai-foreigner-intake-v2`: foreign-national temporary-
stay extension, with `1.001146` as a provincial integration candidate. It keeps
central extension, visa issuance and visa-exemption cases distinct, retains an
unknown procedure variant, and never converts a citizen request into this route.
NA5 is not presented as an approved or applicable form.

Refresh the existing `?audio=realtime&language=en` (or `vi`) page and start a new
call. No server restart or key re-entry is needed. This changes the conversational
scope; Vincent's assistant API is still not invoked. Sources/review/version gates
and report integration remain pending. The old typed/chained diagnostic routes
still exercise the historical citizen journey and must not be used for this new
demo. Their codes are not mappings to the foreigner catalog.

Current manual rubrics: `evals/foreigner-intake-scenarios.json` (12 synthetic
scenarios). `evals/intake-scenarios.json` and the two previously observed live
pilots belong to the earlier citizen profile; they do not validate this profile.
The optional live pilot script now targets the new scope but has not been run
against the provider for this increment. No reviewed data or form is enabled.

## Hồ Sơ AI conversation profile

The voice now follows a project-specific intake: welcome -> understand the goal ->
clarify the procedure variant -> confirm understanding -> useful
verbal recap and the next unresolved step -> close. It remembers answers within
the call, handles corrections/language switches, and does not keep repeating the
same menu or data-unavailable warning. This is a conversational plan in the prompt,
not a deterministic server workflow, legal decision, persisted dossier or report.

Canonical source: `src/voice_app/project_profile.json`. It contains VI/EN greetings,
language rules, tone, scope, conversation stages, privacy and unavailable-action
boundaries. It contains no official facts or personal data. The backend reads it;
a marked generated block in the headless client carries the same profile for
already-running local servers. No product HTML/CSS is changed by this profile.

```powershell
# After editing the canonical profile, from the repository root:
son/voice/.venv/Scripts/python.exe -m voice_app.project_profile --write-client
son/voice/.venv/Scripts/python.exe -m voice_app.project_profile
```

The check exits nonzero on drift. The client sends instructions/budget at channel
open, waits for a matching `session.updated`, then enables outbound microphone
tracks and starts the project greeting. A missing acknowledgement fails closed
after eight seconds. Refresh and start a new call to use the new profile without
re-entering the private server key. This is configuration synchronization, not
an authorization or grounding guarantee. Optional `onDiagnostic` also receives
`{event:'profile_applied', profileId:...}` without prompt/transcript text.

22 handwritten synthetic acceptance scenarios live in
`evals/intake-scenarios.json`, covering VI/EN new registration, renewal, correction,
language switch, missing official facts, phone delivery, foreigner scope, personal
access, fabricated-source pressure, project explanation and closure. They are not
retrieval examples, official records, or a procedure/report contract. The whole
catalog has not been run against the live model.

An optional live pilot uses only synthetic text and a silent synthetic microphone,
muted output and coarse observations. It never logs transcripts/keys/SDP, but it
does make potentially billable Realtime requests. It does nothing without `--live`.

```powershell
node son/voice/evals/live-intake-smoke.cjs        # no paid call
node son/voice/evals/live-intake-smoke.cjs --live # one English pilot
node son/voice/evals/live-intake-smoke.cjs --live --vi
```

The agent explains the intended reviewed-checklist/form/mobile-report journey
only as future functionality; no lookup, form, dossier or report tool is enabled.
Those adapters must wait for Vincent's retrieval/data contract and Kim's app.v1 /
Clerk integration agreement. The existing public demo cookie is not Clerk identity.
No new producer schema, retrieval implementation or personal-data tool is supplied.

## Live voice call (current requested experience)

The phone-like mode is **OpenAI Realtime over WebRTC**: one connection carries
microphone audio and the agent's live speech, automatic turn detection and
interruptions. It does not use MediaRecorder, transcript confirmation or a Send
button. Earlier browser/chained-audio modes below remain diagnostic alternatives.

After restarting the private launcher to load the new backend, open:

- http://127.0.0.1:8001/?audio=realtime&language=en
- http://127.0.0.1:8001/?audio=realtime&language=vi

Accept the live-audio disclosure, choose **Start voice call**, and allow the mic.
Talk normally, pause for the agent's reply, or interrupt it by speaking. **End
call** stops the microphone/peer and requests server hangup. If autoplay is
blocked, **Enable sound** resumes it; End call remains available at the top.
Nothing connects or transmits mic audio before the call button. Calls have a
three-minute demo limit (also limited by public-session expiry). Use fictional
needs, and headphones if speaker echo causes false interruptions.

`RealtimeVoiceClient` in `/realtime-client.js` is headless for Kim's product UI.
The existing test layout only hosts Start/End call controls; no product redesign.
The browser sends an SDP offer to the local server; the server authenticates the
unified `/v1/realtime/calls` request. Only SDP is returned, never an API key,
ephemeral credential or provider call ID. The server owns hangup, one call per
public cookie, four concurrent demo calls, lease timeout and shutdown cleanup.
The public cookie is not application identity and does not authorize personal data.

Default model: `gpt-realtime-2.1`; override `VOICE_REALTIME_MODEL` in the private
server environment before launching if account access requires another supported
model. `realtime_available` in capabilities means configured, not verified model
access. No extra package beyond the existing audio/httpx extra is needed.

Reply budget: 2,048 output tokens, including room for audio. The original 250
token cap could terminate a normal spoken answer mid-sentence. The browser also
sets this bounded allowance on data-channel open, so reloading the page and
starting a new call upgrades an already-running older backend without re-entering
its key. The server default matches it for new processes. Responses should remain
brief by instruction, not by an artificially tiny audio budget.

Generation completion (`response.done`) is not playback completion. The client
waits for `output_audio_buffer.stopped` before showing the agent as finished, and
keeps the caller-speaking state during an interruption. Optional `onDiagnostic`
receives only allowlisted response status/reason and token count, never transcript,
audio, credentials or provider IDs; it is not logged or persisted by default.

Reference: [official OpenAI WebRTC guide](https://developers.openai.com/api/docs/guides/voice-webrtc),
[turn detection](https://developers.openai.com/api/docs/guides/realtime-vad),
[hangup API](https://developers.openai.com/api/reference/resources/realtime/subresources/calls/methods/hangup).

This is an **exploratory conversation-only mode**: the agent clarifies intent,
does not have reviewed legal facts, and has zero tools for dossiers, forms,
reports or submissions. Instructions prohibit legal requirements/fees/eligibility
claims and discourage personal data. These are prompt constraints on generated
speech, not a deterministic guarantee of legal grounding. Do not treat model
speech/transcripts as a reviewed checklist or forward them to the report. This
mode is not the legally grounded release of VOICE-01; verified fact/tool delivery
still needs the contract and code gates with Vincent/Kim before integration.

Live audio goes directly to OpenAI while connected. No server audio/transcript
logging or persistence; optional assistant transcripts appear only in page memory.
Provider retention has not been reviewed. Closing the browser/withdrawing consent
releases local media and asks the backend to hang up. Failed network hangup cannot
guarantee immediate cessation of provider billing; the server also attempts hangup
at lease expiry and process shutdown. Do not expose this public prototype online.

Tests: `python -m unittest discover -s son/voice/tests -v` and
`node son/voice/tests/realtime_browser_smoke.cjs` (Playwright setup below).
The browser test uses synthetic WebRTC/media/provider events. Passing it does not
establish actual acoustic quality, real barge-in, latency or legal-policy adherence.

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
- Optional browser speech synthesis in the legacy mode; the live-call mode above
  instead uses the Realtime speech-to-speech model.
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
