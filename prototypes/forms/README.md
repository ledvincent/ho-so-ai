# Synthetic forms prototype

First executable forms slice on `feature/kim-form`. No framework or external package is required. Requires Node.js 20 or newer.

```sh
node --test prototypes/forms/state.test.mjs
node prototypes/forms/serve.mjs
```

Open http://127.0.0.1:4173. Try editing, checking the preview, preparing/downloading a review copy, applying a correction, and switching sessions while an export is pending. On phones, use the browser's responsive viewport; this development server binds to loopback only.

The demo uses synthetic text fields and downloads **JSON**, not an official PDF. It has no authentication, authorization, persistence, live session API, delivery, or LLM calls. Do not enter real PII. Its state isolation does not establish backend authorization.

## Implemented behavior

- Session selection clears all previous editor, preview and export state immediately.
- Load tokens reject stale responses, including A -> B -> A and repeated loads of the same session.
- Replacing current answers replaces the complete field map; explicit clears and omitted fields do not restore old values.
- Text validation preserves invalid values for correction; it never truncates them.
- Edits, corrections and template/mapping version changes invalidate exports and acknowledgement.
- An export adapter receives the immutable checked preview snapshot. Its result attaches only if its token remains current.
- Input and output snapshots cannot mutate current state behind revision tracking.
- Visible load/export failure states allow retry without carrying previous session data forward.

## Provisional adapter contract

`state.mjs` is a browser-compatible ES module with an internal API, not an agreed external session schema.

1. Call `beginLoad(sessionId)` before each session load/reload, then `finishLoad(token, values)` or `failLoad(token)`. The real adapter must authorize access and resolve the latest corrected answers before supplying a map of configured text fields. Request order alone cannot establish the semantic order of upstream corrections.
2. `replaceAnswers(values)` treats the supplied map as the complete current answer set. This prototype replaces local edits on correction; the team's save/conflict policy is still unresolved.
3. Read `snapshot()` for the preview; call `confirmValues()` after the user checks it. This is user acknowledgement, not official template approval.
4. Call `beginExport()`, pass its immutable snapshot to a renderer, then `finishExport(token, { blob, filename })` or `failExport(token)`. Use `document()` only for the current download.
5. Bind `setTemplateVersion(version)` to both source-template and mapping versions once those inputs exist. A real PDF adapter must enforce reviewed-template rules server-side.

The team still needs to agree field/schema types, session access, persistence, source revision behavior, official templates, PDF coordinates and review policy. The test artifacts are mocks and establish lifecycle behavior only; they do not verify PDF layout or production privacy.

No application manifests, shared contracts, dependency locks or database schema are changed by this prototype.
