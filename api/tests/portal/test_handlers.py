"""Real registered profile routes/lifespan with synthetic storage and tokens.

Production routes are wired by APP-01 and return 503 when storage is unavailable.
Locally signed tokens exercise the real shared verifier, not a live Clerk tenant.
"""

import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest

from hoso_api.main import create_app
from hoso_api.settings import Settings


@pytest.fixture(scope="module")
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    return key, Settings(
        clerk_jwt_key=public,
        clerk_issuer="https://auth01-synthetic.clerk.accounts.dev",
        clerk_authorized_parties=("http://127.0.0.1:3001",),
    )


def credential(signing, subject="synthetic_a", **overrides):
    key, settings = signing
    now = int(time.time())
    token = jwt.encode({
        "sub": subject, "sid": "synthetic_session", "iss": settings.clerk_issuer,
        "azp": "http://127.0.0.1:3001", "iat": now - 10, "nbf": now - 10,
        "exp": now + 120, **overrides,
    }, key, algorithm="RS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(signing, service):
    # The fixture owns its SQLite repository; the real app owns routing/lifespan.
    with TestClient(create_app(signing[1], profile_service=service)) as actual:
        yield actual


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_integrated_route_without_storage_returns_private_503(signing, method):
    app = create_app(signing[1])
    # Context entry runs the real application lifespan. Do not replace its router.
    with TestClient(app) as actual:
        assert app.state.profile_service is None
        response = actual.request(
            method, "/v1/profile", headers=credential(signing),
            **({"json": {"expected_revision": 0, "fields": {}}} if method == "PUT" else {}),
        )
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}
        assert response.headers["cache-control"] == "no-store"
    assert app.state.profile_service is None


def test_registered_api_a_b_ownership_and_revisions(client, signing):
    a, b = credential(signing), credential(signing, "synthetic_b")
    assert client.get("/v1/profile", headers=a).status_code == 404
    body = {"expected_revision": 0, "fields": {"full_name": "Synthetic Nguyễn A"}}
    first = client.put("/v1/profile", headers=a, json=body)
    assert first.status_code == 200
    assert first.json()["revision"] == 1
    assert client.get("/v1/profile", headers=b).status_code == 404
    attack = client.put("/v1/profile", headers=b, json={**body, "expected_revision": 1})
    assert attack.status_code == 404
    b_first = client.put("/v1/profile", headers=b, json={**body, "fields": {"full_name": "Synthetic B"}})
    assert b_first.status_code == 200
    # Browser identity hints and IDs cannot choose a different profile.
    response = client.get(
        "/v1/profile?subject=synthetic_b&profile_id=" + b_first.json()["profile_id"],
        headers={**a, "X-User-Id": "synthetic_b"},
    )
    assert response.json() == first.json()
    assert response.headers["cache-control"] == "no-store"
    changed = client.put("/v1/profile", headers=a, json={"expected_revision": 1, "fields": {}})
    assert changed.status_code == 200
    assert changed.json()["revision"] == 2
    assert client.put("/v1/profile", headers=a, json=body).status_code == 409
    assert client.get("/v1/profile", headers=b).json() == b_first.json()


@pytest.mark.parametrize("field", ["owner", "owner_subject", "user_id", "subject", "profile_id"])
def test_injected_owner_fields_rejected_without_echo(client, signing, field):
    response = client.put("/v1/profile", headers=credential(signing), json={
        "expected_revision": 0, "fields": {}, field: "synthetic-private-marker",
    })
    assert response.status_code == 422
    assert "synthetic-private-marker" not in response.text
    assert client.get("/v1/profile", headers=credential(signing)).status_code == 404


@pytest.mark.parametrize("overrides", [{"exp": 1}, {"iss": "https://other.invalid"}, {"azp": "https://evil.invalid"}])
def test_invalid_signed_claims_cannot_reach_repository(client, signing, overrides):
    response = client.get("/v1/profile", headers=credential(signing, **overrides))
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_missing_and_tampered_token_and_signed_out_cookie(client, signing):
    assert client.get("/v1/profile").status_code == 401
    token = credential(signing)["Authorization"]
    prefix, signature = token.rsplit(".", 1)
    corrupted = prefix + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
    assert client.get("/v1/profile", headers={"Authorization": corrupted}).status_code == 401
    client.cookies.set("__session", token.removeprefix("Bearer "))
    assert client.get("/v1/profile").status_code == 401


def test_storage_errors_and_missing_service_are_generic(client, signing):
    class Broken:
        def read(self, user):
            raise RuntimeError("synthetic-secret-dsn-and-profile")

    client.app.state.profile_service = Broken()
    response = client.get("/v1/profile", headers=credential(signing))
    assert response.status_code == 503
    assert response.json() == {"detail": {"code": "PROFILE_UNAVAILABLE"}}
    assert "synthetic-secret" not in response.text
    del client.app.state.profile_service
    assert client.get("/v1/profile", headers=credential(signing)).status_code == 503
