# Kim application delivery for Son and Vincent

Task: APP-01. Owner: Kim. This branch provides actual application code and
contracts for consumer development; it is not only a status report.

## Fetchable checkpoint

- Branch: `codex/kim/app-01-profile-integration`.
- Exact tested implementation/evidence checkpoint:
  `b07e28e74b4b9174979b7922ad3576d0562c778a`.
- Shared route/lifespan producer: `9cacda7320b5d18975a0bc2b62410eb74e45210f`.
- Portal hardening: `584e1ee9adbb5fd1f0a845c1357e204833202d6f`;
  portal evidence: `def58b7d04667d1865e281391dc25ef1723aa0a2`.
- This handoff is a documentation-only follow-up. Application behavior remains
  exactly that of the tested checkpoint. No main merge or live deployment.

Fetch without switching an active checkout:

```text
git fetch origin codex/kim/app-01-profile-integration
git show b07e28e74b4b9174979b7922ad3576d0562c778a:docs/application-contract.md
git show b07e28e74b4b9174979b7922ad3576d0562c778a:docs/clerk-configuration.md
```

Use an isolated consumer branch/worktree for implementation. Read the corrected
manager guidance at `17900c3234add2a8c81c323e10a20d44dde88f1e`; historical ownership
or pre-scaffold status notes do not supersede Kim/Son/Vincent's current split.

## Authoritative files

| Purpose | Path |
| --- | --- |
| Application contract, version `app.v1` | `docs/application-contract.md` |
| Clerk transport/configuration names and current limits | `docs/clerk-configuration.md` |
| API profile models and routes | `api/hoso_api/profile.py` |
| Verified identity/session boundary | `api/hoso_api/auth.py`, `api/hoso_api/settings.py` |
| Application composition/lifecycle | `api/hoso_api/main.py` |
| Profile repository/service/storage | `api/hoso_api/portal/` |
| Generated browser types | `web/lib/profile.generated.ts` |
| Browser-to-API proxy | `web/app/api/profile/route.ts`, `web/lib/server/clerk.ts` |
| Executed backend evidence | `docs/profile-integration-handoff.md`, `api/hoso_api/portal/HANDOFF.md` |

This is the user/profile backend and the earlier application foundation. The
latest branded frontend and demo login are a separate UI checkpoint; do not expect
them on this backend branch. Vincent owns procedure/retrieval/document services.

## Identity and profile adapter boundary

The API accepts a Clerk Bearer **session token**. It verifies the configured
public key, exact issuer, authorized parties, optional audience and required
subject/session/expiry claims. `GET /v1/me` returns the verified subject.
`GET /v1/profile` and `PUT /v1/profile` operate on that subject only; clients do
not select an owner or profile ID. Browser callers use the existing same-origin
Next `/api/profile` proxy. No service-account or browser-supplied identity bypass
is provided.

The six profile keys are `full_name`, `date_of_birth`, `nationality`, `address`,
`phone_number`, `email`, with exact types/bounds in the contract and generated
types. A synthetic creation body is:

```json
{
  "expected_revision": 0,
  "fields": {
    "full_name": "Synthetic Example",
    "date_of_birth": "1990-01-01",
    "nationality": null,
    "address": null,
    "phone_number": null,
    "email": null
  }
}
```

A successful create returns `profile_id`, revision 1 and all six fields. Updates
replace all six values and require the last received `expected_revision`; omitted
values become null. GET never creates a profile. Stale writes return 409
`PROFILE_REVISION_CONFLICT`; absent profiles return 404 `PROFILE_NOT_FOUND`;
storage failures return 503 `PROFILE_UNAVAILABLE`, in `detail: {code}`. Authentication
errors use the separately documented 401/503 shape. Private responses are no-store.

Consent-grant/revoke HTTP routes and conversation/document ownership contracts are
**not implemented by this delivery**. Son must bind authorization to his existing
voice conversation, verified Clerk subject and agreed consent scope; do not create
a second conversation or identity store. Local signature checks do not establish
immediate logout/revocation. Agree expiry/revocation behavior before live claims.

## Reproduce the bounded checks

From `api/`, with Python 3.12+ and uv:

```text
uv sync --locked --group dev
uv run pytest -q
uv run python scripts/export_profile_contract.py --check
```

Use a fresh test temp directory if Windows temp ownership prevents pytest setup.
The scaffold consumer independently reports 147 API tests passed and a matching
generated contract at the checkpoint. Fixtures use locally signed synthetic tokens
and disposable SQLite; no live Clerk keys are needed for this suite.

The separately documented 54 SQL/privilege checks used PGlite 0.3.16 reporting
PostgreSQL 17.5. They are not PostgreSQL 16/psycopg/TLS or pool/concurrency proof.
Their installed test dependency is not a new portable CI guarantee. Read the exact
handoff commands and limits before reproducing them.

Real Clerk instance/issuer/authorized-party configuration and PostgreSQL 16/TLS
acceptance remain pending. The API fails closed when unavailable. Never weaken
TLS or use the sample Compose database as proof of the restricted runtime setup.

## Vincent alignment and consumer next steps

Kim selected Vincent's published `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`
NA5 workflow `1.001146` as the primary frontend demo. Its existing schema,
conditional fields and exact blank document take precedence over the earlier CT01
test mock. User/profile fields are not automatically equivalent to applicant,
sponsor, birth-nationality or residence fields; mapping needs explicit semantics.

Vincent's `/assistant/chat` returns answers/citations, not validated form patches.
His schema/preview/download contract and review gate remain authoritative. Do not
auto-fill official values by parsing answer prose or create a duplicate retrieval
backend. His current draft/source gates and search-configuration limits remain.

Son can now inspect the actual app.v1 models and build isolated consumer contract
tests. Record this producer SHA, the consumer SHA and `received`, `adaptation
required` or `tested compatible` with exact evidence. Live identity/consent and a
shared immutable procedure/checklist reference remain explicit integration tasks.

Implementation is paused for Kim's intermediary preview except the designated
frontend owner's bounded NA5/admin demo checkpoint. This delivery does not restart
other workstreams or grant publication/merge permissions on their behalf.
