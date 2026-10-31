# ACCESS-01 — isolated app.v1 profile reader

Owner: Son
Task: ACCESS-01 — server-side personal-tool authorization and profile consumer
State: In progress; isolated read adapter verified, voice/production integration pending
Branch: `codex/son/access-01-tool-authorization`
Worktree: `C:/Users/Son/.codex/worktrees/access-01-authorization/ho-so-ai`
Base/HEAD: `60cb3be26e928cbef71cb636b8662e3a6cde693f`
Date: 31 October 2026 (Asia/Saigon)
Git: local, uncommitted; not pushed; no PR/merge performed by this task

## Result

The profile reader now consumes Kim's actual published application source at
`ae77fa8bd47d590a53d26690b687bcad80692a9b` on
`origin/codex/kim/app-01-profile-integration`, contract **app.v1**. It imports
Kim's `ProfileFields`, `ProfileResponse`, `SessionVerifier` and authentication
error types instead of copying her schema or implementing another verifier.

The read path verifies the current credential using Kim's injected verifier,
compares both subject and login-session ID to the trusted authorization context,
then performs exactly one `GET /v1/profile` through an injected API-origin client.
It validates the complete response and returns only approved field values,
including nulls. It does not expose profile ID/revision or unapproved values,
send owner hints, create/update a profile, retry or follow redirects. No personal
token is retained on the adapter. The current API returns a full profile to the
trusted adapter; minimization is at the model boundary, not upstream partial reads.

No new profile store, identity mapping, Clerk instance, conversation system,
HTTP route/listener, service port, application manifest or shared contract added.
No Kim, Vincent or voice implementation file edited. Allowed paths remain
`son/access/` and this handoff. The manager owns consolidated Son status.

## Changed paths and internal migration

- `son/access/src/agent_access/profile_adapter.py`: read-only `ProfileReader`.
- `son/access/src/agent_access/authorization.py`, `__init__.py`: trusted context
  includes `auth_session`; dispatch preserves allowlisted `ToolFailure` outcomes.
- `son/access/tests/test_authorization.py`: verifies core supplies login-session ID.
- `son/access/contract_tests/test_profile_adapter.py`: pinned producer tests.
- `son/access/README.md`, `INTEGRATION.md`, this handoff: setup, evidence and limits.

Producer: Kim application; consumer: Son reader, invoked only by a trusted host
inside authorized dispatch. The Python adapter is not an accepted external wire
contract or a browser/model endpoint. Internal context construction changed from
four to five fields: `ToolContext(owner, conversation_id, procedure, fields,
auth_session)`. Core dispatch supplies the verified auth-session value. Update any
future direct internal constructors; never deserialize this object from a client.
No existing voice consumer is wired to it yet.

## Inputs, outputs, errors and configuration

`ProfileReader(client=..., verifier=..., timeout=5)` takes the existing Kim
verifier and a dedicated synchronous HTTP client configured for the trusted API
origin. The host owns their lifecycle and secret loading. No environment variables
are added here. The client must verify TLS in deployment and have no credential/
body logging or untrusted response hooks. Timeout must be finite and positive.

`read(credential, context)` takes a credential only for that call and the trusted
core context. Field names must be a nonempty subset of Kim's imported model keys.
The credential must verify to both the bound owner and exact login session.
Output is a dict whose keys are exactly the requested fields; no envelope metadata.
The adapter is not a consent gate on its own: invoke only after core authorization.
The credential closure used by tests exists only for synthetic test lifetimes;
production request binding and canonical voice lifecycle remain to implement.

| Outcome | Internal result |
| --- | --- |
| Invalid token, account/session mismatch, API 401/403 | `AccessDenied` |
| Existing verifier unavailable | `ToolFailure('AUTH_UNAVAILABLE')` |
| Exact documented 404 missing-profile response | `ToolFailure('PROFILE_NOT_FOUND')` |
| API 503 or transport failure/timeout | `ToolFailure('PROFILE_UNAVAILABLE')` |
| Invalid JSON/schema/field keys/types, missing no-store, redirect or unexpected status | `ToolFailure('PROFILE_RESPONSE_INVALID')` |

No raw upstream errors, credentials or field values enter these messages.
These four static `ToolFailure` codes pass through dispatch; unexpected callback
exceptions still become generic denial. No public HTTP mapping is invented.
The contract's `expected_revision` belongs to explicit PUT. The read adapter
never writes; 409 on GET is a protocol failure, not a retry instruction.

Core defaults remain: deny-all identity verifier, injected server-owned tools,
monotonic clock, conversation TTL 600 s, request TTL 120 s, grant TTL 600 s (bounded
by conversation/login expiry), 1,000 conversations, four per login session and
20 requests per conversation. Memory-only/single-process; no transcript/dossier
storage. Account/session IDs and approval metadata exist in private process memory
until end/lazy cleanup. Restart invalidates grants; bounds are not a distributed
rate limiter. Full method signatures/sequence remain documented in README.

## Verification executed

Producer source was exported with `git archive` at the exact SHA into ignored
`work/access-app-v1/source`. Dependencies were installed with the producer's
unmodified `api/uv.lock` via uv `sync --frozen`. No running service or port needed.
Python 3.13.15; no real account, secret or data supplied.

From repository root (reproduction/bootstrap in README):

