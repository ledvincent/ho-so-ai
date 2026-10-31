# VOICE-01 standalone connected voice checkpoint

Owner: Son. Branch: `codex/son/voice-01-browser-conversation`.
Status: checkpoint; human microphone acceptance pending. No merge requested.
Code revision: recorded in the publication follow-up below after the code commit.
This supersedes older readiness statements in `RAG-VOICE-HANDOFF.md`.

## Scope and dependencies

Existing diagnostic voice page only. No Kim UI, integration-chat files, manager
board/status, data producer, collector, report, profile or form implementation
changed. Touched paths are only `son/voice/`: RAG consumer, privacy gate,
Realtime SDK, diagnostic harness, local launchers, tests, probes and handoff.

Fetched Vincent head: `61b99f37dbb79409dba8a6d4027ce023a1dcf5c4`.
Read `docs/assistant.md`, `docs/kim-start-here.md`, `docs/contracts/README.md`,
OpenAPI/document-card examples and the relevant producer types. Running source
remains `7c78ec4a731a2200d834f40e530eb0f2b5b9d38e` in the isolated WSL runtime.
The latest head removes demo/example routes and a form example URL; voice does
not use those. No upstream merge, source edits or database/index restore occurred.

Consumed chat fields: status, answer, citations, choices, retrieval_state,
procedure_code, documents and model. Signed state is opaque and stays on the
gateway. Only exact returned choice IDs are accepted. Document requirements,
conditions, quantities, provenance and opaque form metadata are retained; no
action is invoked. This does not establish a versioned reviewed report contract.
Vincent retains responsibility for source readiness and RAG relevance.

## Services and launch

Check the ports first; do not start duplicate services. Run from repository root
in separate interactive terminals, preserving the other team's servers:

```powershell
# Private voice, 8001. Key entered only in the masked prompt.
& 'C:\Users\Son\Documents\Codex\ho-so-ai\son\voice\.venv\Scripts\python.exe' -m voice_app.launch

# Existing restored Vincent runtime, 8004. Same private-input rule.
& 'C:\Users\Son\Documents\Codex\ho-so-ai\son\voice\start-vincent.ps1'

# Son's gateway, 8003; no credential needed here.
& 'C:\Users\Son\Documents\Codex\ho-so-ai\son\voice\.venv\Scripts\python.exe' son/voice/evals/live_rag_voice.py --assistant-url http://127.0.0.1:8004
```

Stop an owned service with Ctrl+C in its terminal. End the call first. Do not
stop 8000–8002 fixtures/legacy services or the separate product UI on 3020.
Source-code changes in Python require a restart; static SDK/page changes require
a fresh page load and call. No secret is saved or printed by these launchers.

Backend configuration is fixed in the local launcher: existing PostgreSQL
`hoso_kim_demo` on 55432, model `gpt-6.1-sol`, medium reasoning, BGE-M3 on 11434,
fresh process-only signing secrets. No `.env` load. Real Realtime default remains
`gpt-realtime-2.1`, voice `marin`; input transcript model is
`gpt-4o-mini-transcribe`. No model was silently substituted.

Readiness: 8001 `/api/voice/capabilities`, 8003 `/health`, 8004
`/assistant/setup`. Setup flags alone do not validate a conversation.
`/voice-runtime/diagnostics` on 8004 reveals only last provider HTTP status and
an allowlisted error code, never a key, transcript, body or signed token.

Test URLs:

- EN: http://127.0.0.1:8003/?audio=realtime&language=en&documents=rag
- VI: http://127.0.0.1:8003/?audio=realtime&language=vi&documents=rag

Port 8002 is still the separately labeled fixture. Real mode does not fall back
to it. 8003 rejects fixture lookup and fake `/assistant/chat` requests.

## Behavior and limits

- General goal goes to Vincent for routing. No default procedure or NA5 choice.
- A choice resolves the original question in Vincent's signed state. Ask the
  paperwork question as the next turn; do not infer that a missing card means
  no documents are required. `needs_clarification` can also be a sourced model
  question with a selected code and no machine-readable choices.
