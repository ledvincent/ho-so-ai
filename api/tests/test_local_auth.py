"""Local checkpoint acceptance with synthetic accounts and temporary SQLite only."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
from pathlib import Path
import secrets
import shutil
import sqlite3
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from hoso_api.auth import AuthenticatedUser, AuthenticationUnavailable, InvalidSession
from hoso_api.local_auth import (
    LocalAuthStore, LocalSessionVerifier, RateLimited, SQLiteTransactions,
    build_local_services, create_router,
)
from hoso_api.local_auth.hashing import check_password, hash_password
from hoso_api.local_auth.store import InvalidCredentials
import hoso_api.local_auth.store as store_module
from hoso_api.portal.repository import ProfileMissing, ProfileRepository, RevisionConflict, StorageUnavailable
from hoso_api.portal.service import ProfileService
from hoso_api.profile import ProfileUpdate, router as profile_router
from hoso_api.main import create_app
from hoso_api.settings import Settings

ORIGIN = "http://127.0.0.1:3015"
HEADERS = {"Origin": ORIGIN}


class Clock:
    value = 1_700_000_000

    def __call__(self):
        return self.value


@pytest.fixture(autouse=True)
def no_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Local auth tests must not contact external services")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture(scope="module")
def seed_database(tmp_path_factory):
    path = tmp_path_factory.mktemp("auth02-synthetic-seed") / "checkpoint.sqlite3"
    store = LocalAuthStore(path)
    store.create_user("admin", "admin", demo_password=True)
    store.create_user("reviewer", "reviewer-demo", demo_password=True)
    store.close()
    return path


@pytest.fixture
def store(seed_database, tmp_path):
    path = tmp_path / "checkpoint.sqlite3"
    shutil.copyfile(seed_database, path)
    actual = LocalAuthStore(path, clock=Clock())
    try:
        yield actual
    finally:
        actual.close()


def local_app(store):
    transactions = SQLiteTransactions(store)
    service = ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
    app = FastAPI()
    app.state.local_auth_store = store
    app.state.session_verifier = LocalSessionVerifier(store)
    app.state.profile_service = service
    app.include_router(create_router(public_origin=ORIGIN))
    app.include_router(profile_router)
    return app, service


@pytest.fixture
def client(store):
    app, service = local_app(store)
    with TestClient(app, client=("127.0.0.1", 50123)) as actual:
        yield actual
    service.close()


def login(client, username="admin", password="admin"):
    return client.post("/v1/auth/login", headers=HEADERS, json={"username": username, "password": password})


def test_scrypt_uses_independent_salts_and_safe_comparison():
    salt, digest = hash_password("synthetic-long-password")
    other_salt, other_digest = hash_password("synthetic-long-password")
    assert len(salt) == 16 and len(digest) == 32
    assert salt != other_salt and digest != other_digest
    assert check_password("synthetic-long-password", salt, digest)
    assert not check_password("synthetic-wrong-password", salt, digest)


def test_namespace_and_user_identity_persist_without_plaintext_passwords(store):
    saved = store.login("admin", "admin", client="synthetic-client")
    namespace = store.namespace
    assert saved.user.id.startswith(f"local:{namespace}:")
    assert saved.user.id != "admin"
    reopened = LocalAuthStore(store.path, clock=store.clock)
    assert reopened.namespace == namespace
    assert reopened.session(saved.session_token).user == saved.user
    assert b"reviewer-demo" not in store.path.read_bytes()
    with store.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE local_auth_metadata SET namespace=?", ("0" * 32,))
    reopened.close()


def test_tokens_are_random_hash_only_and_not_returned_by_session(client, store):
    result = login(client)
    assert result.status_code == 200
    payload = result.json()
    token = payload["session_token"]
    assert len(token) == 43
    assert payload["user"]["identity_provider"] == "local"
    assert result.headers["cache-control"] == "no-store"
    assert token.encode() not in store.path.read_bytes()
    with store.connection() as connection:
        digest = connection.execute("SELECT token_hash FROM local_auth_sessions").fetchone()[0]
        assert digest == hashlib.sha256(token.encode()).digest()
    session = client.get("/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert session.status_code == 200
    assert "session_token" not in session.json()
    assert session.json()["user"] == payload["user"]


def test_sessions_expire_and_logout_revokes_persistently(store):
    issued = store.login("admin", "admin", client="synthetic-client")
    verifier = LocalSessionVerifier(store)
    assert verifier.verify(issued.session_token).subject == issued.user.id
    reopened = LocalAuthStore(store.path, clock=store.clock)
    reopened.logout(issued.session_token)
    with pytest.raises(InvalidSession):
        verifier.verify(issued.session_token)
    again = store.login("admin", "admin", client="synthetic-client")
    assert again.session_token != issued.session_token
    store.clock.value = again.expires_at
    with pytest.raises(InvalidSession):
        reopened.session(again.session_token)
    reopened.close()


@pytest.mark.parametrize("token", ["", "fake.jwt.token", "a" * 42, "a" * 44, "a" * 43, "!" * 43])
def test_invalid_and_unknown_tokens_cannot_establish_identity(store, token):
    with pytest.raises(InvalidSession):
        LocalSessionVerifier(store).verify(token)


def test_two_accounts_share_existing_profile_logic_without_owner_hints(store):
    transactions = SQLiteTransactions(store)
    profiles = ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
    verifier = LocalSessionVerifier(store)
    a = verifier.verify(store.login("admin", "admin", client="synthetic-a").session_token)
    b = verifier.verify(store.login("reviewer", "reviewer-demo", client="synthetic-b").session_token)
    saved_a = profiles.write(a, ProfileUpdate(expected_revision=0, fields={"full_name": "Synthetic A"}))
    with pytest.raises(ProfileMissing):
        profiles.read(b)
    saved_b = profiles.write(b, ProfileUpdate(expected_revision=0, fields={"full_name": "Synthetic B"}))
    assert saved_a.profile_id != saved_b.profile_id
    assert profiles.read(a) == saved_a
    with pytest.raises(RevisionConflict):
        profiles.write(a, ProfileUpdate(expected_revision=0, fields={}))
    changed = profiles.write(a, ProfileUpdate(expected_revision=1, fields={}))
    assert changed.revision == 2 and changed.profile_id == saved_a.profile_id
    assert all(value is None for value in changed.fields.model_dump().values())
    assert profiles.read(b) == saved_b
    with pytest.raises(StorageUnavailable):
        profiles.read(AuthenticatedUser("user_clerk_synthetic", "synthetic-session"))
    profiles.close()


def test_revoked_session_cannot_use_previously_captured_profile_identity(store):
    session = store.login("admin", "admin", client="synthetic-client")
    identity = LocalSessionVerifier(store).verify(session.session_token)
    transactions = SQLiteTransactions(store)
    profiles = ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
    store.logout(session.session_token)
    with pytest.raises(StorageUnavailable):
        profiles.write(identity, ProfileUpdate(expected_revision=0, fields={}))
    profiles.close()


def test_logout_requires_exact_origin_and_revokes_http_session(client):
    token = login(client).json()["session_token"]
    bearer = {"Authorization": f"Bearer {token}"}
    rejected = client.post("/v1/auth/logout", headers={**bearer, "Origin": "http://127.0.0.1:3016"}, json={})
    assert rejected.status_code == 403
    assert client.get("/v1/auth/session", headers=bearer).status_code == 200
    assert client.post("/v1/auth/logout", headers={**HEADERS, **bearer}, json={}).json() == {"ok": True}
    assert client.get("/v1/auth/session", headers=bearer).json() == {"detail": {"code": "UNAUTHENTICATED"}}


@pytest.mark.parametrize("headers", [{}, {"Origin": "https://untrusted.invalid"}, {"Origin": "http://127.0.0.1:3016"}])
def test_login_rejects_missing_or_foreign_origins_before_credentials(client, headers):
    response = client.post("/v1/auth/login", headers=headers, json={"username": "admin", "password": "admin"})
    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "ORIGIN_FORBIDDEN"}}
    assert response.headers["cache-control"] == "no-store"


def test_non_loopback_client_is_rejected(store):
    app, service = local_app(store)
    with TestClient(app, client=("198.51.100.5", 50123)) as remote:
        assert login(remote).status_code == 403
    service.close()


def test_wrong_and_unknown_credentials_are_generic_and_not_logged(client, caplog):
    responses = [login(client, password="synthetic-private-wrong-password"), login(client, username="unknown-synthetic")]
    for response in responses:
        assert response.status_code == 401
        assert response.json() == {"detail": {"code": "INVALID_CREDENTIALS"}}
    assert "synthetic-private-wrong-password" not in caplog.text


def test_json_validation_is_sanitized_and_bounded(client):
    response = client.post("/v1/auth/login", headers=HEADERS, json={"username": "admin", "password": 123, "private-key-marker": "private-body-marker"})
    assert response.status_code == 422
    assert "private" not in response.text
    wrong_type = client.post("/v1/auth/login", headers={**HEADERS, "Content-Type": "text/plain"}, content="private-body-marker")
    assert wrong_type.status_code == 403
    oversized = client.post("/v1/auth/login", headers={**HEADERS, "Content-Type": "application/json", "Content-Length": "1"}, content=b"x" * 4097)
    assert oversized.status_code == 413


def test_session_cannot_use_cookie_or_query_token(client):
    token = login(client).json()["session_token"]
    client.cookies.set("hoso_local_session", token)
    response = client.get("/v1/auth/session", params={"token": token, "user_id": "admin"})
    assert response.status_code == 401


def test_account_throttle_persists_across_restart_and_client_rotation(store, monkeypatch):
    monkeypatch.setattr(store_module, "check_password", lambda *args: False)
    for number in range(5):
        with pytest.raises(InvalidCredentials):
            store.login("admin", "synthetic-wrong", client=f"synthetic-client-{number}")
    reopened = LocalAuthStore(store.path, clock=store.clock)
    with pytest.raises(RateLimited) as error:
        reopened.login("admin", "synthetic-wrong", client="synthetic-another-client")
    assert error.value.retry_after == 300
    store.clock.value += 300
    with pytest.raises(InvalidCredentials):
        reopened.login("admin", "synthetic-wrong", client="synthetic-another-client")
    reopened.close()


def test_client_throttle_applies_across_unknown_usernames(store, monkeypatch):
    monkeypatch.setattr(store_module, "check_password", lambda *args: False)
    for number in range(20):
        with pytest.raises(InvalidCredentials):
            store.login(f"synthetic-user-{number}", "synthetic-wrong", client="same-synthetic-client")
    with pytest.raises(RateLimited):
        store.login("synthetic-user-21", "synthetic-wrong", client="same-synthetic-client")


def test_http_throttle_has_stable_error_and_retry_after(client, monkeypatch):
    monkeypatch.setattr(store_module, "check_password", lambda *args: False)
    for _ in range(5):
        assert login(client, password="synthetic-wrong").status_code == 401
    response = login(client, password="synthetic-wrong")
    assert response.status_code == 429
    assert response.json() == {"detail": {"code": "RATE_LIMITED"}}
    assert response.headers["retry-after"] == "300"


def test_generic_rate_limits_are_atomic_bounded_and_expire(store, monkeypatch):
    monkeypatch.setattr(store_module, "_MAX_RATE_BUCKETS", 4)
    def attempt(_):
        try:
            store.check_rate_limit("synthetic-chat-bucket", 3, 60)
            return True
        except RateLimited:
            return False
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(attempt, range(8))) == 3
    for index in range(3):
        store.check_rate_limit(f"synthetic-bucket-{index}", 1, 60)
    with pytest.raises(RateLimited):
        store.check_rate_limit("synthetic-fifth-bucket", 1, 60)
    with store.connection() as connection:
        assert connection.execute("SELECT count(*) FROM local_auth_rates").fetchone()[0] == 4
    store.clock.value += 60
    store.check_rate_limit("synthetic-new-window", 1, 60)


def config(path, **changes):
    return SimpleNamespace(**{
        "auth_provider": "local", "local_db_path": str(path), "public_origin": ORIGIN,
        "local_api_host": "127.0.0.1", "local_demo_seed": False,
        "local_session_ttl_seconds": 3600, **changes,
    })


def test_factory_is_opt_in_and_does_not_allocate_disabled_database(tmp_path):
    path = tmp_path / "not-created.sqlite3"
    assert build_local_services(config(path, auth_provider="clerk", local_demo_seed=True)) is None
    assert not path.exists()


@pytest.mark.parametrize("changes", [{"local_api_host": "0.0.0.0"}, {"public_origin": "https://untrusted.invalid:443"}, {"local_db_path": "relative.sqlite3"}])
def test_factory_refuses_non_loopback_and_relative_storage_before_seeding(tmp_path, changes):
    path = tmp_path / "not-created.sqlite3"
    with pytest.raises(AuthenticationUnavailable):
        build_local_services(config(path, local_demo_seed=True, **changes))
    assert not path.exists()


def test_demo_seed_requires_separate_flag_and_persists_identity(tmp_path):
    path = tmp_path / "synthetic-factory.sqlite3"
    services = build_local_services(config(path))
    with services.store.connection() as connection:
        assert connection.execute("SELECT count(*) FROM local_auth_users").fetchone()[0] == 0
    services.close()
    seeded = build_local_services(config(path, local_demo_seed=True))
    first = seeded.store.login("admin", "admin", client="synthetic-client")
    other = seeded.store.login("reviewer", "reviewer-demo", client="synthetic-client")
    assert first.user.id != other.user.id
    seeded.close()
    reopened = build_local_services(config(path, local_demo_seed=True))
    assert reopened.store.login("admin", "admin", client="synthetic-client").user == first.user
    reopened.close()


def test_absent_store_returns_auth_unavailable_without_seeding():
    app = FastAPI()
    app.include_router(create_router(public_origin=ORIGIN))
    with TestClient(app, client=("127.0.0.1", 50123)) as actual:
        response = login(actual)
    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "AUTH_UNAVAILABLE"}}


def test_unconfigured_router_constructs_but_never_uses_an_injected_store(store):
    app = FastAPI()
    app.state.local_auth_store = store
    app.include_router(create_router(public_origin=None))
    with TestClient(app, client=("127.0.0.1", 50123)) as actual:
        assert login(actual).json() == {"detail": {"code": "AUTH_UNAVAILABLE"}}
        assert actual.get("/v1/auth/session").status_code == 503


def test_registered_local_app_login_profile_isolation_and_logout(store):
    settings = Settings(
        auth_provider="local", local_db_path=str(store.path), public_origin=ORIGIN,
        local_api_host="127.0.0.1", local_demo_seed=False,
    )
    app = create_app(settings)
    with TestClient(app, client=("127.0.0.1", 50123)) as actual:
        a = login(actual).json()
        b = login(actual, "reviewer", "reviewer-demo").json()
        auth_a = {"Authorization": f"Bearer {a['session_token']}"}
        auth_b = {"Authorization": f"Bearer {b['session_token']}"}
        assert actual.get("/v1/me", headers=auth_a).json() == {"subject": a["user"]["id"]}
        saved = actual.put("/v1/profile", headers={**HEADERS, **auth_a}, json={
            "expected_revision": 0, "fields": {"full_name": "Synthetic registered A"},
        })
        assert saved.status_code == 200
        assert saved.json()["revision"] == 1
        assert actual.get("/v1/profile", headers=auth_b).status_code == 404
        assert actual.get("/v1/profile", headers=auth_a).json() == saved.json()
        assert actual.get("/v1/chat/schema").status_code == 401
        assert actual.post("/v1/auth/logout", headers={**HEADERS, **auth_a}, json={}).status_code == 200
        assert actual.get("/v1/profile", headers=auth_a).status_code == 401
        assert actual.get("/v1/auth/session", headers=auth_a).status_code == 401
    assert app.state.local_auth_store is None
    assert app.state.profile_service is None


def test_registered_local_session_and_profile_survive_restart(store):
    settings = Settings(auth_provider="local", local_db_path=str(store.path), public_origin=ORIGIN)
    with TestClient(create_app(settings), client=("127.0.0.1", 50123)) as first:
        logged_in = login(first).json()
        headers = {"Authorization": f"Bearer {logged_in['session_token']}"}
        saved = first.put("/v1/profile", headers={**HEADERS, **headers}, json={
            "expected_revision": 0, "fields": {"full_name": "Synthetic restart account"},
        }).json()
    with TestClient(create_app(settings), client=("127.0.0.1", 50123)) as restarted:
        assert restarted.get("/v1/auth/session", headers=headers).json()["user"] == logged_in["user"]
        assert restarted.get("/v1/profile", headers=headers).json() == saved


def test_registered_local_app_unconfigured_storage_returns_sanitized_503():
    app = create_app(Settings(auth_provider="local", public_origin=ORIGIN))
    with TestClient(app, client=("127.0.0.1", 50123)) as actual:
        replies = [
            login(actual), actual.get("/v1/auth/session"),
            actual.post("/v1/auth/logout", headers=HEADERS, json={}),
        ]
        for reply in replies:
            assert reply.status_code == 503
            assert reply.json() == {"detail": {"code": "AUTH_UNAVAILABLE"}}
            assert reply.headers["cache-control"] == "no-store"
