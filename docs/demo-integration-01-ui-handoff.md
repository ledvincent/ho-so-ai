# DEMO-INTEGRATION-01: combined UI delivery

Browser-ready source: `9202cbb0b676a48c1eb5909eafc67aca3f73d80e` on
`codex/kim/demo-integration-01-live-retrieval`, checkout `work/kim-demo-ui`.
This follows UI checkpoints `1e56854` and `1eb710c`; backend owner deliveries
`1ad7db19140647764ce8705998d92ac53e8a736d` and
`cee62535a221414536924a5f259d6225446dbd22` were consumed as `8fbaac4` and
`119a0e7`. No main merge, push, service launch, credential provisioning or Sites
change was made by this integration delivery. Existing 3022/8022 remains intact.

## Implemented behavior

- General chat preserves returned signed state, choices, procedure code, citations
  and sourced document cards. A choice sends its exact state/ID and omits the
  procedure code. Initial flat search cannot bypass clarification. In-form Q&A
  has its own public conversation/state and never adds profile/form values to RAG
  history or applies a procedure answer as form data.
- The actual setup catalog is available without a model request. Readiness and
  returned records are displayed independently; records are not hard-coded as
  live. Inspection and explicit procedure/document confirmation precede filling.
- Supporting documents, conditional evidence and submission instructions remain
  distinct. Partial answers can retain useful cards without claiming complete
  legal context or approving a form edition.
- Document actions use exact protected BFF paths. Schema, original hash, template
  version, document ID, procedure, fields, flags, conditions, fixed values, dates
  and page count are checked. Other documents use their own pages/manual fields;
  they do not inherit NA5 overlays or the legacy assistant mapping.
- The exact public e162 NA5 schema is compared before enabling profile proposals
  and the legacy CHAT-01 field assistant. Profile requests send the owner-approved
  `0ea995...` document version. CHAT-01 keeps logical version `50fe2f...`. Other
  documents and editions remain manual. Explicit applicant consent, passport
  confirmation, profile revision recheck, typed-field locks, atomic apply and undo
  remain in place. Profile copy does not save the profile.
- Server validation uses the full normalized snapshot/current template version;
  returned mutations are rejected. Preview pages require the exact version and
  protected review header. Value-bearing tokens are discarded because final
  download stays locked for this draft/unresolved edition. Edits, undo, account,
  document or revision changes invalidate the preview and acknowledgment.
- New authored controls/errors are available in VI/EN. Source wording, service
  answers, identifiers, citations and entered values remain unchanged.

## Checks observed in this checkout

| Check | Result |
| --- | --- |
| Focused UI/document/profile/locale tests | 20 passed |
| All frontend components/lib tests | 200 passed |
| `node web/node_modules/typescript/bin/tsc --noEmit -p web/tsconfig.json` | Passed |
| `node node_modules/next/dist/bin/next build --webpack` from `web` | Passed |
| `git diff --check` | Passed |
| Live model calls from this UI workstream | 0 |
| New browser/HTTPS acceptance in this UI workstream | Not run yet |

Tests use public checked-in producer examples and fictional transports. They cover
state/choice preservation, session changes during 409/503, exact NA5 compatibility,
a different small optional/conditional/manual/uppercase schema, dynamic pages,
whole-snapshot validation, unexpected response mutations and review-header gates.
They do not prove live retrieval quality, external TLS/session behavior or legal
approval. Backend-owner test evidence is in `demo-integration-01-handoff.md`.

## Root runtime handoff

The root owns the existing jury DB/credentials, Vincent 8001, Next 3030/API 8030,
the HTTPS tunnel and the remaining shared live model budget. Do not provision
another jury database or run competing logins. The combined checkout has a built
`web/.next`; invoke the owner launcher against this checkout as documented in the
backend handoff. Dependency junctions point to the existing integration install;
do not run a package install against them.

Suggested actual-browser acceptance: login -> browse actual catalog or one
allocated question -> inspect 1.001146 -> select installed NA5 -> confirm draft ->
opt into profile proposals (or skip) -> apply/edit/undo the same draft -> review
and server validation/preview -> edit and confirm preview invalidation -> in-form
procedure Q&A without field mutation -> VI/EN preservation -> logout/account
isolation. Blank/partial validation should show missing fields; complete fictional
values can render a draft, while download must remain locked.

No external HTTPS/browser or live runtime result is claimed by this source handoff.