```powershell
$env:PYTHONPATH = "$((Resolve-Path son/access/src).Path);$((Resolve-Path work/access-app-v1/source/api).Path)"
work/access-app-v1/source/api/.venv/Scripts/python.exe -m pytest son/access/contract_tests -q --tb=short
python -m unittest discover -s son/access/tests -q
work/access-app-v1/source/api/.venv/Scripts/python.exe work/access-app-v1/source/api/scripts/export_profile_contract.py --check
```

Results: **28 adapter tests passed; 24 core tests passed; generated profile
contract matches the API model**. Adapter tests import and reuse the pinned
producer's actual registered application routes, Clerk JWT verifier, profile
service and SQL repository with disposable SQLite fixtures. In-memory generated
RSA keys, session tokens, accounts and values are synthetic. No production route
or auth dependency is replaced. External HTTP is blocked. A source-pin test checks
the imported implementation/fixture files against that Git commit.

Covered: approved-field projection/null handling, missing-profile 404 without
creation, storage 503, wrong/expired issuer/session/party credentials, account/
login binding, owner isolation, unknown fields, absent auth configuration, read
without revision mutation, actual PUT revision conflict remaining separate,
authorization-before-read/revocation, sanitized typed errors, invalid/extra/missing
response fields, invalid revision/type, malformed/oversized payload, missing cache
protection, HTML, redirect, unexpected 409, network failure and timeout. Protocol
faults use MockTransport; tests make no network requests.

Eight existing Starlette/httpx TestClient deprecation warnings were observed,
including timeout use with TestClient; no skips/failures/suppression. These are
in-process tests, not proof of network timeout enforcement. Python 3.12 not run.
No Next/browser session, actual Clerk sign-in/logout, PostgreSQL/RLS or combined
voice/report flow tested. Producer's broader suites are not claimed as rerun.

## Dependencies and acknowledgement

| Dependency | Reference | Status |
| --- | --- | --- |
| Kim application | `ae77fa8bd47d590a53d26690b687bcad80692a9b`; authoritative `docs/application-contract.md`, generated types, API models/auth/profile implementation and configuration | received; isolated consumer checks passed; consumer uncommitted, not a full tested-compatible release |
| Earlier Kim checkpoint | `845291a04329324791c6ecf726037577ef8986e1` | received as a report; previous source-publication blocker now superseded for this reader |
| Shared guidance | `17900c3234add2a8c81c323e10a20d44dde88f1e` | received; one Clerk/app.v1 setup, no parallel stores or conversation system |
| Son voice | `d934436a3ba692b3fda8876ff3cd888683ded7d0`, static inspection | adaptation required; canonical lifecycle not wired |
| Kim consent/current-session revocation | No accepted live transport/configuration delivered to this consumer | pending; profile contract explicitly says local JWT verification does not establish immediate logout/revocation |
| Vincent retrieval/procedure | Not consumed by this adapter | separate dependency for reviewed facts/version/checklist and eventual report |

Full `tested compatible` acknowledgement awaits exact producer/consumer delivery
commits and agreed combined checks; this consumer has no commit yet. `app.v1`
profile revision is not a legal-procedure/checklist version.

## Remaining adaptation and limits

`Authorization.start()` still mints its isolated conversation ID. Do not connect
it as a second live conversation service. Attach authorization metadata to the
existing voice lifecycle with the voice owner; verify liveness at each personal
operation, invalidate on reset/end/expiry, realtime hangup/lease expiry and
shutdown, and agree reconnect consent semantics. Background invalidation needs a
trusted internal hook rather than a user-authenticated `end()` call. This task
does not implement a substitute lifecycle or enable personal Realtime tools.

Kim's local JWT verifier handles cryptographic/claim validation but not immediate
revocation. Agree current-session/logout enforcement, one shared Clerk instance,
issuer/authorized parties/audience/origins and credential transport before live
integration. Reuse the existing proxy/API path; never forward client-selected
owner IDs. Shared configuration changes remain with their owner.

Dispatch/adapter are synchronous under the existing global lock. The host must
coordinate async execution, I/O bounds and process model. A read admitted before
revocation can finish; data already transmitted cannot be recalled. Response
size is checked after buffering (16 KiB limit), and the supplied HTTP timeout is
not a total operation deadline. No retries or writes are implemented. This is a
profile consumer, not an approval UI or proof of full application security.

Next: manager reviews local delivery; Son and Kim agree the remaining identity/
consent and voice hooks, then wire and run two-account SECURITY-01 with exact SHAs.
Keep personal Realtime tools disabled until the host gates are integrated.

## Preserved documents and Git state

Earlier `docs/team/board.md` and `docs/team/status/son.md` edits are preserved,
not changed/staged by this adapter task. Board diff remains 2 additions/1 deletion
for ACCESS-01 state/dependencies/declaration; Son status remains 27 additions/
12 deletions describing the original isolated core and 24 tests. It contains old
missing-identity/source wording; the manager owns consolidation with newer
voice/adapter evidence. Do not publish these older edits indiscriminately.

Verification: eight explicit task files were temporarily staged and inspected;
`git diff --cached --check` passed. Preserved board/status edits and ignored
producer environments were not included. Files were subsequently unstaged for
local review; no commit was attempted.

Tracked modified files are those preserved board/status documents; handoff and
`son/access/` remain untracked against HEAD. Producer snapshot/environments are
ignored under work/. No ACCESS-01 commit, push, PR, merge, external message or
Git identity configuration change performed. Latest changes stay local for review.
