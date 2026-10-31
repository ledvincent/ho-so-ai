# DEMO-INTEGRATION-01 UI checkpoint — work in progress

UI owner: Kim. Branch `codex/kim/demo-integration-01-live-retrieval`, checkout
`work/kim-demo-ui`, from reviewed `6ffec8e0270ff52bd27ceca9d4c4b57105c0cb54`.
The separate `work/kim-demo-integration` checkout belongs to the backend owner.
The existing profile preview on 3022/8022 is preserved.

Producer inspected: `e16279119281e0d1897f0259ec8f9366e091c90d`, including
`docs/kim-start-here.md`, checked-in OpenAPI/chat/document examples and API source.
The backend owner's draft browser contract is
`work/kim-demo-integration/docs/demo-integration-01-discovery-contract.md`.

This is an early source checkpoint, not a completed integration or jury deployment.
The UI parses signed clarification state/choices and document cards, avoids parallel
initial search that could bypass ambiguity, and reads the producer catalog through
the planned authenticated setup route. Installed document actions require explicit
procedure/document confirmation and bind document ID, original hash and template
version. The form engine accepts dynamic schema fields/conditions/fixed values and
pages; other documents never inherit NA5 field definitions or overlays.

TypeScript passed for the checkpoint. No production build, new browser acceptance,
live retrieval/model call, data restore or external-link acceptance has run here.
The new backend consumer commit has not been delivered or consumed yet.

Outstanding work at this checkpoint:

- Carry signed state/choices through in-form procedure Q&A as well as initial chat.
- Finish focused contract/race tests and production/browser verification after the
  exact backend delivery. Keep supporting documents/instructions and conditional
  applicability distinct from mandatory forms or legal approval.
- Explicitly coordinate profile compatibility: producer `template_version` starts
  `0ea995...`; existing profile mapping uses logical `schema_version` `50fe2f...`.
  These are different contracts. Live-document profile copying is deliberately
  withheld until the owner confirms the exact compatible binding; fixture copying
  retains its reviewed existing behavior. No hash bypass is implemented.
- Complete new VI/EN labels. Preserve original source/service text and entered values.
- Connect validation/preview through owner-delivered document routes, respecting
  draft/download locks and invalidating any preview on edit/account/document change.
- Runtime requires Vincent's separately supplied populated database/store/index;
  Git alone is not evidence of live retrieval. The root owns hosting and publication.

No handlers, backend auth/configuration, generated profile contracts, dependencies,
runtime databases, credentials or secrets were changed by this UI checkpoint.
