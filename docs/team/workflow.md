# Shared agent workflow

This workflow applies to Son, Vincent, Kim and their managers. It defines how
work is assigned, verified and handed over. Vincent owns the procedure-data
contract; no manager creates a competing schema.

## 1. Ownership and coordination

| Owner | Main scope | Coordination required |
| --- | --- | --- |
| Son | Primarily the voice agent, conversation sessions and server-side tool authorization | Consume Vincent's retrieval interface and contract; agree identity, consent and profile access with Kim |
| Vincent | Document retrieval, search through RAG, sources, collection, structured data, review, the procedure contract and related tests | Deliver the retrieval interface, format and examples needed by Son and Kim |
| Kim | Login, personal profiles and owner checks, consent UI, forms, reports and delivery | Send authenticated consent decisions to Son; preserve the procedure version and checklist used by voice |
| Local manager | Coordinate the named member's agents, dependencies, reviews and handoffs | Maintain that member's status; respect other owners' scope |
| Agreed integration coordinator | Consolidate the global board, accepted decisions, integration order and combined verification | Appointment requires explicit team agreement; propose changes until that agreement exists |

Assign every task an owner, branch/worktree, allowed paths, dependencies and a
verifiable result. Use one implementation owner for each task and file at a
time. Separate branches in the same checkout do not isolate concurrent edits;
use separate worktrees and agree ownership of shared configuration and contracts.

Describe a required change in another member's scope and coordinate with that
owner before implementing it. Announce shared dependency/configuration changes
in the PR. Do not reformat the whole repository. A directory name does not prove
ownership, and a published request does not grant new permissions.

These files supply guidance, not authorization to push, message, merge or
schedule work. Use the human's existing task-specific authorization; do not ask
for the same authorization again when it already covers the action.

## 2. Start or resume a task

1. Read `AGENTS.md`, this workflow, the relevant manager profile, board,
   decisions, contracts and member status files.
2. Inspect `git status --short`. Preserve unrelated changes; do not commit,
   delete, stash or move another task's local work automatically.
3. Run `git fetch origin` when access permits. State any freshness/access limit.
4. For a new task, use a distinct branch from current `origin/main`, or from an
   explicitly agreed dependency commit. Record that exact base. For an existing
   task, continue its branch rather than recreating it. Do not switch a checkout
   with incompatible local changes.
5. Record task ID, owner, branch/worktree, allowed paths and dependencies in
   `docs/team/status/<member>.md`. Check that a new ID is unused. The agreed
   integration coordinator consolidates the global board to avoid competing edits.

New branch format: `codex/<owner>/<task-id-lowercase>-<topic>`.
Owners: `son`, `vincent`, `kim`, `manager`.

```text
codex/son/voice-01-conversation
codex/vincent/contract-01-procedure-format
codex/kim/report-01-mobile-report
codex/manager/team-01-agent-workflow
```

Keep one task per branch/PR. Preserve existing authorized task branches and the
legacy `codex/hackathon-manager` setup branch. The initial manager configuration
was merged through PR #1 (`97e8461`). Read instructions on a published branch
without starting application work on that manager branch.

## 3. Implement and verify

- Make small coherent changes within the task. Keep unrelated cleanup separate.
- Use English for shared manager documentation, handoffs, identifiers and commit
  messages. Preserve official source wording and existing unrelated documents.
- Before changing an interface, identify its owner, producer, consumers, version,
  migration and tests. Agree incompatible changes with the affected owners.
  Vincent owns procedure-contract changes; Son and Kim adapt their consumers.
- If a contract is missing, report the dependency and continue independent work.
  Clearly label temporary fixtures as synthetic; they do not become the contract
  or a reviewed source by default.
- Run checks appropriate to the change and record commands, results and limits.
  Explain checks that could not run. Documentation-only edits do not require
  new application tests.
