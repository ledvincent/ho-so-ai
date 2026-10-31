# UI-02 owner integration seam

Base preserved: `b4a3ebf2d208ad4533b2a50f69aec9462626145c`.
Branch: `codex/kim/ui-02-guided-portal`, sole frontend owner.

AUTH-02/CHAT-01 exact delivered commit and contract are pending from the manager.
No new auth/API handler, database implementation or competing wire schema has
been implemented here. The `GuidedAdapter` type is a provisional component
view-model boundary, not a proposed API response format. It will be mapped to
the scaffold's actual response and replaced where needed.

Prepared UI paths: `web/components/guided-portal/**`; compact document above
conversation, bottom composer, optional manual editing, visible changes and
single-operation undo. One canonical in-memory NA5 draft; model response/edit
revision invalidates review and acknowledgment. Abort + generation/revision
checks discard replies after edits, navigation or logout. No implicit profile
save. All template input bytes remain unchanged.

Scoped shared presentation change: `web/components/ui/site-shell.tsx` removes
global internal navigation/chrome. It does not authorize any page or API. The
authenticated workbench owns its small navigation header. AUTH-02 must supply
server protection for direct `/workspace`, `/portal`, `/research` and document
routes/APIs before these are described as private.

`PortalLogin` is prepared with an injected authentication callback; no password
handler or identity scheme is attached. The separate `/demo/*` visual preview
remains labeled synthetic/provisional and cannot establish real authentication.
It must not be the primary path after AUTH-02 is consumed.

Pending exact producer contract: login/session/logout paths and errors, server
session guard/helper, cookie semantics and session discriminator, guided-turn
request/response/statuses, validated draft changes, startup question behavior,
provider configuration and isolated local database initialization instructions.

No shared root auth layout, proxy, application contract, generated profile types,
manifests or lockfiles were edited independently. Manager remains sole writer
of `docs/team/status/kim.md`. No team/main merge, push or deployment.
