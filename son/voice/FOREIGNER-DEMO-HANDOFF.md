# VOICE-01: first-test domain alignment

Owner: Son. Status: in progress; conversational increment ready for review.
Branch: `codex/son/voice-01-browser-conversation`.
Code: `74822859c2bcc11476d49d9da0ae037b2aba304f`, local, not pushed.

Son explicitly requested adapting to Vincent for a first test. This supersedes
the earlier citizen-only scope **for the Realtime demo**. It does not establish
agreement from Kim/Vincent or change the reviewed data contract. The canonical
profile `ho-so-ai-foreigner-intake-v2` now welcomes VI/EN callers asking about a
foreign national's temporary-stay extension. Candidate `1.001146` follows the
provincial catalog entry inspected at dependency commit
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`. Central extension, visa issuance and
visa-exemption cases remain distinct; unknown variants remain unresolved.

## Changed paths and migration

- `src/voice_app/project_profile.json` and generated `static/realtime-client.js`:
  bilingual greeting, scope, clarification, recap and explicit unavailable tools.
- `tests/realtime_browser_smoke.cjs`: expects the new acknowledged profile ID.
- `evals/foreigner-intake-scenarios.json`: 12 synthetic manual acceptance rubrics.
- `evals/live-intake-smoke.cjs`: new fictional foreigner pilot inputs, not run live.
- `README.md` and `ASSISTANT-INTEGRATION-HANDOFF.md`: scope decision and remaining gaps.

All listed paths are relative to `son/voice/`. Existing session/SDP APIs and the
2048-token output allowance are unchanged. Refresh the diagnostic Realtime page
and start a new call to apply the synchronized profile without restarting the
private server. Product UI ownership remains Kim's; no HTML/CSS change here.

Historical typed/chained diagnostic routes still target citizen procedures.
They are excluded from this new demo, not silently remapped. Their earlier
fixtures and the two previous live pilots do not validate this foreigner profile.
No collector/retrieval/schema implementation, global board or status file changed.

## Verification and limits

- `son/voice/.venv/Scripts/python.exe -m unittest discover -s son/voice/tests -q`:
  46 passed; existing Starlette dependency deprecation warning only.
- `son/voice/.venv/Scripts/python.exe -m voice_app.project_profile`: parity passed.
- `node son/voice/tests/realtime_browser_smoke.cjs` with bundled Playwright and
  `VOICE_BROWSER_CHANNEL=msedge`: passed, all media/provider signaling mocked.
- `node son/voice/evals/live-intake-smoke.cjs`: opt-in guard exits without a call.
- Staged whitespace check passed. No paid call, additional assistant/server or
  real microphone evaluation was performed. The 12 rubrics were not run live.

## Integration acknowledgements / next action

Vincent interface: **received / adaptation required**, not **tested compatible**.
The domain choice is now aligned for a first test, but this call still has no
retrieval tool and does not invoke `/assistant/chat`. It cannot yet answer official
requirements. The profile must not fabricate source review or choose NA5 editions.

Next, Son prepares server-side orchestration against Vincent's existing endpoint
after agreeing pinned procedure/version, reviewed hashes and checklist identity.
No source ID is treated as that missing contract. Kim app.v1/Clerk and report
integration: notice **received**, **adaptation required**; personal/report access
remains **blocked** pending agreed server authorization and report interfaces.
No spoken consent or public cookie grants dossier access. End-to-end voice/report
compatibility is not verified. See `ASSISTANT-INTEGRATION-HANDOFF.md` for the
existing interface assessment and proposed offline consumer tests.
