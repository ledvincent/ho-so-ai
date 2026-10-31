"""Registered profile routes + real local JWT verifier + actual service/SQL.

All identities, keys and field values are synthetic. The attached SQLite fixture
checks repository owner predicates and atomic revisions, not PostgreSQL or RLS.
No production router or authentication dependency is replaced in these tests.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from threading import Barrier
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx
import jwt
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

from hoso_api.main import create_app
from hoso_api.portal.repository import ProfileRepository
from hoso_api.portal.service import ProfileService
from hoso_api.settings import Settings


PRIVATE_SENTINEL = "synthetic-private-storage-credential-and-profile-marker"
A = "profile_integration_synthetic_a"
B = "profile_integration_synthetic_b"


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Profile integration tests must not make external HTTP requests.")

    async def async_blocked(*args, **kwargs):
        raise AssertionError("Profile integration tests must not make external HTTP requests.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_blocked)


@pytest.fixture(scope="module")
def signing():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    settings = Settings(
        clerk_jwt_key=public,
        clerk_issuer="https://profile-integration-synthetic.clerk.accounts.dev",
        clerk_authorized_parties=("http://127.0.0.1:3001",),
    )
    return private, settings


def credential(signing, subject=A, **overrides):
    private, settings = signing
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": subject,
            "sid": "profile_integration_synthetic_session",
            "iss": settings.clerk_issuer,
            "azp": "http://127.0.0.1:3001",
            "iat": now - 10,
            "nbf": now - 10,
            "exp": now + 120,
            **overrides,
        },
        private,
        algorithm="RS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def transactions(tmp_path):
    """Each connection attaches an isolated file, including concurrent workers."""
    database = str(tmp_path / "synthetic-profile-route-integration.sqlite")
    engine = create_engine(
        "sqlite://",
        poolclass=NullPool,
        connect_args={"check_same_thread": False, "timeout": 10},
        hide_parameters=True,
    )

    @event.listens_for(engine, "connect")
    def attach(connection, _):
        connection.execute("ATTACH DATABASE ? AS hoso_portal", (database,))
        connection.execute("PRAGMA busy_timeout = 10000")

    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE hoso_portal.profiles (
              owner_subject TEXT PRIMARY KEY, profile_id TEXT NOT NULL UNIQUE,
              revision INTEGER NOT NULL CHECK(revision > 0), full_name TEXT,
              date_of_birth TEXT, nationality TEXT, address TEXT,
              phone_number TEXT, email TEXT
            )
        """)

    class SyntheticSqliteTransactions:
        def __init__(self):
            self.subjects = []

        @contextmanager
        def for_user(self, user):
            self.subjects.append(user.subject)
            # No RLS here: the actual repository must apply its owner predicate.
            with engine.begin() as connection:
                yield connection

    try:
        yield SyntheticSqliteTransactions()
    finally:
        engine.dispose()


@pytest.fixture
def service(transactions):
    return ProfileService(ProfileRepository(transactions))


@pytest.fixture
def client(signing, service):
    # Exercise the application factory and its registered production handlers.
    # A context manager is required so startup and shutdown really execute.
    with TestClient(create_app(signing[1], profile_service=service)) as actual:
        yield actual


def body(revision=0, name="Synthetic Nguyễn A", **fields):
    return {"expected_revision": revision, "fields": {"full_name": name, **fields}}


def assert_private(response, status):
    assert response.status_code == status, response.text
    assert response.headers.get("cache-control") == "no-store"
    return response


@pytest.mark.parametrize("method", ["GET", "PUT"])
@pytest.mark.parametrize("kind", ["missing", "basic", "tampered", "expired", "issuer", "party", "session"])
def test_profile_authentication_refusals_do_not_reach_storage(client, signing, transactions, method, kind):
    headers = {}
    if kind == "basic":
        headers = {"Authorization": "Basic synthetic-not-a-session"}
    elif kind == "tampered":
        bearer = credential(signing)["Authorization"]
        prefix, signature = bearer.rsplit(".", 1)
        headers = {"Authorization": prefix + "." + ("A" if signature[0] != "A" else "B") + signature[1:]}
    elif kind != "missing":
        overrides = {
            "expired": {"exp": 1},
            "issuer": {"iss": "https://another-synthetic-instance.invalid"},
            "party": {"azp": "https://untrusted.invalid"},
            "session": {"sid": ""},
        }[kind]
        headers = credential(signing, **overrides)
    response = client.request(method, "/v1/profile", headers=headers, **({"json": body()} if method == "PUT" else {}))
    assert_private(response, 401)
    assert response.headers["www-authenticate"] == "Bearer"
    assert transactions.subjects == []


