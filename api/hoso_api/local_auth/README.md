# AUTH-02 local checkpoint

This is an explicit single-machine development provider. It does not replace
Clerk/app.v1, provide civil identity proof, implement PostgreSQL RLS or permit a
public deployment. Use synthetic accounts and dossiers. SQLite files, journals
and backups require local filesystem access controls and an ignored directory;
this code does not claim encryption at rest.

`build_local_services(settings)` returns `None` unless `auth_provider == "local"`.
Local mode requires an absolute `local_db_path`, a loopback `local_api_host` and
an exact loopback `public_origin` with its explicit port. Defaults belong to the
shared settings owner: local auth and `local_demo_seed` remain disabled by default.
`local_session_ttl_seconds` is 60..86400 seconds (recommended checkpoint default3600).
Do not expose the API beyond its configured loopback listener. Forwarded client-IP
headers are not trusted by this router.

The application lifespan owns the returned `.store`, `.verifier` and `.profiles`
and calls `LocalServices.close()` once. It sets `app.state.local_auth_store` before
mounting `create_router(public_origin=...)` endpoints. Next owns the browser
HttpOnly/SameSite/Secure cookie and strips `session_token` from browser JSON.
The API receives that opaque token only in a Bearer header; cookies/query tokens
are not accepted. Session routes never return the token again.

The database stores an immutable random namespace and random user IDs. Subjects
are `local:<database namespace>:<uuid>`, so a matching username cannot become a
Clerk identity. Metadata persists across restart; demo seeding is idempotent and
does not reset an existing password or profile. Only a separate explicit local
demo flag seeds `admin/admin` and `reviewer/reviewer-demo`. There is no signup API.

Passwords use independent 16-byte random salts and stdlib scrypt N=2^17,r=8,p=1,
32-byte output and constant-time comparison. These are the OWASP minimum scrypt
parameters when Argon2id is unavailable. Two concurrent derivations bound RAM.
Unknown accounts perform the same password derivation against a dummy verifier.
The database never stores plaintext passwords or raw session tokens. Sessions
use 256 random bits, expire absolutely and are revoked at logout; only SHA-256
token verifiers are persisted. New login creates a fresh session, not a client-
supplied token. Up to20 active sessions are retained per account.

Login budgets are five attempts/account and20/client per300seconds. These count
all login attempts, including successful ones. Counters are atomic and persist
in SQLite, with hashed bucket keys, expiry pruning and a global2048-bucket cap.
`store.check_rate_limit(bucket,limit,window_seconds)` exposes the same persistent
counter for the server-owned chat boundary and raises `RateLimited.retry_after`.
Never take the bucket, limit or user identity from a browser field.

The SQLite transaction adapter attaches this same file as `hoso_portal` and uses
the existing `ProfileRepository`/`ProfileService`, preserving its owner predicates
and compare-and-swap revisions. It additionally checks that the local session is
still active before profile operations. This is a local adapter, not RLS.

Verification uses temporary databases and synthetic credentials. Run from `api/`:

```powershell
python -m pytest tests/test_local_auth.py -q -p no:cacheprovider
```

Security references used:

- [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP authentication and throttling](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP session management and one-way token storage](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
