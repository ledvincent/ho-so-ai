"""PostgreSQL runtime for the proposed AUTH-01 schema; never creates/migrates it."""

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from ..auth import AuthenticatedUser
from ..settings import Settings
from .repository import ProfileRepository, StorageUnavailable, require_verified_user
from .service import ProfileService


# MEMBER deliberately over-approximates usable PG16 roles: it includes INHERIT
# FALSE / SET TRUE and mixed SET-then-inherit chains, even dormant memberships.
# Check every candidate's ACLs, not just privileges inherited by current_user.
# A provisioner must not accidentally be used as the application login.
_ROLE_CHECK = text("""
WITH runtime_roles AS (
  SELECT r.* FROM pg_roles r
  WHERE r.rolname IN (session_user, current_user)
     OR pg_has_role(session_user, r.oid, 'MEMBER')
     OR pg_has_role(current_user, r.oid, 'MEMBER')
)
SELECT
  NOT EXISTS (
    SELECT 1 FROM runtime_roles r
    WHERE (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb
        OR r.rolname IN ('pg_read_all_data', 'pg_write_all_data',
          'pg_read_server_files', 'pg_write_server_files', 'pg_execute_server_program'))
  )
  AND NOT EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'hoso_portal'
      AND (EXISTS (SELECT 1 FROM runtime_roles r WHERE r.oid = c.relowner)
        OR (c.relname = 'profiles' AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)))
  )
  AND NOT EXISTS (
    SELECT 1 FROM runtime_roles r
    WHERE has_schema_privilege(r.oid, 'hoso_portal', 'CREATE')
  )
  AND EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'hoso_portal' AND c.relname = 'profiles'
      AND c.relkind = 'r' AND c.relrowsecurity AND c.relforcerowsecurity
  )
  AND NOT EXISTS (
    SELECT 1 FROM runtime_roles r
    WHERE has_column_privilege(r.oid, 'hoso_portal.profiles', 'owner_subject', 'UPDATE')
       OR has_column_privilege(r.oid, 'hoso_portal.profiles', 'profile_id', 'UPDATE')
       OR has_table_privilege(r.oid, 'hoso_portal.profiles', 'DELETE,TRUNCATE,TRIGGER')
       OR has_any_column_privilege(r.oid, 'hoso_portal.identity_namespace', 'INSERT,UPDATE')
       OR has_table_privilege(r.oid, 'hoso_portal.identity_namespace', 'DELETE,TRUNCATE,TRIGGER')
  )
""")
_NAMESPACE = text("SELECT issuer FROM hoso_portal.identity_namespace WHERE singleton = true")
_CONTEXT = text("SELECT set_config('hoso_portal.subject', :subject, true)")


class PostgresTransactions:
    def __init__(self, database_url: str, issuer: str):
        if not issuer or not issuer.strip():
            raise StorageUnavailable()
        try:
            url = make_url(database_url)
            if url.drivername not in {"postgresql", "postgresql+psycopg"}:
                raise ValueError()
            # No unverified TLS or Unix-socket/hostaddr override from a DSN.
            allowed_query = {"sslmode", "sslrootcert"}
            if not url.host or set(url.query) - allowed_query:
                raise ValueError()
            if url.query.get("sslmode", "verify-full") != "verify-full":
                raise ValueError()
            self._engine = create_engine(
                url.set(drivername="postgresql+psycopg"),
                echo=False,
                hide_parameters=True,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=0,
                pool_timeout=10,
                connect_args={
                    "sslmode": "verify-full",
                    "ssl_min_protocol_version": "TLSv1.2",
                    "gssencmode": "disable",
                    "connect_timeout": 5,
                    "application_name": "hoso-auth01",
                },
            )
        except Exception:
            raise StorageUnavailable() from None
        self._issuer = issuer

    def close(self) -> None:
        self._engine.dispose()

    @contextmanager
    def for_user(self, user: AuthenticatedUser):
        require_verified_user(user)
        with self._engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            connection.execute(text("SET LOCAL lock_timeout = '3000ms'"))
            if connection.execute(_ROLE_CHECK).scalar_one() is not True:
                raise StorageUnavailable()
            bound_issuer = connection.execute(_NAMESPACE).scalar_one_or_none()
            if bound_issuer != self._issuer:
                raise StorageUnavailable()
            connection.execute(
                _CONTEXT,
                {"subject": user.subject},
            )
            yield connection
            # begin() commits or rolls back before returning the connection;
            # set_config(..., true) never persists identity in the pooled session.


def build_profile_service(settings: Settings) -> ProfileService | None:
    """Inject at startup; call the returned service.close() after requests drain."""
    if not settings.database_url or not settings.clerk_issuer:
        return None
    transactions = PostgresTransactions(settings.database_url, settings.clerk_issuer)
    return ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
