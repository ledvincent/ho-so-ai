# DEMO-GUIDE-01: readable bilingual guide and English form flow

Checkout: `work/kim-procedure-guide-ui`; branch
`codex/kim/demo-integration-01-readable-guide`, based on reviewed `8c8743e`.
The source-copy delivery `1779a7e89eea982a24d4fc6d6c285539763c75c5` is consumed as
`c533ec9`. Original data JSON/hash and audit script are unchanged.

The source-bound guide is shown immediately after procedure inspection. It uses
the actual source SHA and exact procedure code; changed snapshots receive an
explicit unavailable-translation message instead of silently reusing old content.
All four procedures have English/Vietnamese names, document lists with quantities
and alternatives, separate online submission instructions, numbered steps and
visible conditions. Conditional family-relationship proof remains in the visible
conditions for the three applicable procedures. No extra copy count is invented.

In particular, `1.000771` has three document items, a separate online/postal
instruction, three steps and its conditions. It remains useful without an editor.
Source originals, hashes/timestamps, form metadata and lengthy conflict analysis
are in collapsed disclosures. One concise applicability/edition notice remains
visible. The original Vietnamese source sections are retained, not replaced by
the display translation. Chat remains available with compact procedure selection.

Only the actually installed provincial NA5 workflow gets a visible **Fill this
form** action. The click confirms the current exact procedure/document action and
loads its checked schema/pages. Other procedures never borrow provincial NA5.
Profile consent, field ownership, canonical draft, manual correction, undo,
validation/preview invalidation and draft/download gates remain unchanged.

Form guidance uses authored bilingual prompts based on validated field IDs and the
actual missing fields. English input still uses the existing field-assistant API;
no locale or new field values enter RAG. The original service reply is available
in an optional disclosure, including clarification detail. Completion is based on
the checked draft's remaining required fields, not a null service next-field alone.
Manual field labels and the primary fill action respect the selected UI locale.

Checks before the final completion-label correction: all 207 frontend tests passed,
including six new guide/locale/source-binding tests, and production build passed.
The final committed checkout is rebuilt and focused tests rerun before handoff;
the final chat handoff provides its exact clean SHA, build ID and observed result.
No runtime service, shared browser login, paid request or deployment is performed
by this UI task. Root owns restart and actual HTTPS/English-answer acceptance.

Relevant files: procedure-chat `guide-projection`, `dossier`, `chat`, `api`,
`document-cards`, `model` and scoped CSS; guided-portal `workbench` and `document`;
the authored English dictionary and `guide-projection.test.ts`. Shared backend
handlers, API DTOs, auth/configuration, dependencies and generated types are intact.