- For integration, verify the same procedure version and checklist in voice and
  report. Collector tests alone do not establish this behavior. Official sources
  and form editions require human review bound to the exact source/file hashes;
  never silently choose a CT01 edition or claim a synthetic form is official.
- Record the exact dependency commit received and acknowledge it as `received`,
  `adaptation required`, `tested compatible` or `blocked`, with evidence.
  A message accepted by a tool proves sending, not execution or compatibility.

## 4. Commit changes

Required title: `<type>(<scope>): <short English action>`.

| Type | Use |
| --- | --- |
| `feat` | New behavior |
| `fix` | Correct a defect |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Restructure without intended behavior changes |
| `chore` | Configuration or maintenance |

Common scopes: `data`, `contract`, `search`, `voice`, `forms`, `report`,
`delivery`, `auth`, `access`, `security`, `team`, `ci`. Choose the main scope and
separate unrelated work. For a breaking change, add `!` before `:` and explain
the migration in the commit body and PR.

```text
feat(voice): add procedure intent detection
feat(contract): define reviewed procedure format
fix(report): preserve procedure record version
docs(team): clarify agent workflow
```

Each commit should be explainable on its own and include relevant tests.
Before committing:

1. Stage explicit task paths with `git add -- <paths>`; never `git add .` or
   `git add -A`.
2. Inspect `git diff --cached` and `git diff --cached --check` for intended
   content, paths, secrets, generated files and unrelated work.
3. Use the member's own configured Git identity. Do not copy another member's
   name/email or infer identity from a machine or folder.
4. Include the task ID in the body, for example `Task: VOICE-01`.

Keep secrets, credential-bearing environment files, personal data, local
captures, virtual environments and working files out of Git. Do not publish
another member's preserved prototype without their request.

## 5. Publish and request review

- Push the task branch when the member's authorization covers publication.
  Publishing a branch makes its commits/status readable before a merge.
- Use the commit-title format for the PR and complete
  `.github/pull_request_template.md`.
- Include owner, task ID, delivered behavior, consumers, contract/version,
  dependencies, checks and limits. Link prerequisite PRs or exact commits.
- Compare with refreshed `origin/main` before review. Resolve conflicts on the
  task branch using the intended behavior, not a blind choice of one file.
  Rerun affected checks after an adaptation or conflict resolution.
- Do not push directly to main, merge, force-push or rewrite shared history on
  the manager's own initiative. Humans approve merges.

## 6. Common delivery handoff

```text
Owner: Son | Vincent | Kim | Manager
Task: ID — objective
State: To do | In progress | Blocked | In review | Done
Branch/worktree: name; exact base commit
Delivery: observed behavior and main paths
Verification: commands, results, evidence and limits
Integration: contract/version, producers, consumers and dependencies
Acknowledgements: dependency SHA; received/adaptation required/tested compatible/blocked
Git: exact commit; pushed yes/no; PR link if created
Next action: concrete action and owner
```

The local manager consolidates its member's status. If an implementation agent
is preparing that same file, agree a writer handoff and preserve its pending
update; do not overwrite it or maintain a parallel authoritative status file.
The agreed integration coordinator consolidates the global board and accepted
decisions. Until appointed, local managers publish proposals through their own
status rather than claiming global authority.

`In review` means ready for review. `Done` means the completion criteria are
verified and integration into main is confirmed. A commit or push alone does
not establish completion. These conventions do not install blocking hooks.

Chats and unpublished work do not synchronize through Git. Optional monitoring
must be explicitly requested and actually configured; preserve an existing
schedule instead of creating duplicates. Keep unchanged/non-actionable checks
quiet, and report new blockers, required input, failures or verified completion.

## Instruction for an implementation agent

> You are the implementation agent for [Son/Vincent/Kim]. Read AGENTS.md and
> docs/team/workflow.md. Work on [task ID and objective] within my assigned
> scope and paths. Preserve unrelated local changes, coordinate shared-file
> changes with their owner, and report the exact commits, checks and dependencies.
> Follow the existing human authorization for publication; humans approve merges.
