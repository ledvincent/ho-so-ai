"""Connection policy checks only: no live PostgreSQL connection is opened."""

import pytest

from hoso_api.portal.postgres import PostgresTransactions, build_profile_service
from hoso_api.portal.repository import StorageUnavailable
from hoso_api.settings import Settings


@pytest.mark.parametrize("url", [
    "sqlite://", "postgresql:///db", "postgresql://user@host/db?sslmode=disable",
    "postgresql://user@host/db?sslmode=require", "postgresql://user@host/db?hostaddr=127.0.0.1",
    "postgresql://user@host/db?options=-c%20role=admin",
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
