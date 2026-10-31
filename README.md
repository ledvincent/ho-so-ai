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

## Data collection

Vincent owns collection, its tests and the shared data contract. The manager
configuration does not ship a collector or impose a data schema. Son and Kim
will integrate against the contract Vincent delivers.
