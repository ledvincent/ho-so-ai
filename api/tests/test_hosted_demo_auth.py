"""Hosted-demo auth opt-in: synthetic accounts, private API and exact HTTPS CSRF."""

from dataclasses import replace
import shutil

from fastapi.testclient import TestClient
import httpx
import pytest

from hoso_api.auth import AuthenticationUnavailable
from hoso_api.local_auth.runtime import build_local_services, valid_auth_origin
from hoso_api.local_auth.store import LocalAuthStore
from hoso_api.main import create_app
from hoso_api.settings import Settings


ORIGIN = "https://synthetic-jury.trycloudflare.com"
HEADERS = {"Origin": ORIGIN}


@pytest.fixture(autouse=True)
def no_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Hosted-demo tests must not contact external services")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture(scope="module")
def seed_database(tmp_path_factory):
    path = tmp_path_factory.mktemp("hosted-synthetic-seed") / "profiles.sqlite3"
    store = LocalAuthStore(path)
    store.create_user("synthetic-jury-a", "Synthetic-strong-password-a")
    store.create_user("synthetic-jury-b", "Synthetic-strong-password-b")
    store.close()
    return path


@pytest.fixture
def settings(seed_database, tmp_path):
    path = tmp_path / "isolated-hosted.sqlite3"
    shutil.copyfile(seed_database, path)
    return Settings(
        auth_provider="local", deployment_mode="hosted-demo", public_origin=ORIGIN,
        local_db_path=str(path), local_api_host="127.0.0.1", local_demo_seed=False,
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), client=("127.0.0.1", 51001)) as actual:
        yield actual


def login(client, username="synthetic-jury-a", password="Synthetic-strong-password-a", **kwargs):
    return client.post("/v1/auth/login", headers=HEADERS, json={"username": username, "password": password}, **kwargs)


@pytest.mark.parametrize("origin", [ORIGIN, "https://jury.example.invalid", "https://jury.example.invalid:8443"])
def test_https_public_origin_is_an_explicit_hosted_opt_in(origin):
    assert not valid_auth_origin(origin)
    assert valid_auth_origin(origin, "hosted-demo")
    assert not valid_auth_origin(origin, "unknown")


@pytest.mark.parametrize("origin", [
    None, "", "not-a-url", "http://jury.example.invalid", "https://localhost", "https://demo.localhost",
    "https://127.0.0.1", "https://192.168.1.1", "https://[::1]", "https://localhost:3025",
    "https://user:password@jury.example.invalid", ORIGIN + "/", ORIGIN + "/path",
    ORIGIN + "?next=private", ORIGIN + "#fragment", "https://*.example.invalid",
    "https://UPPER.example.invalid", "https://jury.example.invalid:443",
    "https://jury.example.invalid,https://other.example.invalid", "https://-jury.example.invalid",
])
def test_hosted_origin_rejects_weak_or_ambiguous_configuration(origin):
    assert not valid_auth_origin(origin, "hosted-demo")


def test_deployment_mode_defaults_local_and_rejects_unknown_env(monkeypatch):
    monkeypatch.delenv("HOSO_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("HOSO_LOCAL_DEMO_SEED", raising=False)
    assert Settings().deployment_mode == Settings.from_env().deployment_mode == "local"
    monkeypatch.setenv("HOSO_DEPLOYMENT_MODE", "hosted-demo")
    assert Settings.from_env().deployment_mode == "hosted-demo"
    monkeypatch.setenv("HOSO_DEPLOYMENT_MODE", "HOSTED-DEMO")
    with pytest.raises(ValueError, match="Unsupported deployment mode"):
        Settings.from_env()


def test_hosted_mode_refuses_weak_demo_seed_before_database_allocation(tmp_path, monkeypatch):
    path = tmp_path / "must-not-be-created.sqlite3"
    config = Settings(auth_provider="local", deployment_mode="hosted-demo", public_origin=ORIGIN,
                      local_db_path=str(path), local_demo_seed=True)
    with pytest.raises(AuthenticationUnavailable):
        build_local_services(config)
    assert not path.exists()
    monkeypatch.setenv("HOSO_DEPLOYMENT_MODE", "hosted-demo")
    monkeypatch.setenv("HOSO_LOCAL_DEMO_SEED", "true")
    with pytest.raises(ValueError, match="Weak demonstration seeding"):
        Settings.from_env()


@pytest.mark.parametrize("username,password", [("admin", "admin"), ("reviewer", "reviewer-demo")])
def test_hosted_runtime_and_registered_app_refuse_old_seeded_accounts_with_seed_flag_off(settings, username, password):
    store = LocalAuthStore(settings.local_db_path)
    store.create_user(username, password, demo_password=True)
    store.close()
    assert settings.local_demo_seed is False
    with pytest.raises(AuthenticationUnavailable):
        build_local_services(settings)
    with TestClient(create_app(settings), client=("127.0.0.1", 51001)) as client:
        response = client.post("/v1/auth/login", headers=HEADERS, json={"username": username, "password": password})
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "AUTH_UNAVAILABLE"}}


