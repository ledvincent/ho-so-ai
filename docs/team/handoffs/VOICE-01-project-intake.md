# VOICE-01: project-specific conversational intake

- Owner: Son
- Task: VOICE-01 — personalize the existing live voice prototype while reviewed data is pending.
- Status: In progress; this increment is ready for review. Cross-component integration remains pending.
- Branch: `codex/son/voice-01-browser-conversation`
- Code commit: `45943572a225fa0cd628d5977a04e66ad5c9dcc8`
- Publication: local only; no push, PR, merge or team message.

## Delivered behavior and paths

The AI introduces Hồ Sơ AI in Vietnamese or English, clarifies initial temporary-
residence registration versus renewal, confirms its interpretation and offers a
verbal recap. The prompt asks it to retain context through corrections and language
switches, avoid repeated intake, and explain unavailable official information or
phone delivery without simulating those actions. These are model instructions,
not a deterministic workflow or a guarantee of grounded output.

Touched component paths:

- `son/voice/src/voice_app/project_profile.json`: canonical bilingual conversation profile, no legal records.
- `son/voice/src/voice_app/project_profile.py`: server loader and generated-client parity check/update.
- `son/voice/src/voice_app/realtime.py`: loads the canonical instructions.
- `son/voice/src/voice_app/static/realtime-client.js`: generated profile and acknowledgement gate before outbound mic/greeting.
- `son/voice/pyproject.toml`: packages the profile resource.
- `son/voice/tests/realtime_browser_smoke.cjs`: verifies profile synchronization and pre-ack mic/greeting behavior with mocked WebRTC.
- `son/voice/evals/intake-scenarios.json`: 22 explicitly synthetic VI/EN acceptance scenarios.
- `son/voice/evals/live-intake-smoke.cjs`: opt-in synthetic live pilot with muted output and coarse observations only.
- `son/voice/README.md`: usage, configuration, verification and limits.

No Sites/product UI, collector, retrieval implementation or producer contract was
changed. Unrelated root prototypes were preserved. No board/status changes were
prepared in this increment; the manager owns the coordinated status update.

## Voice/session interface and configuration

Existing `/api/voice/session`, `/api/voice/realtime` POST/DELETE and public demo
cookie interfaces are unchanged. The headless client still exposes start/stop and
state/transcript callbacks; optional diagnostics add only
`{event: 'profile_applied', profileId: 'ho-so-ai-intake-v1'}`. This is not an app,
procedure or report contract. The demo cookie is not authenticated application
identity and grants no personal-data access.

The server reads the profile. The browser carries a generated copy and sends
`session.update` on the data channel, retaining the existing 2048 output budget.
Outbound microphone tracks remain disabled until matching instructions are
acknowledged; an eight-second timeout ends an unacknowledged call. This also adapts
the already-running local server on refresh/new call without restarting it or
re-entering its key. No key, transcript, SDP or real personal data is committed.

After a profile edit, run from the repository root:

```powershell
son/voice/.venv/Scripts/python.exe -m voice_app.project_profile --write-client
son/voice/.venv/Scripts/python.exe -m voice_app.project_profile
```

## Verification evidence

- `son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -v`: 46 passed, offline/mocked; one dependency deprecation warning.
- `son/voice/.venv/Scripts/python.exe -m voice_app.project_profile`: profile and browser asset agree.
- `node son/voice/tests/realtime_browser_smoke.cjs`, with bundled Playwright on `NODE_PATH` and `VOICE_BROWSER_CHANNEL=msedge`: passed; WebRTC/provider mocked.
- `node son/voice/evals/live-intake-smoke.cjs`: exits without dependencies or any paid call unless `--live` is supplied.
- Opt-in live pilot run once in English and once in Vietnamese on the existing private local server: four assistant responses per pilot; both observed profile acknowledgement, project greeting, renewal context, an unavailable-action explanation, no numeric fee and no sent-report claim under the script's coarse checks. Inputs were fictional text, microphone synthetic silence, playback muted; reply text remained transient and was cleared. Calls were closed afterward.
- `git diff --cached --check`: passed before the code commit.

The full 22-scenario catalog has not been executed against the model. Two pilots
do not validate all prompt boundaries, legal safety, real microphone quality,
acoustic interruptions or end-to-end voice/report consistency. No additional paid
calls were made merely to prepare this handoff. Existing servers/ports preserved.

## Dependency acknowledgements and integration order

The shared ownership protocol at
`17900c3234add2a8c81c323e10a20d44dde88f1e` on
`origin/codex/kim/team-03-manager-protocol` was received/read read-only, not merged.
Vincent owns retrieval/RAG and the shared data contract; Kim owns the unique Sites
product UI. A coordination notice is not evidence that their integration exists.

| Dependency | Acknowledgement / compatibility | Next action |
| --- | --- | --- |
| Local standalone voice prototype | **tested compatible**, only within the verification scope above | Son maintains the profile and adapter. |
| Vincent reviewed retrieval/data contract | **blocked** pending a delivered versioned schema/API, reviewed fixtures and provenance/authorization requirements | Vincent delivers contract; Son adapts its consumer afterward. No competing schema or retrieval code supplied here. |
| Kim app.v1 | Notice **received**; **adaptation required**. Concrete versioned integration artifact was not received/observed in the refs inspected | Kim supplies the app-facing agreement; Son and Kim verify the voice/session boundary together. |
| Kim Clerk identity integration | Notice **received**; **adaptation required**, personal-data integration **blocked** pending agreed server verification and owner/approval rules | Agree issuer/audience/JWKS verification and server-enforced access flow before enabling personal tools. Public demo cookie remains separate. |
| Kim Sites/report/mobile delivery | Ownership **received**; end-to-end compatibility **blocked** pending actual reviewed report/delivery interface | Kim supplies the consumer; both components must reference the same approved procedure version/checklist. |

No personal dossier, source lookup, form submission or mobile delivery tool is
enabled. The model may only describe those as future integrations. The next step
is to adapt this existing voice client to delivered interfaces, then verify the
shared procedure/version and authorized voice-to-report scenario with Kim and
Vincent. Human approval remains required for publication/merge decisions.
