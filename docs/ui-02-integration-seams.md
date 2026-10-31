# UI-02 owner integration seam

Base preserved: `b4a3ebf2d208ad4533b2a50f69aec9462626145c`.
Branch: `codex/kim/ui-02-guided-portal`, sole frontend owner.

AUTH-02/CHAT-01 draft contract was forwarded by the manager and inspected:
`feac4cf36bc8dd6367924712d790f85f81bb48bfe8636e3523dc25bc3e71a906`.
The committed implementation delivery is still pending. Consumer mapping is
prepared in `a05471c`: exact `/api/auth/*`, `/api/chat/schema` and
`/api/chat/assist` routes, request identity/revision checks, validated proposals,
schema version pinning and session checks before/after replies. Twelve focused
consumer/NA5 tests and typecheck pass without network/provider calls.

No new auth/API handler, database implementation or competing wire schema has
been implemented here. `GuidedAdapter` remains an internal component view model;
`api.ts` maps the exact producer contract. It is not attached to the primary
route until the manager's verified implementation commit arrives.

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

Pending implementation handoff: server guard/helper, account fixtures, process
ownership/configuration and final exact code SHA. Primary login UI is prepared
at `/`; it is disabled and explicitly labeled until this delivery is consumed.
Initial UI guidance is deterministic. No model call is made on mount, focus,
retry or manual correction. Reserve at most one fictional live browser call.

No shared root auth layout, proxy, application contract, generated profile types,
manifests or lockfiles were edited independently. Manager remains sole writer
of `docs/team/status/kim.md`. No team/main merge, push or deployment.