@pytest.mark.parametrize("changes", [
    {"local_api_host": "0.0.0.0"}, {"local_api_host": "192.168.1.1"},
    {"public_origin": "http://jury.example.invalid"}, {"public_origin": "http://127.0.0.1:3025"},
    {"deployment_mode": "unknown"},
])
def test_hosted_factory_keeps_api_binding_loopback_and_fails_before_allocation(tmp_path, changes):
    path = tmp_path / "must-not-be-created.sqlite3"
    config = Settings(auth_provider="local", deployment_mode="hosted-demo", public_origin=ORIGIN, local_db_path=str(path))
    with pytest.raises(AuthenticationUnavailable):
        build_local_services(replace(config, **changes))
    assert not path.exists()


def test_registered_hosted_login_session_profile_isolation_and_logout(client):
    first = login(client)
    assert first.status_code == 200
    token = first.json()["session_token"]
    headers = {**HEADERS, "Authorization": "Bearer " + token}
    session = client.get("/v1/auth/session", headers=headers)
    assert session.status_code == 200 and "session_token" not in session.json()
    assert session.json()["user"]["identity_provider"] == "local"
    assert client.put("/v1/profile", headers=headers, json={
        "expected_revision": 0, "fields": {"full_name": "Synthetic hosted jury A"},
    }).status_code == 200
    second = login(client, "synthetic-jury-b", "Synthetic-strong-password-b")
    other_headers = {**HEADERS, "Authorization": "Bearer " + second.json()["session_token"]}
    assert client.get("/v1/profile", headers=other_headers).status_code == 404
    assert client.get("/v1/profile", headers=headers).json()["fields"]["full_name"] == "Synthetic hosted jury A"
    assert client.post("/v1/auth/logout", headers=headers, json={}).status_code == 200
    assert client.get("/v1/auth/session", headers=headers).status_code == 401
    assert client.get("/v1/profile", headers=headers).status_code == 401


@pytest.mark.parametrize("headers", [
    {}, {"Origin": "https://other.trycloudflare.com"}, {"Origin": "null"},
    {"Origin": ORIGIN + "/"}, {"Origin": "http://synthetic-jury.trycloudflare.com"},
    {"Origin": "http://127.0.0.1:3025"},
])
def test_hosted_mutations_require_exact_public_origin_before_authentication(client, headers):
    result = client.post("/v1/auth/login", headers=headers, json={
        "username": "synthetic-jury-a", "password": "Synthetic-strong-password-a",
    })
    assert result.status_code == 403
    assert result.json() == {"detail": {"code": "ORIGIN_FORBIDDEN"}}


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded"])
def test_hosted_mutations_require_json(client, content_type):
    response = client.post("/v1/auth/login", headers={**HEADERS, "Content-Type": content_type}, content="{}")
    assert response.status_code == 403


def test_duplicate_origins_cannot_pass_exact_origin_guard(client):
    response = client.post("/v1/auth/login", headers=[("Origin", ORIGIN), ("Origin", ORIGIN)], json={})
    assert response.status_code == 403


@pytest.mark.parametrize("path,method", [
    ("/v1/auth/session", "get"), ("/v1/auth/login", "post"),
    ("/v1/profile", "get"), ("/v2/profile", "get"),
])
def test_hosted_api_still_refuses_non_loopback_peers_despite_forwarded_headers(settings, path, method):
    with TestClient(create_app(settings), client=("203.0.113.20", 51002)) as remote:
        headers = {**HEADERS, "X-Forwarded-For": "127.0.0.1", "Forwarded": "for=127.0.0.1", "X-Real-IP": "127.0.0.1"}
        response = getattr(remote, method)(path, headers=headers, **({"json": {}} if method == "post" else {}))
        assert response.status_code == 403


def test_hosted_failed_login_is_generic_and_does_not_echo_credentials(client, caplog):
    marker = "Synthetic-unknown-password-marker"
    response = login(client, "synthetic-unknown", marker)
    assert response.status_code == 401
    assert response.json() == {"detail": {"code": "INVALID_CREDENTIALS"}}
    assert marker not in response.text and marker not in caplog.text
    assert response.headers["cache-control"] == "no-store"


def test_hosted_unconfigured_origin_returns_unavailable_without_creating_database(tmp_path):
    path = tmp_path / "must-not-be-created.sqlite3"
    settings = Settings(auth_provider="local", deployment_mode="hosted-demo", public_origin=None, local_db_path=str(path))
    with TestClient(create_app(settings), client=("127.0.0.1", 51001)) as client:
        assert client.get("/v1/auth/session").status_code == 503
    assert not path.exists()