def test_missing_read_and_positive_revision_write_are_404_without_creation(client, signing):
    auth = credential(signing)
    assert_private(client.get("/v1/profile", headers=auth), 404)
    response = assert_private(client.put("/v1/profile", headers=auth, json=body(1)), 404)
    assert response.json() == {"detail": {"code": "PROFILE_NOT_FOUND"}}
    assert_private(client.get("/v1/profile", headers=auth), 404)


def test_expected_revision_zero_creates_and_positive_revision_updates(client, signing):
    auth = credential(signing)
    created = assert_private(client.put("/v1/profile", headers=auth, json=body()), 200).json()
    assert created["revision"] == 1
    assert created["profile_id"] and created["profile_id"] != A
    assert created["fields"]["full_name"] == "Synthetic Nguyễn A"
    assert_private(client.get("/v1/profile", headers=auth), 200)
    changed = assert_private(client.put("/v1/profile", headers=auth, json=body(1, "Synthetic corrected")), 200).json()
    assert changed["revision"] == 2
    assert changed["profile_id"] == created["profile_id"]
    assert changed["fields"]["full_name"] == "Synthetic corrected"


def test_registered_routes_isolate_a_b_despite_browser_owner_hints(client, signing):
    a, b = credential(signing), credential(signing, B)
    saved_a = assert_private(client.put("/v1/profile", headers=a, json=body()), 200).json()
    assert_private(client.get("/v1/profile", headers=b), 404)
    assert_private(client.put("/v1/profile", headers=b, json=body(saved_a["revision"], "Synthetic attack")), 404)
    saved_b = assert_private(client.put("/v1/profile", headers=b, json=body(0, "Synthetic Trần B")), 200).json()
    assert saved_a["profile_id"] != saved_b["profile_id"]
    queried_a = assert_private(client.get(
        "/v1/profile",
        params={"subject": B, "owner_subject": B, "user_id": B, "profile_id": saved_b["profile_id"]},
        headers={**a, "X-User-Id": B, "X-Owner-Subject": B},
    ), 200)
    assert queried_a.json() == saved_a
    # The same misleading hints on PUT can only modify B's own record.
    updated_b = assert_private(client.put(
        "/v1/profile",
        params={"subject": A, "profile_id": saved_a["profile_id"]},
        headers={**b, "X-User-Id": A},
        json=body(saved_b["revision"], "Synthetic B changed"),
    ), 200).json()
    assert updated_b["profile_id"] == saved_b["profile_id"]
    assert updated_b["revision"] == 2
    assert assert_private(client.get("/v1/profile", headers=a), 200).json() == saved_a
    assert assert_private(client.get("/v1/profile", headers=b), 200).json() == updated_b


@pytest.mark.parametrize("location", ["body", "fields"])
@pytest.mark.parametrize("field", ["owner", "owner_subject", "user_id", "subject", "profile_id"])
def test_client_selected_identity_fields_are_rejected_without_echo_or_mutation(client, signing, field, location):
    auth = credential(signing)
    original = assert_private(client.put("/v1/profile", headers=auth, json=body()), 200).json()
    request = body(1, "Synthetic must not be saved")
    (request if location == "body" else request["fields"])[field] = PRIVATE_SENTINEL
    response = assert_private(client.put("/v1/profile", headers=auth, json=request), 422)
    assert PRIVATE_SENTINEL not in response.text
    assert "Synthetic must not be saved" not in response.text
    assert assert_private(client.get("/v1/profile", headers=auth), 200).json() == original


def test_stale_create_and_update_return_409_without_lost_data(client, signing):
    auth = credential(signing)
    assert_private(client.put("/v1/profile", headers=auth, json=body()), 200)
    duplicate = assert_private(client.put("/v1/profile", headers=auth, json=body(0, "Synthetic duplicate")), 409)
    assert duplicate.json() == {"detail": {"code": "PROFILE_REVISION_CONFLICT"}}
    current = assert_private(client.put("/v1/profile", headers=auth, json=body(1, "Synthetic winner")), 200).json()
    assert_private(client.put("/v1/profile", headers=auth, json=body(1, "Synthetic stale")), 409)
    assert assert_private(client.get("/v1/profile", headers=auth), 200).json() == current


