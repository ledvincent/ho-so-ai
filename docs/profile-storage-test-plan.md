# Profile storage: isolated PostgreSQL and TLS acceptance plan

Status: proposed test plan, not an executed migration or live-storage proof.
Review snapshot: portal handoff `82e61585dd97f599f5dce506cbd6dfe3e3464223`.
The review read the actual provider, repository, proposed SQL and handoff; it did
not start PostgreSQL, apply SQL, change a role or exercise a TLS handshake.

This is an APP-01 integration dependency. The portal owner owns its repository,
runtime provider, role guard and SQL proposal. The scaffold owner wires the shared
application lifecycle and existing profile routes. Runtime fixes below remain
portal-owned until a new exact delivery is received and reviewed. Son owns voice,
conversation sessions and tool authorization; Vincent owns retrieval/RAG, official
sources and the procedure-data contract. No procedure schema is defined here.

## Review findings to resolve before acceptance

The proposed SQL currently gives narrow grants. The following findings concern
the runtime guard's ability to reject unsafe provisioning or transport drift;
they do not assert that these bad grants already exist in a running database.

| Finding | Reviewed location | Narrow owner action |
| --- | --- | --- |
| The issuer marker is not checked for runtime mutation rights | `api/hoso_api/portal/postgres.py:41-45`; `HANDOFF.md:116-120` promises an immutable marker | Reject table- and column-level mutations of `identity_namespace` for the runtime login and reachable roles. Cover UPDATE of `issuer`, INSERT, DELETE and TRUNCATE; keep provisioning separate. |
| Excess profile mutation checks inspect only `current_user` | `api/hoso_api/portal/postgres.py:41-43`, unlike the membership checks earlier in the guard | Inspect reachable custom roles as well. A role reachable with `INHERIT FALSE, SET TRUE` can hold TRUNCATE or identity-column rights without exposing those rights to the original `current_user`. |
| The TLS policy leaves GSS negotiation implicit | `api/hoso_api/portal/postgres.py:71-76` | Set `gssencmode=disable` in trusted connection arguments to force TLS, alongside `verify-full` and the minimum protocol. Test the negotiated transport. |

