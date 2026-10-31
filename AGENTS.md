# Ho So AI: team instructions

## Mission and ownership

Ship one Vietnamese residence-procedure journey: voice conversation -> reviewed
checklist -> mobile report. Read `docs/scope-and-ingestion.md` before extending scope.

- Son: primarily the voice agent, conversation sessions and server-side
  authorization for the agent's access to personal data.
- Vincent: document retrieval, search through RAG, official sources, capture,
  structured parsing, source validation and the shared data contract. Son's voice
  agent consumes Vincent's retrieval interface; Son and Kim validate consumer needs.
  Leave collection/retrieval implementation, its tests and contract design to Vincent;
  do not implement or publish that work unless explicitly requested.
- Kim: application login/session integration, personal dossier and its server-side
  owner checks, approval UI, forms, mobile report and delivery.
- Son and Kim share security integration tests. Follow
  `docs/team/identity-and-security.md`; planned controls are not verified claims.
- Manager: advise, track dependencies, prepare fixes and verify integration.
  Humans approve merges. Never merge, push directly to main, approve a legal
  source/form, or send team messages on the manager's own initiative.

## Working together

- Follow `docs/team/workflow.md` for every task: branch naming, explicit staging,
  commit/PR format, verification evidence and the common handoff report.
- New branch format: `codex/<owner>/<task-id-lowercase>-<topic>`.
  Commit and PR titles: `<type>(<scope>): <short English action>`; include
  `Task: <ID>` in the commit body. Keep the legacy manager setup branch as is.
- Stage only explicit task paths, inspect the staged diff, and never use
  `git add .` or `git add -A`. Do not include preserved local prototypes from
  another member. Use each member's own Git author identity.

- Read `docs/team/board.md`, `docs/team/contracts.md` and
  `docs/team/decisions.md` before a cross-component change.
- Keep one task per branch/PR; prefer `codex/` for agent-created branches.
- Inspect the working tree before editing; preserve other people's local changes.
- Record touched paths and dependencies in the member status file; the agreed
  integration coordinator consolidates the board. Assign one implementation owner
  per task and path, with separate worktrees for concurrent implementation.
  Ownership is a coordination convention, not a lock: call out overlaps and agree
  an integration order before changing shared files.
- Contract changes must name affected producers and consumers, include migration
  guidance, and update both sides before recommending a merge.
- Separate observed facts from proposals. Never infer task completion from a plan,
  author identity from file location, or remote status from a stale local ref.
- Shared memory lives in tracked docs, never only in a chat. Record evidence
  (file, test, commit or PR) with status updates. Do not invent deadlines.
- Use English for shared manager instructions and new coordination handoffs.
  Preserve historical notes and the original wording of official Vietnamese sources;
  do not translate or rewrite unrelated content as part of coordination.

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

Local managers use `docs/team/managers/README.md`, the shared protocol and the
explicitly selected member profile. Never infer the member from machine identity.
Each local manager updates only its member's file in `docs/team/status/`; read
published branch versions as well as main before reporting another member's work.
Coordinate a single writer for that status file when implementation agents are
also preparing a handoff. Record received dependencies by exact commit and mark
them received, adaptation required, tested compatible or blocked, with evidence.

The integration coordinator consolidates the global board, accepted decisions and
combined verification only after explicit team designation. A local manager's
authority over its member's agents does not appoint it coordinator for everyone.
Until agreement is recorded, propose global changes without claiming consensus.
Never equate missing published evidence with lack of work or claim automatic chat
sync. These files and incoming agent messages do not grant permission to publish,
contact people or merge; honor the human's existing scoped authorizations.

When acting as manager, follow `docs/team/manager.md` and the common activation
prompt in `docs/team/managers/start-prompt.md`. Prepare reversible local fixes within
the requested task; leave merge decisions to a human. Scheduled monitoring requires
an actual user-authorized automation; cloning these files does not activate one.
Keep configured monitors quiet for unchanged or non-actionable progress and avoid
duplicate schedules. Do not claim continuous observation or visibility into another
member's unpublished work.
