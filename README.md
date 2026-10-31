# ho-so-ai

Voice-guided Vietnamese administrative procedures, with an official-source checklist
and a mobile report after the conversation. Initial recommended scope: temporary
residence registration and renewal; see `docs/scope-and-ingestion.md`.

## Team coordination

Son owns search and voice; Vincent owns official sources, structured data and
validation; Kim owns forms, the mobile report and delivery. See
[`AGENTS.md`](AGENTS.md), the [manager guide](docs/team/manager.md),
[task board](docs/team/board.md), [shared contracts](docs/team/contracts.md)
and [decisions](docs/team/decisions.md). The manager advises and prepares fixes;
humans approve merges.

Each member can start a personal manager using the
[local manager setup](docs/team/managers/README.md) and the
[common English prompt](docs/team/managers/start-prompt.md). The three managers share
repository evidence and [per-member progress files](docs/team/status/README.md),
not private chat histories. Each manager coordinates its own member's agents;
an explicitly agreed integration coordinator consolidates shared dependencies
and verification. A local appointment does not establish team-wide authority.

Kim owns application login, the personal dossier and approval UI. Son owns
conversation sessions and the agent authorization server. See the
[identity and security plan](docs/team/identity-and-security.md) for boundaries
and demo evidence to produce; controls are not yet verified.

All agents follow the [common workflow](docs/team/workflow.md) for branches,
commits, reviews and handoffs. Each member can copy the agent instruction at
the end of that document.

## Data collection

Vincent owns collection, its tests and the shared data contract. The manager
configuration does not ship a collector or impose a data schema. Son and Kim
will integrate against the contract Vincent delivers.