- Each session retains four history messages, signed state, last result and
  choices server-side. A lock rejects overlapping requests. Reset explicitly
  discards the prior procedure context; it does not reset the usage budget.
- Interrupted HTTP work is cancelled before commit while retaining the last
  completed context. Late client results and tool calls from older speech turns
  cannot restart speech. A delivered result can establish context even if the
  user subsequently interrupts its spoken explanation. Cancellation cannot
  retract provider work or guarantee cancellation of billing.
- 180-second total RAG deadline, 185-second browser deadline, no automatic
  retries, 12 lookup attempts per session, 8-minute call and 10-minute session.
  New calls get clean cookies/context. Teardown is serialized against restarts.
- End call releases tracks, playback and peer immediately, then deletes call
  and session. A disconnected peer gets an 8-second recovery window before
  cleanup. Microphone denied, missing and busy have separate visible states.
- HTTP errors, malformed responses/citations, expired state, timeout, no result
  and unsupported scope remain distinct from administrative answers. Partial
  sourced answers retain their status and uncertainty.
- Complete returned answers and source links stay in the diagnostic page's DOM
  until a new call/reload. No storage/logging of conversations is added. Citation
  URLs are rendered separately, prose as text. The voice is instructed not to
  read URLs or remove conditions when summarizing. Generated speech still needs
  human quality review; citation membership is not semantic entailment.
- No personal tools. The prompt sends only general questions, and a conservative
  server detector rejects recognizable personal names/contact/ID/date/credential
  patterns without forwarding or storing that question. This is not exhaustive
  PII detection and can reject legitimate questions. Audio still reaches OpenAI.
  Use fictional needs; this is not a production privacy/security certification.

## SDK for the integration chat (future work only)

Use the headless `RealtimeVoiceClient` exported by `realtime-client.js` with
`rag-tool.js` beside it. Keep the cookie gateway and browser on one origin.

```javascript
const voice = new RealtimeVoiceClient({
  onState(state) { /* connecting/listening/hearing/thinking/speaking/etc. */ },
  onFinalTranscript({role, text, itemId, final}) { /* ephemeral user/assistant text */ },
  onResult({status, answer, citations, choices, procedure_code, documents, context_reset}) {
    /* render backend result; retain document metadata, never auto-run actions */
  },
  onContextReset() { /* discard the prior selected procedure in the host UI */ },
  onError({code}) { /* show a technical/privacy error, not a legal answer */ },
  onDiagnostic(event) { /* status/reason/token counts only; optional */ }
});
await voice.start({language:'vi', consent:true, ragDocuments:true});
await voice.resumeAudio(); // only after an autoplay-blocked user gesture
await voice.stop();        // also aborts pending lookup and clears server session
```

`onTranscript(text)` remains the legacy diagnostic text callback; it includes
spoken assistant text plus full RAG answers/source lines. Prefer `onResult` and
`onFinalTranscript` for a future chat adapter to avoid duplication. Final ASR
events are asynchronous and deduplicated by item ID; final means transcription
finished, not that all assistant audio was heard. State events track playout.
Transcripts may contain personal speech: do not automatically persist or copy
them into the RAG/history, analytics or a report.

Change language at call start (`en`/`vi`); a spoken language switch preserves
conversation. Change procedure conversationally: the voice tool sends `reset:true`
with the new general question. For a complete reset, stop and start a fresh call.
The model never creates signed state or reconstructs choice IDs from labels.
There is no typed-chat submission API in this milestone; the integration chat
must agree shared session ownership before wiring Kim's existing text chat.

