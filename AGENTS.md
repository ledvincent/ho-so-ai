# Working together

- Read `docs/form-workstream.md` before starting form work. It records the current scope, open inputs, and ownership.
- Check the current branch and working-tree changes before editing. Preserve other contributors' work.
- Use one implementation owner per task and file. If another agent is implementing concurrently, use a separate Git worktree and branch with explicit ownership. Separate branches in the same folder do not isolate file edits.
- Kim confirmed the split: Codex implements the form; Dot reviews interfaces and acceptance checks read-only. Relay this assignment to Dot before relying on it; Dot's active task is not visible here.
- Coordinate changes to shared contracts, dependencies, and app configuration through the implementation owner.
- Mark provisional payloads and mock behavior clearly. Do not present unverified integration or test results as working.
- End a task with changed files, checks and their results, unresolved inputs, and the next handoff.
