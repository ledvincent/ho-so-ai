# PROFILE-01 backend handoff

Responsable : Kim. Etat : **En revue**, paused on 2026-10-31 after the bounded
backend delivery. No push, deployment, merge or shared database migration.

## Exact delivery and consumer contract

- Code: `33d1d3d03d98a6542ba80b16a8add8ad9eece10d`.
- Branch: `codex/kim/profile-01-reusable-details`.
- Worktree: `C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-profile-prefill`.
- Reviewed UI-03 base: `1825f5e15cf84fc6259004c56cec7185799ae12c`.
- [Contract](profile-01-contract.md), unchanged from the initial frontend handoff:
  SHA256 `3821c90d1eb21e95c31affd442667340b499b321791d041ce4e8fc8e0fe33df1`.
- Generated types: `web/lib/profile-v2.generated.ts`.
- Author: `BobLemon68 <tessierkim3@gmail.com>`.

`/api/profile/v2` forwards authenticated GET/PUT to `/v2/profile`.
`/api/profile/v2/prefill` forwards explicit consented POST to
`/v2/profile/prefill`. The existing strict six-field app.v1 API and generated
contract are unchanged. All writes use the same owner-bound profile row/ID and
revision. v1 preserves extensions; v2 preserves ambiguous legacy nationality/address.
New optional fields occupy one additive JSON column, without duplicate canonical
name/DOB/phone/email storage or a second identity system.

Prefill is a local pure mapping against Vincent's pinned NA5 schema at
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`. It requires real boolean consent and
applicant confirmation, current profile revision and exact form/schema identifiers.
It returns proposals and exclusions, never applies them or saves the profile.
Generic nationality/address, issue date, permanent address and unsupported sex
values are not guessed into NA5. Phone/email/combined contact are explicit alternatives.
No profile retrieval/transfer to a model, discovery service or voice tool occurs.

## Frontend integration notes

- Use a fresh `structuredClone(EMPTY_PROFILE_DETAILS)` for a new editor. Send all
  four groups and the complete edited snapshot on explicit save; omitted optional
  values clear to null. Empty optional passport dates should be null, not `""`.
- New error failures use `detail.code`; existing API validation remains 422 with
  `{code:"VALIDATION_ERROR",detail:"Invalid request data.",errors:[...]}`. Invalid
  draft prefill is 422 `PREFILL_INVALID_DRAFT`. Bodies are limited to 16384 UTF-8 bytes.
- Proposal source paths are relative to `details`, such as `basics.full_legal_name`;
  excluded legacy paths use `legacy.nationality` / `legacy.address`. Exact mapping
  and exclusion enums are generated from the API. Do not invent new mappings.
- Show exact source/target values and formatting before selection; only one contact
  alternative can be accepted. Confirm that the one saved travel document belongs
  to this application before accepting its passport proposals. No silent replacement
  of existing answers. Apply as one undoable draft change and invalidate review/export.
- Revalidate the current session and profile revision immediately before local
  Apply, not only when generating proposals. Another tab can edit the saved profile
  afterward. Reject stale user/profile/selection/request-generation/draft/schema
  snapshots, reload on conflict and keep saved-profile writes separate.

The backend does not provide an apply/undo UI or an atomic lock spanning server
profile reads and a browser-owned draft. Those consumer checks and the combined
browser journey remain the frontend owner's acceptance work. This is not a Son
ACCESS-01 grant; that integration was not validated by this task.

## Storage/startup requirements

Fresh isolated LOCAL SQLite databases initialize `details_json`. Startup never
alters an existing profile table. On an old schema, v1 remains usable and v2 returns
explicit 503 unavailable. For an explicitly named offline isolated test copy only:

```powershell
# From api/, after confirming this is not a shared or running database:
python scripts/upgrade_isolated_profile_details.py --database '<absolute-isolated-copy>' --confirm-isolated
```

The tool adds only the extension column, preserves data/revisions, refuses missing
or unsuitable paths, and is idempotent. The flag is an operator attestation; the
tool cannot prove a database is unused. PostgreSQL
`portal/migrations/002_profile_details.proposed.sql` is review-only, with the existing
RLS policy and a narrow column UPDATE grant. No PostgreSQL migration was run.

For a new local consumer runtime, use its own synthetic DB and coordinated free
ports. The observed HTTP validation used 3034/8034 with `HOSO_AUTH_PROVIDER=local`,
`HOSO_PUBLIC_ORIGIN=http://127.0.0.1:3034`, `HOSO_API_URL=http://127.0.0.1:8034`.
The API launcher was `scripts/run_local_checkpoint.py --database <new-absolute-path>
--origin http://127.0.0.1:3034 --port 8034 --demo-seed`, with no API key loaded.
Next used `pnpm --dir web build` then `pnpm --dir web start --port 3034`.
Do not reuse a running owner's port or migrate their database to integrate this code.

