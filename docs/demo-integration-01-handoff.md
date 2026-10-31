# DEMO-INTEGRATION-01 backend integration handoff

This follow-up supersedes the temporary pause and limitations marked in the
earlier WIP checkpoint where explicitly updated below. Kim resumed implementation.
Consumer branch: `codex/kim/demo-integration-01-jury`, following WIP `1ad7db1`.
Producer `61b99f37dbb79409dba8a6d4027ce023a1dcf5c4` delivers data/bootstrap;
its `api`, `data/forms` and `docs/contracts` have no changes from pinned `e162791`.
The manager owns publication, data restore, final UI assembly and HTTPS launch.

## Consume now

- Protected route/types contract: `docs/demo-integration-01-discovery-contract.md`.
- Exact NA5 profile prefill bridge: `docs/demo-integration-01-prefill.md`.
  Keep the logical CHAT schema `50fe...` distinct from document template `0ea...`.
  The public pinned schema differs only by the evidenced uppercase flag and four
  date-order constraints; all field identities/definitions are checked before the
  new document version is accepted by prefill. Other documents remain unsupported
  for this narrow mapping. CHAT requests/responses remain unchanged.
- Preserve current account/profile revision, explicit applicant consent, request
  and draft revisions. Profile copy remains a proposal for review, not a save.
- Generic document requests use bounded dynamic fields (2000, 16000 code points
  per value, 128-character IDs, 1 MiB body) and current template version. Preview
  tokens have a 128 KiB adapter cap, are returned only in `X-Review-Token`, and
  are bound by hash to the authenticated owner, document, version and values.
  Producer/server HTTP header limits may be lower for unusually large tokens.
- Original DOCX hash is not a converted PDF hash. Producer checks private PDF
  integrity through its version; the adapter checks MIME/magic and versioned
  JSON contracts without pretending the public original hash identifies the PDF.

## Verification

| Check | Result |
| --- | --- |
| Hosted/local/Clerk auth and PostgreSQL settings API tests | 122 passed |
| Existing and new exact NA5 prefill tests | 101 passed |
| TypeScript auth/request-origin policy | 15 passed |
| Discovery routes and owner/version/value review bindings | 43 passed |
| Existing + new upstream transport tests | 57 passed (33 new) |
| Initial checkpoint production build | Passed |
| Production Next + private API HTTP smoke | 15 passed |
| Private jury provisioning | Passed; exclusive DB and owner-readable credentials |
| Launcher start + stop-file cleanup | Passed; both owned test ports closed |

Transport tests include checked-in public producer fixtures, a different small
document schema, signed state/choices, setup/degraded search, version mismatch,
draft-download refusal, exact protected URLs, MIME/PNG checks, streaming bounds,
safe errors and fake-clock 20/180-second deadlines. They perform no live calls.

HTTP smoke used fictional accounts and production Next on private `3036`, API
`8036`, configured HTTPS Origin `https://jury.example.test`. It verified fixed
login redirect, unauthenticated rejection, wrong-Origin rejection, Secure/HttpOnly/
SameSite host-only cookie flags, no token in browser JSON, authenticated workspace,
profile v2 write/read, cross-account isolation, stale revision rejection, logout
and revoked-session rejection. This is local HTTP evidence, not actual TLS/browser
acceptance through the jury tunnel. Smoke services are stopped; old previews are
unchanged. No provider keys or calls were used by these checks.

## Final launcher contract

Verified Python with dependencies:
`C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint\api\.venv\Scripts\python.exe`.
Scripts select code relative to their own checkout, so this Python environment
does not import the older checkpoint's application.

Run from the final assembled checkout, using absolute new paths under its ignored
`.runtime` folder. Do not reuse this backend owner's smoke DB/credentials.

```powershell
$demoPython = 'C:\Users\Kim\Documents\ChatGPT\Hackathon\work\kim-auth-chat-checkpoint\api\.venv\Scripts\python.exe'
& $demoPython api/scripts/provision_jury_accounts.py --database <new-absolute-.runtime-jury.sqlite3> --credentials-file <new-absolute-.runtime-credentials.json>
pnpm build
& $demoPython scripts/run_hosted_demo.py --origin https://dans-timer-miami-davis.trycloudflare.com --database <same-jury.sqlite3> --key-file <authorized-ignored-env-file> --web-port 3030 --api-port 8030 --vincent-url http://127.0.0.1:8001 --pid-file <absolute-.runtime-pids.json> --stop-file <absolute-initially-absent-.runtime-stop-file>
```

For background startup use `Start-Process -WindowStyle Hidden`. Creating the
chosen stop file triggers cleanup of only the launcher's owned process trees.
The API binds only loopback and ignores forwarded-client headers. The launcher
refuses occupied ports, weak demo accounts, an unbuilt checkout or unsafe origin.
Next receives explicit empty provider-key environment values; only the private
API reads the already authorized key file into memory. The root manager separately
starts Vincent with its own private configuration and owns the Quick Tunnel.

## Remaining acceptance

The final assembled frontend must be rebuilt and exercise the actual data-backed
producer, generic form flow, consented prefill, PDF preview and new signed-state
conversation. Manager must verify external HTTPS cookie/login/owner/logout behavior.
Template remains draft, applicability unresolved and official download disabled.
Source/transport tests do not establish legal approval or live RAG answer quality.
Shared live model budget used by this backend task: **0 of 6**. No retries or
uncoordinated paid smoke runs were performed.
