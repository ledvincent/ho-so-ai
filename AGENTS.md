# Ho So AI: team instructions

## Mission and ownership

Ship one Vietnamese residence-procedure journey: voice conversation -> reviewed
checklist -> mobile report. Read `docs/scope-and-ingestion.md` before extending scope.

- Son: search/retrieval and voice agent.
- Vincent: official sources, capture, structured parsing, source validation and
  ownership of the shared data contract. Son and Kim validate consumer needs.
  Leave collection implementation, its tests and contract design to Vincent;
  do not implement or publish that work unless explicitly requested.
- Kim: forms, mobile report and delivery.
- Manager: advise, track dependencies, prepare fixes and verify integration.
  Humans approve merges. Never merge, push directly to main, approve a legal
  source/form, or send team messages on the manager's own initiative.

## Working together

- Read `docs/team/board.md`, `docs/team/contracts.md` and
  `docs/team/decisions.md` before a cross-component change.
- Keep one task per branch/PR; prefer `codex/` for agent-created branches.
- Inspect the working tree before editing; preserve other people's local changes.
- Record touched paths and dependencies on the board. Ownership is a coordination
  convention, not a lock: call out overlapping changes and agree an integration order.
- Contract changes must name affected producers and consumers, include migration
  guidance, and update both sides before recommending a merge.
- Separate observed facts from proposals. Never infer task completion from a plan,
  author identity from file location, or remote status from a stale local ref.
- Shared memory lives in tracked docs, never only in a chat. Record evidence
  (file, test, commit or PR) with status updates. Do not invent deadlines.
- Use French for team updates; follow existing code/document language elsewhere.

## Verification

Use the verification commands documented by each component owner once delivered.
Collection code, its tests and its CI are left to Vincent and are not shipped
with the manager. Running a live collector does not establish integration.
Verify the shared contract and voice-to-report scenario once those components exist.

## Code Review Rules

- Check changed behavior against the common procedure/report contract, including
  no result, unreviewed records, source changes and unsupported procedures.
- Capture output is draft. Only human-reviewed records tied to specific hashes
  may feed the live voice/report path. Never silently choose a CT01 edition.
- Preserve official wording, quantities, conditions and provenance. Retrieval date
  does not establish a legal effective date. Do not infer legal facts with an LLM.
- Voice and report must reference the same procedure version and checklist;
  synthetic fixtures must be explicitly labeled and kept out of production data.
- Keep user identity, phone numbers, transcripts, credentials and report tokens
  out of Git, public logs and the source corpus.
- Report actionable bugs with affected paths and concrete impact. A green unit
  suite alone does not prove the three components integrate or eliminate conflicts.

## Manager mode

When acting as manager, follow `docs/team/manager.md`. Prepare reversible local
fixes within the requested task; leave fusion decisions to a human. Do not claim
continuous monitoring or visibility into another member's unpublished work.
