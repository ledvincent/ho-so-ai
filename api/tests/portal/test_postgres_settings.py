"""Connection policy checks only: no live PostgreSQL connection is opened."""

import pytest
import psycopg

from hoso_api.auth import AuthenticatedUser
from hoso_api.portal import postgres
from hoso_api.portal.postgres import PostgresTransactions, build_profile_service
from hoso_api.portal.repository import StorageUnavailable
from hoso_api.settings import Settings


@pytest.mark.parametrize("url", [
    "sqlite://", "postgresql:///db", "postgresql://user@host/db?sslmode=disable",
    "postgresql://user@host/db?sslmode=require", "postgresql://user@host/db?hostaddr=127.0.0.1",
    "postgresql://user@host/db?options=-c%20role=admin",
    "postgresql://user@host/db?gssencmode=prefer",
    "postgresql://user@host/db?gssencmode=require",
    "postgresql://user@host/db?ssl_min_protocol_version=TLSv1",
])
def test_downgraded_or_overridden_connections_rejected(url):
    with pytest.raises(StorageUnavailable):
        PostgresTransactions(url, "https://synthetic.invalid")


def test_unconfigured_factory_stays_unavailable():
    assert build_profile_service(Settings()) is None


def test_secure_engine_is_lazy_and_hides_parameters():
    transaction = PostgresTransactions("postgresql://synthetic@db.invalid/isolated", "https://synthetic.invalid")
    assert transaction._engine.hide_parameters is True
    assert transaction._engine.echo is False
    transaction.close()


def test_trusted_tls_options_reach_psycopg_despite_environment(monkeypatch):
    # Actual SQLAlchemy dialect -> DBAPI connect boundary; no socket is opened.
    monkeypatch.setenv("PGGSSENCMODE", "require")
    monkeypatch.setenv("PGSSLMODE", "disable")
    calls = []

    def reject_connection(*args, **kwargs):
        calls.append(kwargs)
        raise psycopg.OperationalError("synthetic-private-dsn-driver-details")

    monkeypatch.setattr(psycopg, "connect", reject_connection)
    service = build_profile_service(Settings(
        database_url="postgresql://synthetic@isolated.invalid/auth01?sslrootcert=synthetic-ca.pem",
        clerk_issuer="https://synthetic.invalid",
    ))
    assert service is not None
    try:
        with pytest.raises(StorageUnavailable) as failure:
            service.read(AuthenticatedUser(subject="synthetic_transport", session_id="synthetic_session"))
        assert str(failure.value) == ""
        assert failure.value.__suppress_context__ is True
        assert len(calls) == 1
        assert calls[0]["sslmode"] == "verify-full"
        assert calls[0]["ssl_min_protocol_version"] == "TLSv1.2"
        assert calls[0]["gssencmode"] == "disable"
        assert calls[0]["sslrootcert"] == "synthetic-ca.pem"
    finally:
        service.close()


def test_engine_configuration_failure_is_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic-private-connection-options")

    monkeypatch.setattr(postgres, "create_engine", fail)
    with pytest.raises(StorageUnavailable) as failure:
        PostgresTransactions("postgresql://synthetic@isolated.invalid/auth01", "https://synthetic.invalid")
    assert str(failure.value) == ""
    assert failure.value.__suppress_context__ is True
