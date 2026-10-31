"""Synthetic SQL test fixture. SQLite is NOT PostgreSQL/RLS evidence."""

from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import create_engine, event

from hoso_api.portal.repository import ProfileRepository
from hoso_api.portal.service import ProfileService


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Synthetic portal tests must not make external HTTP requests.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture
def transactions(tmp_path):
    database = str(tmp_path / "synthetic-auth01.sqlite")
    engine = create_engine("sqlite://", hide_parameters=True)

    @event.listens_for(engine, "connect")
    def attach(connection, _):
        connection.execute("ATTACH DATABASE ? AS hoso_portal", (database,))
        connection.execute("PRAGMA busy_timeout = 10000")

    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE hoso_portal.profiles (
              owner_subject TEXT PRIMARY KEY, profile_id TEXT NOT NULL UNIQUE,
              revision INTEGER NOT NULL CHECK(revision > 0), full_name TEXT,
              date_of_birth TEXT, nationality TEXT, address TEXT, phone_number TEXT, email TEXT
            )
        """)

    class SyntheticSqliteTransactions:
        @contextmanager
        def for_user(self, user):
            # Deliberately no RLS: exercises the repository's SQL owner predicates.
            with engine.begin() as connection:
                yield connection

    yield SyntheticSqliteTransactions()
    engine.dispose()


@pytest.fixture
def repository(transactions):
    return ProfileRepository(transactions)


@pytest.fixture
def service(repository):
    return ProfileService(repository)