PostgreSQL distinguishes role membership, immediately inherited privileges and
the ability to SET ROLE. Its `has_any_column_privilege` function detects column-only
grants, which table-level checks alone can miss. TRUNCATE is outside RLS. These are
the basis for the first two negative-test groups, not evidence of an executed
exploit. [Privilege inquiry functions](https://www.postgresql.org/docs/16/functions-info.html),
[role membership](https://www.postgresql.org/docs/16/role-membership.html),
[RLS limits](https://www.postgresql.org/docs/16/ddl-rowsecurity.html).

libpq can prefer working GSSAPI encryption regardless of `sslmode`; forcing TLS
also requires disabling GSS encryption. Psycopg accepts libpq connection options
and keyword arguments override conninfo options. [libpq transport options](https://www.postgresql.org/docs/16/libpq-connect.html),
[Psycopg connection parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html).

## Isolated environment candidate

Use a separate disposable PostgreSQL 16 instance, not another schema inside a
shared development database. The existing root `compose.yaml` does not configure
TLS certificates or server TLS settings and cannot satisfy this plan as supplied.
Do not weaken the provider to make that compose work. There is no plaintext fallback.

Agree and record the following before creating resources:

- A unique test project/container/network/volume identity, with a resource manifest
  for cleanup. Do not reuse another worktree's database or provisioning credentials.
- Candidate host database port `55432`, bound to `127.0.0.1` only after checking
  availability immediately before startup. API `8002` and web `3002` were available
  at a prior observation; that observation is not a reservation. Recheck all ports.
- One isolated database, for example `hoso_auth01_test`. The proposed names
  `hoso_portal` and `hoso_portal_runtime` are acceptable candidates inside this
  isolated instance; they are not authorization to migrate a shared deployment.
- Separate provisioner and nonprivileged application login. `hoso_portal_runtime`
  remains a NOLOGIN grant role. An example separate login name is
  `hoso_portal_test_login`; it must not own the database/schema/tables or have
  superuser, BYPASSRLS, role/database administration or privileged memberships.
- Synthetic profile values and a fixed, owner-approved synthetic issuer. An example
  test-only issuer is `https://auth01-test.invalid`; it is not a real Clerk tenant.
  Use the same approved value in the local token verifier configuration and the
  database marker. Do not infer an issuer from a browser field or a profile payload.
- Locally generated synthetic signing keys for API tests. No real Clerk account,
  token, profile, phone number or legal document is needed for these tests.

### TLS preparation

Generate an ephemeral test CA and a server certificate signed by it. Keep private
keys, configured DSNs and passwords in ignored test storage with restricted access;
never print or commit them. No system trust-store or hosts-file change is required.

The certificate may include `DNS:db.localhost` and `IP:127.0.0.1` SANs. Use
`127.0.0.1` for the host client when that IP SAN exists. Use `db.localhost` only
when the isolated network explicitly resolves it to the test server; do not assume
the operating system resolves every `.localhost` subdomain. For the negative-name
test, use a resolving loopback name absent from the certificate SANs, or a second
test certificate with the wrong SAN.

Configure the disposable server with TLS enabled, its certificate/key paths and
TLS >=1.2. Enforce hostssl access from only the isolated test network, reject
hostnossl access, and use a reviewed authentication method such as SCRAM. Mount
the server key with ownership/permissions acceptable to the PostgreSQL process.
Enabling TLS alone does not reject plaintext clients. [PostgreSQL server TLS setup](https://www.postgresql.org/docs/16/ssl-tcp.html).

Give the runtime provider an explicit CA path through `sslrootcert`, retain
`sslmode=verify-full`, and require the portal-owned GSS fix before acceptance.
`verify-full` checks the certificate chain and the requested hostname/IP against
the certificate; merely completing an encrypted connection is insufficient.
[libpq certificate verification](https://www.postgresql.org/docs/16/libpq-ssl.html).

### Provisioning boundary

After the owner accepts the exact SQL candidate, the provisioner may apply it only
to the disposable instance. Do not add an automatic startup migration to the API.
Create the restricted login and runtime membership separately, with reviewed
INHERIT/SET choices and a credential supplied by local secret tooling.

Insert the fixed issuer as a bound parameter using the provisioning connection,
not string interpolation. For example, inside a provisioning transaction:

```python
connection.execute(
    "INSERT INTO hoso_portal.identity_namespace (singleton, issuer) VALUES (true, %s)",
    (approved_test_issuer,),
)
```

This is a review example, not a migration executed by this document. Treat the
marker as an immutable namespace binding, not a tenant-migration switch. Changing
tenants or reassigning subjects requires a separately reviewed identity migration.
The application receives only the runtime DSN; it must never receive the provisioner
DSN or a login capable of repairing its own privileges.

## Acceptance matrix

Every row is pending execution. Record exact producer/consumer commits, commands,
test versions and sanitized outcomes. A passing earlier SQLite/PGlite test does not
satisfy a real psycopg/network/TLS row.

| Area | Required exercise | Acceptance |
| --- | --- | --- |
| Actual wire stack | Use the shipped SQLAlchemy provider and installed psycopg against PostgreSQL 16 | Real connection and repository SQL run as the restricted login; no SQLite/PGlite substitute |
| Positive TLS | Correct CA and certificate SAN using the real provider | Current backend reports SSL with protocol TLSv1.2 or TLSv1.3; provider connection options enforce verify-full and GSS disabled |
| Negative TLS | Wrong CA, wrong certificate name, TLS-disabled server, and attempted downgraded DSN | Connection/configuration fails without plaintext fallback; API error is sanitized, without DSN or credentials |
| Runtime identity | Inspect session_user/current_user and memberships | Application is not the provisioner/owner; unexpected elevated or mutation-capable roles fail the guard |
| Namespace | Missing marker, wrong configured issuer, and a token with another issuer | Storage mismatch/missing marker is unavailable; a wrong-issuer token is rejected by the real verifier before personal access |
| Normal profile path | Synthetic A/B: missing read, create at revision 0, read, update, full null replacement | GET has no creation side effect; correct data and revision; another user's record is never selected |
| CAS races | Two independent physical connections create the same subject, then update from the same revision | Exactly one success and one conflict each time; no lost write or duplicate record |
| RLS | Direct runtime SELECT without an owner predicate, forged-owner INSERT/UPDATE and no context | Only current subject rows are visible; invalid mutation is denied; absent context exposes no profile |
| Pool reuse | A commit -> B request and A rollback/error -> B request on deterministically reused connections | No subject context survives transaction completion; B never receives A's row |
| Failure recovery | Hold a conflicting row lock; exercise lock/statement timeouts and a failed commit | Sanitized unavailable response, rollback and released connection; later valid operation succeeds |
| Production API composition | Wire the existing shared GET/PUT profile routes to the delivered service | Missing/invalid session 401; missing profile 404; valid create/update 200; stale revision 409; invalid payload 422; storage unavailable 503; private no-store responses |
| Browser seam | API 8002/web 3002 after fresh port checks; synthetic A/B accounts or the approved local auth-test harness | Explicit save only; form prefill is a copy; form edits do not PUT the saved profile; logout/account transition clears old draft and late responses |
| Lifecycle | Application shutdown through the agreed public cleanup interface | Engine/pool resources are disposed; no private-field traversal required by the shared factory |

Do not add a production authentication bypass to pass browser tests. A local
test-only composition is separate evidence; genuine Clerk browser acceptance
remains pending until its agreed tenant and credentials are available.

For transport evidence, query the runtime connection itself:

```sql
SELECT ssl, version
FROM pg_stat_ssl
WHERE pid = pg_backend_pid();
```

The view reports actual transport for that backend. Keep evidence to booleans,
protocol/version and synthetic test outcomes; do not include credentials or profile
contents. [PostgreSQL SSL statistics](https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-SSL-VIEW).

### Privilege drift probes

Use the provisioner to introduce each bad grant in a fresh disposable fixture,
then connect as the runtime login. Never grant these rights in a shared database.
The application guard must refuse service before performing profile operations:

1. Direct table UPDATE or column-only UPDATE of `identity_namespace.issuer`;
   INSERT, DELETE and TRUNCATE of the marker table.
2. Direct UPDATE of `profiles.owner_subject` or `profile_id`; excess DELETE,
   TRUNCATE or TRIGGER rights on `profiles`.
3. The same rights on a custom role granted to the login with
   `INHERIT FALSE, SET TRUE`. Include TRUNCATE specifically, since RLS does not
   protect it. Check both immediately inherited and SET ROLE paths.
4. Table/schema owner membership, superuser/BYPASSRLS, CREATE ROLE/CREATE DB,
   privileged predefined-role memberships and schema-creation rights.

The narrow SQL proposal should also deny these direct mutation commands before
any bad-grant fixture is introduced. Keep separate evidence for baseline SQL
privileges, runtime guard rejection and normal owner-scoped repository behavior.

For pooling tests, use a test configuration that guarantees reuse and record the
backend PID to show it happened. Test identity reset after both commit and rollback.
The provider's transaction context must cover setting the subject and all related
queries on the same connection. PostgreSQL LOCAL settings end with the transaction;
Psycopg transaction contexts commit on success and roll back on an exception.
[PostgreSQL SET LOCAL](https://www.postgresql.org/docs/16/sql-set.html),
[Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

## Cleanup and evidence boundary

Stop only the test API/web processes and the recorded isolated database resources.
Dispose the provider through its public lifecycle method before removing the test
instance. Verify project/container/volume identities against the resource manifest;
do not issue broad database, volume or worktree cleanup commands. Remove ephemeral
private keys, credentials and synthetic data from the isolated test storage, and
confirm unrelated development services are still present.

Keep a sanitized report with exact commits, PostgreSQL/psycopg/libpq versions,
executed test commands, pass/fail counts, transport evidence and any skipped rows.
A future successful run establishes this local integration only. It does not prove
live Clerk sign-in, immediate revocation, production disk/backup encryption,
retention/deletion compliance, Son's authorization path or an approved official form.