Official API references used for input transcript configuration and WebRTC
interruption semantics: [client events](https://developers.openai.com/api/reference/resources/realtime/client-events),
[Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations).

## Verification evidence

Automated, no provider calls:

```powershell
son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -q
son/voice/.venv/Scripts/python.exe -m voice_app.project_profile
$env:NODE_PATH='C:\Users\Son\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:VOICE_BROWSER_CHANNEL='msedge'
node son/voice/tests/realtime_lifecycle_smoke.cjs
$env:VOICE_TEST_URL='http://127.0.0.1:8003'
$env:VOICE_TEST_RAG='1'
node son/voice/tests/realtime_browser_smoke.cjs
Remove-Item Env:VOICE_TEST_RAG
$env:VOICE_TEST_FIXTURE='1'
$env:VOICE_TEST_URL='http://127.0.0.1:8002'
node son/voice/tests/realtime_browser_smoke.cjs
```

73 Python tests pass; profile parity passes. Browser SDK lifecycle and both
fixture/RAG harness modes pass with media, signaling and document HTTP mocked.
Coverage includes contract parsing, conditions/citations, exact choices,
continuity/reset, all documented HTTP errors, total deadline, malformed answers,
PII blocking, cancellation, isolation, forged-origin teardown, no fixture
fallback, final transcript dedup, rapid restart and audio resource release.
Starlette's existing httpx deprecation warning remains non-blocking.

Real HTTP/provider (fictional public questions only):

```powershell
son/voice/.venv/Scripts/python.exe son/voice/evals/live_rag_smoke.py --live --language en
node son/voice/evals/live_rag_call.cjs --live --vi
```

The HTTP probe is limited to three model calls; the browser probe to one call
and six tool requests (up to three successive clarifications, then two factual
questions). Both refuse to run without `--live`; no automatic retry.
The English HTTP journey passes: clarification (3 choices, no code); selected
`1.001146`; paperwork `insufficient_context` with 4 citations and 5 document
cards; follow-up `answered` with 2 citations and the same code. Observed stage
latencies: 0.3 / 10.2 / 9.1 / 3.0 seconds. These are one observation, not an SLA.
An earlier 502 disappeared after Son restarted with private credentials; its
original cause is unknown. Provider diagnostic subsequently reports HTTP 200.
The first probe also exposed an incorrect test assumption: selecting a choice
resolves the original general question, so paperwork must be a separate turn.
The first two VI WebRTC probes returned valid clarifications and audio, but did
not reach a procedure: the fixed scenario failed to answer Vincent's second
clarification. The probe now chooses only from each actual returned option list.
The voice prompt also forbids expanding the user's question with unasked topics.

Real WebRTC probe result: pending at initial handoff drafting; updated below.
Human microphone: **pending**, in both languages. No claim of acoustic success,
production readiness, legal/source approval, report delivery or Kim integration.

## Son's human microphone acceptance

Use the URL for the chosen language, accept the disclosure, click Start voice
call and allow the microphone. Use a headset if speaker echo causes interruptions.
Answer based on this fictional example, without giving any personal values.
If Vincent asks a second clarification, answer that too: for this test choose
the returned foreigner stay-extension option at provincial level. Do not move
to the paperwork question while the procedure remains unresolved.

| Step | English | Vietnamese |
| --- | --- | --- |
| General goal | I need help extending my stay in Vietnam. | Tôi muốn gia hạn tạm trú ở Việt Nam. |
| Clarification | In this fictional example, my sponsor said provincial immigration office. | Trong ví dụ giả định, bên bảo lãnh hướng dẫn nộp tại cơ quan quản lý xuất nhập cảnh cấp tỉnh. |
| Paperwork | What documents do I need? | Tôi cần chuẩn bị những giấy tờ gì? |
| Follow-up | How long does it take? | Thời gian giải quyết là bao lâu? |
| Interrupt while speaking | Wait, repeat the second document. | Khoan, nhắc lại giấy tờ thứ hai giúp tôi. |
| New call | End call, start again, ask about visa issuance. | Kết thúc, gọi lại và hỏi về việc cấp thị thực. |

Expected: backend clarification, same selected procedure for paperwork/follow-up,
consultable sources, explicit unresolved form/source conditions, interruption
stops old speech, repetition preserves conditions, microphone turns off at End,
fresh call does not retain the earlier procedure. Report failed step/language and
what happened, without sending personal recordings or credentials.
