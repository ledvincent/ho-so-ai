# Published member status

| Member | File | Update owner |
| --- | --- | --- |
| Son | [son.md](son.md) | Son and Son's local manager |
| Vincent | [vincent.md](vincent.md) | Vincent and Vincent's local manager |
| Kim | [kim.md](kim.md) | Kim and Kim's local manager |

Each local manager consolidates its member's status. Use one coordinated writer
at a time: if an implementation agent is preparing a status update, agree a
handoff and preserve its pending changes. Do not rewrite another member's file
or create a parallel authoritative status record.

The initially unfilled files do not mean their owners have not started. Update
the existing file on the task branch and publish it when human authorization
covers the push. A branch can be read before it is merged; main contains only
merged status, while task branches may describe newer or parallel work.

## Common handoff fields

Use English for new manager handoffs, preserving previous useful evidence and
history. Existing French field labels may be migrated by their owner when they
next update the file; another manager must not rewrite them just for formatting.

```text
Owner:
Updated: date/time and timezone
Task/state:
Branch/worktree/base commit:
Delivery: behavior and affected paths
Verification: commands, results, evidence and limits
Git: exact code commit; pushed yes/no; PR link if created
Integration into main: yes/no/unverified, with evidence
Contracts: owner, version, producer and consumers
Dependencies received: owner, branch/SHA, acknowledgement and evidence
Requests to others: owner, required deliverable/version, reason and next action
Blockers:
Next action: concrete action and owner
```

For every received dependency, explicitly use one acknowledgement:

| Acknowledgement | Meaning |
| --- | --- |
| `received` | The exact referenced delivery is available and inspected; compatibility is not yet established |
| `adaptation required` | Name the interface mismatch, affected paths, responsible owner and proposed adaptation |
| `tested compatible` | Record the exact producer/consumer commits and successful integration checks, including their limits |
| `blocked` | Name the missing input or failing check, its impact and the next action/owner |

Separate observed facts from another member's reported results. A status label
does not prove a test or merge. A message accepted by an API is sent; an explicit
reply or committed handoff can acknowledge it. Neither alone proves successful
integration. Silence is not agreement and a branch's date does not make it the
only active line of work.

Read commits, diffs and accessible PRs using the
[manager protocol](../managers/protocol.md). Keep authoritative contracts in
their owner-maintained locations; link them rather than copying a second schema.
Never include secrets, tokens, private chat IDs or personal data in shared status.

Member status updates replace repeated edits to the global board. The explicitly
agreed integration coordinator consolidates changes to priorities, ownership,
accepted decisions and integration order in a dedicated review. Until appointed,
local managers publish proposals in their own status and continue independent
work. Git publication does not synchronize private chat histories.

These files do not create agents, install monitoring or authorize publication.
If monitoring is explicitly configured, preserve its agreed scope/cadence and
avoid duplicate schedules. Routine unchanged checks should remain quiet.