## Verification evidence

- **420 API tests passed** in the full regression run: prior 247 plus 103 new storage,
  58 prefill and 12 registered-route tests. Existing Starlette/httpx deprecation was
  the only warning. No live/provider requests were used.
- Final review added rejection of lone Unicode surrogates in new text fields only.
  **49 focused checks then passed**, including 8 new surrogate cases; unchanged
  v1-backed validators retain their existing behavior. The full suite was not
  rerun after that narrow change.
- **130 existing frontend tests passed**; production build including TypeScript
  passed. Both v1 and v2 generated-contract checks passed.
- **21 final production HTTP assertions passed** through Next and a real LOCAL API:
  login/logout, A/B isolation, strict v1 shape, shared ID/revisions, extension and
  legacy preservation, conflict rejection, consent, proposals/overwrite flags,
  unchanged saved profile after prefill, origin/query rejection and escaped-surrogate
  validation. The initial HTTP run created the synthetic profile and verified early
  assertions, then stopped because httpx refused to UTF-8 encode a raw surrogate.
  The final run correctly sent that case as JSON-escaped text and completed.
- Explicit staging, whitespace review and credential-shaped string scan passed.
  No env file, profile database, generated runtime output or UI component was committed.

Reproduction (from `api/`, with its dependencies installed):

```powershell
python -m pytest -q --tb=short --basetemp '<new-absolute-test-temp>'
python scripts/export_profile_contract.py --check
python scripts/export_profile_v2_contract.py --check
```

From the repository root:

```powershell
pnpm --dir web exec tsx --test lib/forms/*.test.ts lib/local-auth-policy.test.ts lib/discovery/*.test.ts components/*/*.test.ts
pnpm --dir web build
```

## Preserved resources and limits

Reviewed UI-03 listeners 3020/8020 and UI-02 listeners 3018/8018 were left running;
no foreign checkout or existing runtime database was edited. Only scratch Next
session 39237 on 3034 and API session 84003 on 8034 were started and then stopped.
The new ignored `api/tmp/profile01-acceptance.sqlite` is retained with synthetic
test data (A at revision 4, B without a profile). No task server remains running.

Security claims remain bounded: authenticated owner checks, CAS, no-store responses,
input limits and consented deterministic copying were tested locally. SQLite profile
contents are not encrypted by this code. No production PII readiness, public hosted
identity, live Clerk/PostgreSQL/RLS deployment, legal approval or official filled
document download was established. Existing model prompts and field-assist routing
were not modified; saved draft/profile values remain excluded from their input.

Read-only discovery follow-up: `validateProcedure` returns the producer snapshot
and requirements intact, rewriting only form original-download links. Returned
form IDs, source/provenance fields and structured-profile conditions/evidence are
preserved; absent producer data is not invented. The pinned producer has no catalog
list endpoint. General Q&A and multi-document checklist rendering remain frontend/
Vincent integration work, not an extra PROFILE-01 backend or retrieval pipeline.

Next: frontend integrates the exact code commit, completes profile/prefill UI and
stale/account/undo browser acceptance in its isolated runtime. Manager owns status
publication. Backend implementation is paused for that review.
