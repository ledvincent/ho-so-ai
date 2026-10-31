# DEMO-INTEGRATION-01: runtime inventory and acceptance gates

Read-only review of producer `e16279119281e0d1897f0259ec8f9366e091c90d`
in `work/vincent-runtime-e162`, against the consumer in `work/kim-demo-integration`.
This review did not start a server/database, restore data, run ingestion, rebuild
an index, read credentials, or call a network/model endpoint. No live-readiness
or legal-review result is established by this document.

## Data/runtime inventory

| Dependency | Observation in the allowed review roots | Consequence |
| --- | --- | --- |
| `handoff/procedure-db.dump` | Absent from the producer checkout; no runtime dump/bundle located in the inspected Hackathon workspace paths | Source and migrations alone cannot reproduce the populated catalog, published RAG release, source IDs or scoped reviews |
| `data/_store/` | Absent from the producer checkout | Obtain the matching public-data snapshot before claiming full evidence availability |
| `data/archive/raw/` | Present, five files including its manifest | Do not describe this checked-out directory as absent; verify the supplied snapshot's exact matching contents before restore |
| `data/forms/` and registry | Checked-in definitions exist; NA5's referenced PDF exists | Retain these exact source-version files; do not replace them with an old bundle's code/schema |
| PostgreSQL/RAG runtime | Not inspected or started by this review | Restore only into an explicitly new isolated database; do not overwrite Vincent's existing database or rebuild ingestion/RAG |
| BGE-M3 weights/runtime | Not verified | The delivered release expects digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`; matching tag name alone is insufficient |
| Assistant configuration/signing secrets | No private values inspected | Root supplies authorized secrets only to private process memory/local tooling; preserve consistent RAG/form signing secrets across the demo processes |

The bundle search stayed within the producer/Hackathon directories, excluding
installed dependencies and Git internals. Some unrelated sandbox-owned test-cache
directories were unreadable. This is a scoped inventory, not a claim about files
elsewhere on the computer. The only matching archives found were unrelated logo
deliverables and an earlier source-baseline tar.

Producer setup references are `docs/kim-start-here.md`, `docs/rag.md`,
`docs/evidence-access.md` and `docs/contracts/`. Their examples include paid smoke
and rebuild commands; those are not automatically authorized by reading the guide.
No such command was run by this review.

Root should record the dump/store provenance and exact source commit before a
fresh isolated restore, then verify migration head `0009`, catalog rows, serving
release, model digest and evidence-file availability. `/health` checks the process
only. `/assistant/setup` is the read-only setup boundary. `/search` may invoke
embeddings and must not become an automatic health check. No-matches, degraded
search and unavailable retrieval remain different outcomes.

## Producer contract changes that the consumer must preserve

- Chat now accepts `retrieval_state` and `clarification_answer`, and returns
  `choices`, `retrieval_state`, selected `procedure_code` and `documents` alongside
  answer/citations/status/model. Preserve opaque state and offered choice IDs;
  conversation history alone is not procedure selection. A fresh intent drops
  the old state; stale/expired state must remain an explicit error.
- A partial `insufficient_context` answer may still have useful cited document
  cards. Do not discard cards solely because status is not `answered`, and do not
  promote `unconfirmed` or `conditional` requirements to universally required.
- Source-attributed evidence access can be authorized by an exact scoped review
  while legacy `facts_ready` is false. Scoped evidence review is distinct from
  current-law verification, accepted form applicability and template approval.
  Do not use the earlier facts flag as a global replacement for producer readiness.
- The producer model timeout is 120 seconds; its guide requests at least
  180 seconds for the chat transport. The old 65-second chat deadline is incompatible
  with that runtime. Keep bounded response reads and no automatic retries.
- Installed document discovery uses `/procedures/{code}/documents` and
  `/documents/{document_id}/{action}`. A card without an installed form has
  `form: null`. Do not invent an editor, universal field list, NA5 default or
  document association from the prose or form filename.
- Form schemas carry `document_id`, procedure/form identity, template version,
  original hash, page count, fields, fixed values and date order. Honour `when`,
  `manual`, `inactive`, `hidden`, `uppercase` and applicable field types. The first
  installed document happens to have 43 fields; generic transport must not require
  that count for every document.

## Exact NA5 version dimensions

| Identifier | Observed value / meaning |
| --- | --- |
| Original file SHA-256 | `a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751` |
| Earlier Kim workflow bytes | `50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3` |
| e162 workflow file bytes | `ddb9c985573e0245d0c52588b0c74685c613a9a0aef668a2416da92697a3115c` |
| e162 document template version in checked-in contract | `0ea9956659b50098c275e687533954cfa68f1541eab40ad167cf8627def4014b` |
| Document ID | `na5-provincial-stay-extension` |
| Revision / current gate | `70/2026/TT-BCA`, `review_status: draft`, `applicability: unresolved`, `download_available: false` |

The original is unchanged, but the workflow definitions are not byte-identical:
both have 43 fields and the same fixed values; e162 adds explicit uppercase
metadata to `applicant_full_name` and a `date_order` list. The document template
version additionally binds installed document identity and the mapping. These
hashes are not interchangeable.

Existing CHAT-01/PROFILE-01 pins remain unchanged. A new document schema must not
be silently presented as compatible with the earlier prefill contract. Either keep
that prefill unavailable for the new version or deliver an explicitly reviewed
compatibility bridge that preserves both version dimensions and stale-context
checks. Generic document display does not itself authorize old-schema prefill.

The checked-in `data/forms/NA5/review.json` still says awaiting human review.
Previewing fictional data does not approve it. Final official download must keep
the producer's 409 gate until a human-approved exact version is delivered.

## Required request/data protections

1. Public traffic reaches only the authenticated Next origin. The application
   API and Vincent server stay on private loopback listeners; no tunnel routes
   directly to either API. The new launcher must fail on occupied ports and
   disable trusted-forwarded-client headers for the private application API.
2. Hosted mode uses the exact configured HTTPS origin, host-only Secure/HttpOnly/
   SameSite cookies, strict mutation Origin/JSON checks and live session/owner
   validation. `HOSO_LOCAL_DEMO_SEED=false` prevents new weak seeding, but does not
   remove weak users from a previously seeded SQLite file: first provisioning must
   use a fresh dedicated database and nondefault fictional jury accounts, or
   otherwise reject that unsafe existing state.
3. Preserve independent A/B profile ownership and v1/v2 CAS behavior. Do not send
   a browser-asserted owner, session cookie, portal Bearer token, profile object or
   saved form values to Vincent's chat/RAG. Free-text procedure conversation and
   personal form preparation are separate data flows.
4. Rewrite only exact, validated server-owned document action paths under the
   authenticated consumer prefix. Never fetch a URL taken directly from prose,
   a citation, a browser selector or an arbitrary upstream field. Recheck document/
   procedure association and identity/version metadata on relevant actions.
5. Require a current `template_version` on consumer form POSTs even though the
   producer permits omission for older callers. Validation sends the complete
   current field map, not a patch. Partial validation and complete preview are
   different operations; never fabricate missing values to enable preview.
6. Preview/download tokens are signed, not encrypted, and contain normalized
   applicant values. Keep them out of URLs, logs, chat/history, model prompts and
   persistent browser storage. Forward `X-Review-Token` only on the authenticated
   private response. Changing values, account, document or version invalidates the
   pending preview/token. Never reuse a token for another installed document.
7. Preserve PDF/PNG media types, page numbering, bounded payloads and private
   no-store responses. Sanitize upstream error strings rather than treating them
   as stable codes or displaying raw exceptions. A document download or valid
   byte hash does not establish legal applicability or source currency.

## Focused acceptance scenarios

These are pending checks, not passed results from this review:

- Missing dump/store/index/model configuration fails explicitly; the launcher
  neither runs ingestion nor publishes a rebuilt index or a fake successful state.
- Hosted HTTPS origin succeeds; HTTP/public-origin mismatches, weak seeding,
  unauthenticated APIs, foreign Origin and non-loopback API peers fail closed.
  A/B profiles remain isolated; logout revokes the old token and clears the UI.
- Mock chat clarification retains state and only offered choice IDs, with no
  default procedure. Partial answers retain safe cited cards. Unsupported IDs,
  malicious action URLs, redirects and cross-procedure associations are rejected.
- Schema/template/validate/preview all retain document identity and version.
  Missing/stale versions, unknown fields, nonempty inapplicable/manual/inactive
  fields, conflicting fixed values and invalid date order fail. Producer-defined
  normalization, including uppercase and fixed defaults, remains explicit.
- Preview requires complete applicable fictional values, returns the exact rendered
  PDF/pages and a private token; it does not write a profile or send values to RAG.
  Edits/account changes reject late previews. Draft final download remains 409;
  a changed value/version/document cannot reuse a prior token.
- The hosted form UI does not apply old pinned prefill against a changed schema
  by substituting hashes. Any explicit compatibility bridge has its own evidence.
- Only root-allocated model smoke calls run, with fictional/general text and no
  automatic retry. This review used zero calls. Keep the shared count in the root
  ledger; do not infer readiness or paid-call permission from a source fixture.

## Hosted-auth source review checkpoint

The source review additionally checked the new hosted-mode wiring, shared cookie
policy, provisioning script and private API launcher. Hosted mode remains an
explicit opt-in: the API retains its loopback peer boundary and exact public
HTTPS Origin checks; Next uses Secure, HttpOnly, host-only, SameSite=Lax cookies.
The provisioner requires an absolute new SQLite path, two distinct nondefault
usernames and either masked local input or an exclusive restricted credential
file. The private API launcher rejects databases containing the earlier known
weak-demo usernames and disables forwarded-header trust. Using these delivered
scripts addresses the weak reused-database condition described above.

This is a bounded source review, not proof of TLS, tunnel behavior, deployed
account state, logout revocation or A/B isolation. Those checks remain pending in
the root-owned runtime acceptance. The transport and handler were still being
updated when this report was written; record their final verified source version
and actual runtime results in the handoff.
