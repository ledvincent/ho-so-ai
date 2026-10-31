# Form workstream and agent handoff

## Current state

Work started on `feature/kim-form`. Kim has now confirmed Next.js/TypeScript/Tailwind, FastAPI/Pydantic, PostgreSQL and Clerk, and explicitly requested staying on this branch. The current `main` team/orchestrator guidance has been incorporated without choosing Vincent's procedure schema. See `shared-scaffold.md`, `application-contract.md` and `team/portal-handoff.md` for the application seams and the separate Clerk portal task. An official reviewed PDF template is still missing.

## Supplied scope

The overall flow is completed session -> accurate checklist -> mobile report -> filled PDF -> mocked phone delivery.

The three workstreams are:

1. Session summary and mobile checklist report.
2. Profile editing and form preview/download.
3. Delivery integration and end-to-end QA.

Session privacy, corrected answers, and preventing duplicate sends on retries are required checks. The delivery channel is undecided; use a mock sender until the team chooses it.

The [PII security and privacy design](security-and-privacy.md) proposes protections across the full flow, including storage, exports, logs, processors, and deletion. Use it alongside this scope when defining contracts; its controls and security checks are not implemented or verified yet.

## Ownership

Kim confirmed this split. Dot's active task is not visible here; relay the prompt below to align its work.

| Work | Owner | Boundary |
| --- | --- | --- |
| Profile editing, form preview and PDF download | Codex, on `feature/kim-form` | Own form implementation and related checks once the app location is known. |
| Interface review and acceptance review | Dot, initially read-only | Identify missing inputs and concrete failure cases; return findings to Kim. |
| Integration of accepted changes | Codex | Review the diff and run relevant checks in the form branch. |

If Dot implements a separate task later, assign it a separate worktree and branch, an explicit file list, and one deliverable. Keep shared app setup, dependencies, and contract changes with one owner at a time. Update the assignments here when they change.

## First form slice

The application scaffold now supports implementation of this slice; real upstream payloads and reviewed official templates still need to be supplied:

1. Load the selected session's profile and latest answers through a small adapter.
2. Allow the agreed profile fields to be edited, with agreed validation and save behavior.
3. Build the preview and PDF from the same current form data.
4. Regenerate or invalidate an existing export after edits so an old PDF is not presented as current.
5. Expose the resulting document to the delivery workstream through an agreed interface.

The adapter boundary and export invalidation behavior are proposals, not existing team contracts. Use explicitly synthetic fixtures while waiting for real sample formats; do not infer the external schema or official form fields.

## Acceptance checklist

These are planned checks; none has been executed against an application yet.

- [ ] Only the selected, authorized session's data appears in the editor, preview, and export.
- [ ] Corrected answers replace earlier values in the relevant checklist, report, preview, and PDF.
- [ ] Agreed editable fields validate and save according to the team's persistence rules.
- [ ] Missing values and integration errors are visible without invented answers.
- [ ] Preview and downloaded PDF represent the same revision of the form data.
- [ ] Editing after an export cannot silently download a stale document as the latest version.
- [ ] The preview works on the agreed phone viewport and the PDF preserves the required form layout.
- [ ] Changing sessions clears the previous session's editor, preview, and document state.
- [ ] End-to-end QA covers completion -> checklist -> mobile report -> PDF -> mock delivery.
- [ ] Delivery retries produce the agreed number of logical sends without duplicates; owned by delivery/E2E.
- [ ] Applicable SEC-01 through SEC-10 checks in the security design have recorded evidence before handling real PII; scope and ownership are agreed across workstreams.

## Inputs to resolve

| Source | Needed input | Purpose |
| --- | --- | --- |
| Resolved by Kim | Next.js/TypeScript/Tailwind in `web/`, FastAPI/Pydantic in `api/`, PostgreSQL and Clerk | Shared dependencies and application contracts are in the scaffold; live credentials and persistence remain separate work. |
| Vincent | Representative completed-session payload, stable session identifier, completion signal, and correction/revision behavior | Read the right session and use current answers. |
| Son | Representative procedure response, procedure/version identity, checklist rules, and form-field mapping if available | Produce the intended checklist and form content. |
| Team | Official PDF template, editable fields, validation, language, and missing-value rules | Implement accurate preview and PDF filling. |
| Team | Profile persistence and session access rules | Define save behavior and verify session privacy. |
| Team/data owner | Actual PII inventory, hosting/processor regions, retention/deletion rules, and security ownership; see the security design | Translate the proposed protections into concrete implementation and acceptance checks. |
| Delivery owner | Document handoff format and mock delivery/retry expectations | Connect the export without selecting a real phone channel. |

## Prompt for Dot now

```text
We are coordinating on ho-so-ai. Codex owns profile editing, form preview,
and PDF download on feature/kim-form.

Your task for now is read-only review. Read AGENTS.md and
docs/form-workstream.md if you can access this checkout; otherwise ask me
to paste them. If you have already started editing, first report your
branch, folder, changed files, and current task so we can reconcile ownership.

Review the proposed form scope and list missing integration inputs and
specific acceptance cases for corrected answers, session privacy, and
preview/PDF consistency. Label assumptions. Do not edit files, switch
branches, or choose the app stack or external payload schema.

Return a short handoff: findings, proposed changes, and questions for Kim.
```

## Prompt for a future parallel implementation task

Replace all placeholders before assigning the task.

```text
Task: <one bounded deliverable>.
Worktree folder: <separate absolute path>.
Branch and base commit: <branch> from <agreed commit>.
Read AGENTS.md and docs/form-workstream.md.
You own only: <specific files or directories>.
Inputs/contracts: <agreed samples and interface versions>.
Acceptance: <observable behavior and relevant checks>.

Implement and verify the task in your worktree. Preserve other work.
If a shared contract, dependency, or file outside your ownership must
change, return the proposed change to Kim before editing that shared area.
Hand off the diff or commit, changed files, exact checks and results,
and unresolved issues. Codex will integrate the accepted changes.
```

## Verification and handoff

Current delivery: a runnable, dependency-free synthetic forms prototype in `prototypes/forms/`, in addition to coordination guidance.

- Implemented: synthetic profile editing, immutable preview snapshots, corrections, acknowledgement, session/load isolation, export invalidation and JSON review-copy download.
- Verified on 31 October 2026: 14 offline Node state tests and 9 local Edge/Playwright browser checks, including mobile layout, downloaded-content consistency and stale export rejection.
- Run: `node --test prototypes/forms/state.test.mjs`, then `node prototypes/forms/serve.mjs`; open `http://127.0.0.1:4173`.
- This is a prototype with synthetic text fields and a mocked JSON renderer. Official PDF rendering, authentication, backend authorization, persistence, real session/procedure adapters and delivery remain unimplemented.
- Client-side session isolation does not establish authorization. The adapter contract is provisional; the team still owns the external schema and save/correction semantics.
- User portal scope was added by Kim. Managed authentication and application/database boundaries are proposals pending team agreement; no production auth or database choice is committed by this prototype.
- Codex remains the implementation owner. An independent Codex review found no remaining actionable prototype issue; this was not Dot, whose separate review handoff remains unconfirmed.

Coordination reference: [OpenAI documentation on Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).
