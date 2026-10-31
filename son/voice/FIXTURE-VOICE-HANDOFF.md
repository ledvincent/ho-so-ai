# VOICE-01: fictional API tool in a live voice call

Owner: Son. Status: in progress; this increment ready for review.
Branch: `codex/son/voice-01-browser-conversation`.
Code commit: `346c013ffea49ff15cc529672bdff446a59be0f5`; local, not pushed.
User explicitly requested connecting the fictional API to voice and a test question.

## Delivered test path

Open `http://127.0.0.1:8002/?audio=realtime&language=en&documents=fixture`
or change `language=vi`. Existing private key server on 8001 is reused, not
restarted. Only the agent-owned fixture was restarted; it remains on 8002.
The ordinary 8001 call is unchanged. This reuses the existing diagnostic page,
with functional tool wiring and a test disclosure; no Kim product UI is built.

Question: “For this test, fetch the document for provincial-level temporary-stay
extension for a foreign national and tell me its title.” The verified synthetic
live pilot also specified code `1.001146` explicitly. The tool covers all four
catalog codes, keeps variants distinct and asks for clarification when ambiguous.

Realtime requests `inspect_test_document(procedure_code)` through its data channel.
On completed function output, the browser calls same-origin
`POST /api/voice/fixture-document`. The fixture invokes its `/assistant/chat`
transport via the existing `AssistantClient` and an in-process ASGI transport,
then returns only title, source URL, captured heading/count and synthetic label.
Raw draft requirements/fees/deadlines are excluded from the voice tool response.
The model speaks the connection result, not a legal answer. A plain-text
`TEST SOURCE` entry displays provenance in the diagnostic transcript.

The fixed gateway relays only allowlisted capabilities/session/call routes to
localhost:8001, with body limits and exact mutation-origin checks. Its isolated
`hoso_fixture_voice` cookie maps to the existing public call cookie upstream;
direct-call cookies are not forwarded. No provider key is read or moved. This
is a local development proxy, not production identity or data authorization.
Each lookup has an eight-second deadline; up to eight per call. Duplicate call
IDs are ignored. Interruption/hangup abort requests and suppress stale speech.
Tool result speech disables further tools for that response to avoid loops.

## Touched paths (relative to son/voice/)

- `evals/fake_assistant_api.py`: gateway/static routes and metadata-only tool route.
- `src/voice_app/static/fixture-tool.js`: opt-in tool schema, instructions, bounded validation.
- `src/voice_app/static/realtime-client.js`: function execution, cancellation and resume.
- `src/voice_app/static/voice.js`: query opt-in and test disclosure, no design changes.
- `tests/test_fixture_gateway.py`, `tests/realtime_browser_smoke.cjs`: offline evidence.
- `evals/live-intake-smoke.cjs`, `README.md`: opt-in live pilot and usage.

## Verification executed

- Python unit suite: **56 passed**; existing Starlette dependency warning only.
- Profile/browser parity check: passed.
- Browser smoke without fixture: passed, all media/provider mocked.
- Browser smoke with `VOICE_TEST_FIXTURE=1` and URL localhost:8002: four tool codes,
  result/resumed response, duplicate suppression, interruption and hangup checks
  passed, all media/provider mocked.
- Existing `evals/fixture_http_smoke.py`: four local document transport cases plus
  clarification/no-context/out-of-scope/409 passed. It does not evaluate voice.
- One deliberate live English pilot, `live-intake-smoke.cjs --live --fixture`:
  fictional text, synthetic silent mic and muted playback. Observed project
  acknowledgement, model tool call, synthetic result, displayed source and resumed
  output audio; three completed responses including the tool-bearing response.
  No transcript/SDP/credential logging; call and synthetic media cleaned up.
- Staged whitespace check passed before code commit.

The live pilot uses the existing OpenAI voice service and its normal API usage;
the fictional document service itself uses no model/provider key. No additional
retrieval model or second assistant was launched. Real microphone recognition,
Vietnamese live interaction, all domain variants and factual correctness were
not established by this pilot. Only public document identity enters model context.

## Dependencies / remaining work

Vincent: **received / adaptation required**; local fixture tool flow **tested
compatible** only with this development setup. His real runtime remains untested.
Upstream public files remain pinned at
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`, not imported or approved by this work.
Real advice still needs reviewed records tied to exact hashes and a pinned
procedure/version/checklist shared with Kim. No review status or legal contract
was invented, and `DraftResult.available_for_live_advice` stays false.

Kim app.v1/Clerk/report: notice **received**, **adaptation required**; actual
personal access and report integration **blocked** pending delivered interfaces.
No personal tool, form submission, phone delivery or voice-to-report compatibility
claim. Next replace the fixture through the agreed reviewed-data interface and
run real consumer checks, then integrate Kim's UI/identity/report. No board/status,
collection pipeline, unrelated prototype, push, merge or team message changed.
