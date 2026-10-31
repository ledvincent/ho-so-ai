"""Offline service ownership/lifecycle checks; no PostgreSQL connection is made."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.portal import postgres
from hoso_api.portal.repository import StorageUnavailable
from hoso_api.portal.service import ProfileService
from hoso_api.profile import ProfileUpdate
from hoso_api.settings import Settings


USER = AuthenticatedUser(subject="synthetic_lifecycle", session_id="synthetic_session")


def test_factory_exposes_public_cleanup_of_its_engine_without_connecting(monkeypatch):
    class SyntheticEngine:
        disposed = 0
        connections_started = 0

        def dispose(self):
            self.disposed += 1

        def begin(self):
            self.connections_started += 1
            raise AssertionError("Closed service must not reopen a connection.")

    engine = SyntheticEngine()
    monkeypatch.setattr(postgres, "create_engine", lambda *args, **kwargs: engine)
    service = postgres.build_profile_service(Settings(
        database_url="postgresql://synthetic@isolated.invalid/auth01",
        clerk_issuer="https://synthetic.invalid",
    ))
    assert service is not None
    service.close()
    service.close()
    assert engine.disposed == 1
    with pytest.raises(StorageUnavailable):
        service.read(USER)
    with pytest.raises(StorageUnavailable):
        service.write(USER, ProfileUpdate(expected_revision=0, fields={}))
    assert engine.disposed == 1
    assert engine.connections_started == 0


def test_concurrent_cleanup_calls_dispose_once(repository):
    calls = []
    service = ProfileService(repository, cleanup=lambda: calls.append("disposed"))
    barrier = Barrier(2)

    def stop(_):
        barrier.wait(timeout=10)
        service.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(stop, range(2)))
    assert calls == ["disposed"]


def test_failed_cleanup_is_generic_retryable_and_never_reopens_service(repository):
    attempts = []

    def cleanup():
        attempts.append("attempt")
        if len(attempts) == 1:
            raise RuntimeError("synthetic-sensitive-driver-details")

    service = ProfileService(repository, cleanup=cleanup)
    with pytest.raises(StorageUnavailable) as failure:
        service.close()
    assert str(failure.value) == ""
    assert failure.value.__suppress_context__ is True
    with pytest.raises(StorageUnavailable):
        service.read(USER)
    service.close()
    service.close()
    assert attempts == ["attempt", "attempt"]


def test_service_without_owned_cleanup_can_close_safely(service):
    service.close()
    service.close()
    with pytest.raises(StorageUnavailable):
        service.read(USER)