@pytest.mark.parametrize("starting_revision", [0, 1])
def test_simultaneous_registered_route_writes_have_one_winner(client, signing, starting_revision):
    auth = credential(signing)
    if starting_revision:
        assert_private(client.put("/v1/profile", headers=auth, json=body()), 200)
    barrier = Barrier(2)

    def save(name):
        barrier.wait(timeout=10)
        return client.put("/v1/profile", headers=auth, json=body(starting_revision, name))

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save, ["Synthetic first writer", "Synthetic second writer"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    for response in responses:
        assert response.headers["cache-control"] == "no-store"
    winner = next(response.json() for response in responses if response.status_code == 200)
    assert winner["revision"] == starting_revision + 1
    assert assert_private(client.get("/v1/profile", headers=auth), 200).json() == winner


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_missing_storage_fails_closed_with_generic_503(signing, method):
    with TestClient(create_app(signing[1])) as actual:
        response = actual.request(method, "/v1/profile", headers=credential(signing),
                                  **({"json": body()} if method == "PUT" else {}))
        assert_private(response, 503)
        assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_storage_failure_is_sanitized_in_registered_routes(signing, caplog, method):
    class BrokenTransactions:
        @contextmanager
        def for_user(self, user):
            raise RuntimeError(PRIVATE_SENTINEL)
            yield  # pragma: no cover - makes the failure a transaction entry error

    actual_service = ProfileService(ProfileRepository(BrokenTransactions()))
    with TestClient(create_app(signing[1], profile_service=actual_service)) as actual:
        response = actual.request(method, "/v1/profile", headers=credential(signing),
                                  **({"json": body()} if method == "PUT" else {}))
        assert_private(response, 503)
        assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}
        assert PRIVATE_SENTINEL not in response.text
        assert PRIVATE_SENTINEL not in caplog.text


def test_failed_transaction_rolls_back_through_real_service_and_route(signing, transactions, service):
    class FailingCommitTransactions:
        @contextmanager
        def for_user(self, user):
            with transactions.for_user(user) as connection:
                yield connection
                raise RuntimeError(PRIVATE_SENTINEL)

    failing = ProfileService(ProfileRepository(FailingCommitTransactions()))
    with TestClient(create_app(signing[1], profile_service=failing)) as actual:
        response = assert_private(actual.put("/v1/profile", headers=credential(signing), json=body()), 503)
        assert PRIVATE_SENTINEL not in response.text
    with TestClient(create_app(signing[1], profile_service=service)) as actual:
        assert_private(actual.get("/v1/profile", headers=credential(signing)), 404)


def test_form_copy_and_preview_do_not_save_profile_without_explicit_put(signing, service):
    settings = replace(signing[1], demo_forms_enabled=True)
    with TestClient(create_app(settings, profile_service=service)) as actual:
        auth = credential(signing)
        saved = assert_private(actual.put("/v1/profile", headers=auth, json=body()), 200).json()
        form_copy = dict(saved["fields"])
        form_copy["full_name"] = "Synthetic form-only correction"
        metadata = assert_private(actual.get("/v1/forms/demo"), 200).json()
        preview = assert_private(actual.post("/v1/forms/demo/preview", json={
            "values": form_copy, "revision": saved["revision"], "acknowledged": False,
            "template_version": metadata["template_version"],
        }), 200)
        assert preview.headers["content-type"] == "image/png"
        assert assert_private(actual.get("/v1/profile", headers=auth), 200).json() == saved
        explicitly_saved = assert_private(actual.put("/v1/profile", headers=auth, json={
            "expected_revision": saved["revision"], "fields": form_copy,
        }), 200).json()
        assert explicitly_saved["revision"] == saved["revision"] + 1
        assert explicitly_saved["fields"]["full_name"] == form_copy["full_name"]


def test_empty_field_replacement_is_explicit_and_preserves_profile_identity(client, signing):
    auth = credential(signing)
    saved = assert_private(client.put("/v1/profile", headers=auth, json=body()), 200).json()
    replaced = assert_private(client.put("/v1/profile", headers=auth, json={
        "expected_revision": saved["revision"], "fields": {},
    }), 200).json()
    assert replaced["profile_id"] == saved["profile_id"]
    assert replaced["revision"] == saved["revision"] + 1
    assert all(value is None for value in replaced["fields"].values())
