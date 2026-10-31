# One local manager per team member

Son, Vincent and Kim each use a manager chat attached to their own repository
checkout. All three follow the [shared protocol](protocol.md) and the same
[start prompt](start-prompt.md). Select the member explicitly; do not infer it
from a computer name, Git author or directory owner.

| Member | Prompt substitution | Profile | Status file owned by that member |
| --- | --- | --- | --- |
| Son | `[MEMBER]` = `Son` | [son.md](son.md) | [son.md](../status/son.md) |
| Vincent | `[MEMBER]` = `Vincent` | [vincent.md](vincent.md) | [vincent.md](../status/vincent.md) |
| Kim | `[MEMBER]` = `Kim` | [kim.md](kim.md) | [kim.md](../status/kim.md) |

## Activate a manager

1. Open a chat on the member's existing checkout. Preserve its current branch
   and uncommitted work; do not switch an application branch to load guidance.
2. Read the current published guidance. Before a documentation change is merged,
   use `git show <published-ref>:docs/team/managers/protocol.md` after fetching.
   Record the exact reference used and any unavailable files.
3. Copy the common prompt, replace its member placeholders, and review its bounded permission
   paragraph before sending it as a human instruction in that chat.
4. The manager establishes current owners, branches, evidence and next actions.
   It coordinates existing work before proposing new implementation.

Reading these files alone does not activate a manager, authorize messages or
pushes, create another person's chat, or install a monitor. Human instructions
and existing authorizations govern actions; the prompt grants its stated scope
only when the person actually sends it.

## Shared coordination

Each local manager coordinates its member's implementation chats and maintains
only that member's status file. Contract owners retain their interfaces. One
explicitly designated integration coordinator consolidates the global board,
shared decisions, dependency order and combined verification.

If no designation is already recorded with evidence, propose Kim's manager for
that role and record it as pending Son's and Vincent's agreement. The proposal
does not give Kim's manager authority over their work. Continue independent
local tasks while agreement or an interface delivery is pending.

Use English for shared manager guidance, status updates and handoffs. Preserve
official Vietnamese source wording and form content; do not translate legal
requirements as part of a manager-documentation update.

## What managers can observe

Git branches, commits, contracts and [member status files](../status/README.md)
are the shared record. A pushed task branch is readable before merging into
main. Unpublished work on another computer remains invisible through Git.
Chats do not synchronize automatically across accounts or computers.

Where local chat tools are available and human-authorized, a manager can inspect
and message relevant local chats. Report tool limitations and distinguish a
message accepted for delivery from an acknowledgement or completed change.

Periodic checks require an explicitly requested, actually configured monitor.
Reuse a suitable existing monitor; do not create duplicates. Report only
meaningful changes, completion, failure or required action unless the user asks
for periodic summaries. These files install no monitoring on any machine.
