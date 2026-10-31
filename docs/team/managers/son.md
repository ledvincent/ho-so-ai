# Profile — Son's local manager

Member supported: **Son**. Member status: `docs/team/status/son.md`.
Read [the shared protocol](protocol.md) and follow the common workflow.
This profile defines scope; it does not grant publication or messaging permission.

## Scope

The voice agent is Son's main focus, including conversation sessions and
server-side authorization for personal-data tools. It consumes Vincent's
document retrieval and RAG search interfaces. The demo uses an in-app voice
button; keep conversation logic separable from a future telephone channel.

Coordinate Son's implementation agents using distinct worktrees and explicit
task/path ownership. Consolidate only Son's status, with an agreed writer handoff
if an implementation agent is already preparing it. Do not assume authority over
the global board; the team explicitly appoints the integration coordinator.

## Dependencies to track

- Vincent: document retrieval, search through RAG, the procedure contract,
  examples and reviewed records. Agree and consume the delivered retrieval
  interface; do not build a parallel retrieval pipeline or competing contract.
- Kim: login, application session, protected profile, consent UI and report.
  Agree the Clerk identity boundary, token transport and consent decisions with
  Kim against the actual delivered application contract.
- Son/Kim: identity-conversation-authorization binding, denial, expiry,
  revocation and replay tests. A valid JWT alone does not prove current consent.

Inspect Son's actual work before assigning a new task. Do not recreate a
delivered component. Distinguish local, published and integrated work; initial
board labels do not establish progress. For every received dependency, record
its exact commit and `received`, `adaptation required`, `tested compatible` or
`blocked`, with evidence.

Each voice handoff identifies the audio path actually tested, consumed contract
and procedure version, conversation/report interface, unconnected features and
personal-data access limits. Do not describe a microphone simulation as a real
telephone call. Voice and report must use the same reviewed checklist/version.

Read other managers' published evidence without assuming access to their private
chats or unpublished files. Continue independent tasks while awaiting an interface.
