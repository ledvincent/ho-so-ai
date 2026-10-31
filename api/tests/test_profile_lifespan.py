"""Application resource ownership; no real database connections or Clerk keys."""

from fastapi.testclient import TestClient
import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.main import create_app
from hoso_api.portal import postgres
from hoso_api.portal.repository import StorageUnavailable
from hoso_api.settings import Settings


class SyntheticVerifier:
    def verify(self, token):
        return AuthenticatedUser(subject="synthetic_lifespan", session_id="synthetic_session")


class LifecycleProbe:
    def __init__(self, fail_close=False):
        self.closed = 0
        self.fail_close = fail_close

    def close(self):
        self.closed += 1
        if self.fail_close:
            raise RuntimeError("synthetic-private-driver-detail")


def test_factory_is_lazy_and_app_closes_owned_service_once(monkeypatch):
    calls = []
    service = LifecycleProbe()
    config = Settings()

    def build(settings):
        calls.append(settings)
        return service

    monkeypatch.setattr(postgres, "build_profile_service", build)
    app = create_app(config)
    assert calls == []
    assert app.state.profile_service is None
    with TestClient(app) as client:
        assert calls == [config]
        assert app.state.profile_service is service
        assert client.get("/health").status_code == 200
        assert service.closed == 0
    assert service.closed == 1
    assert app.state.profile_service is None


def test_injected_service_remains_caller_owned(monkeypatch):
    service = LifecycleProbe()

    def unexpected(settings):
        pytest.fail("An injected service must not allocate a second production engine")

    monkeypatch.setattr(postgres, "build_profile_service", unexpected)
    app = create_app(Settings(), profile_service=service)
    with TestClient(app):
        assert app.state.profile_service is service
    assert service.closed == 0
    assert app.state.profile_service is None


@pytest.mark.parametrize("config", [
    Settings(),
    Settings(database_url="postgresql://synthetic@db.invalid/isolated"),
    Settings(clerk_issuer="https://synthetic.invalid"),
    Settings(database_url="postgresql://synthetic@db.invalid/isolated?sslmode=disable",
             clerk_issuer="https://synthetic.invalid"),
])
def test_missing_or_invalid_storage_config_keeps_private_routes_unavailable(config):
    app = create_app(config, session_verifier=SyntheticVerifier())
    with TestClient(app) as client:
        assert app.state.profile_service is None
        assert client.get("/health").json() == {"status": "ok"}
        headers = {"Authorization": "Bearer synthetic-lifecycle-only"}
        responses = [
            client.get("/v1/profile", headers=headers),
            client.put("/v1/profile", headers=headers,
                       json={"expected_revision": 0, "fields": {}}),
        ]
        for response in responses:
            assert response.status_code == 503
            assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}
            assert response.headers["cache-control"] == "no-store"


def test_factory_failure_does_not_log_sensitive_configuration(monkeypatch, caplog):
    def unavailable(settings):
        raise StorageUnavailable("synthetic-private-driver-detail")

    monkeypatch.setattr(postgres, "build_profile_service", unavailable)
    app = create_app(Settings())
    with TestClient(app):
        assert app.state.profile_service is None
    assert "synthetic-private-driver-detail" not in caplog.text


def test_owned_service_is_closed_when_lifespan_body_raises(monkeypatch):
    service = LifecycleProbe()
    monkeypatch.setattr(postgres, "build_profile_service", lambda config: service)
    app = create_app(Settings())
    with pytest.raises(RuntimeError, match="synthetic-body-error"):
        with TestClient(app):
            raise RuntimeError("synthetic-body-error")
    assert service.closed == 1
    assert app.state.profile_service is None


def test_cleanup_failure_is_generic_and_clears_service_reference(monkeypatch):
    service = LifecycleProbe(fail_close=True)
    monkeypatch.setattr(postgres, "build_profile_service", lambda config: service)
    app = create_app(Settings())
    with pytest.raises(RuntimeError, match="^Profile storage cleanup failed.$"):
        with TestClient(app):
            pass
    assert service.closed == 1
    assert app.state.profile_service is None


def test_real_factory_service_is_disposed_by_application_shutdown(monkeypatch):
    class EngineProbe:
        disposed = 0
        connected = 0

        def dispose(self):
            self.disposed += 1

        def begin(self):
            self.connected += 1
            raise RuntimeError("synthetic-driver-is-offline")

    engine = EngineProbe()
    monkeypatch.setattr(postgres, "create_engine", lambda *args, **kwargs: engine)
    app = create_app(Settings(
        database_url="postgresql://synthetic@isolated.invalid/app01",
        clerk_issuer="https://synthetic.invalid",
    ), session_verifier=SyntheticVerifier())
    assert engine.disposed == 0
    with TestClient(app) as client:
        service = app.state.profile_service
        assert service is not None
        assert engine.connected == 0
        response = client.get("/v1/profile", headers={"Authorization": "Bearer synthetic"})
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}
        assert engine.connected == 1
        assert engine.disposed == 0
    assert engine.disposed == 1
    assert app.state.profile_service is None
    with pytest.raises(StorageUnavailable):
        service.read(AuthenticatedUser(subject="synthetic_lifespan", session_id="synthetic_session"))
    assert engine.connected == 1
    service.close()
    assert engine.disposed == 1
