"""Offline auth boundary tests with synthetic, locally signed session tokens."""

from dataclasses import replace
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx
import jwt
import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.main import create_app
from hoso_api.settings import Settings


@pytest.fixture(autouse=True)
def no_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not make outbound HTTP requests.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture(scope="module")
def signing_keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")
    return private, public


def make_token(private_key, **overrides):
    now = int(time.time())
    claims = {
        "sub": "user_synthetic_a",
        "sid": "sess_synthetic_a",
        "iss": "https://synthetic.clerk.accounts.dev",
        "azp": "http://localhost:3000",
        "iat": now - 30,
        "nbf": now - 30,
        "exp": now + 120,
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="RS256")


def configured_settings(public_key):
    return Settings(
        clerk_jwt_key=public_key,
        clerk_issuer="https://synthetic.clerk.accounts.dev",
        clerk_authorized_parties=("http://localhost:3000",),
    )


def test_health_does_not_require_auth():
    response = TestClient(create_app(Settings())).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic synthetic"}])
def test_missing_bearer_is_unauthorized(headers):
    response = TestClient(create_app(Settings())).get("/v1/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_unconfigured_auth_fails_closed(monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS", "true")
    response = TestClient(create_app(Settings())).get(
        "/v1/me", headers={"Authorization": "Bearer synthetic"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is unavailable."}


def test_valid_signed_session_exposes_only_verified_subject(signing_keys):
    private, public = signing_keys
    response = TestClient(create_app(configured_settings(public))).get(
        "/v1/me?user_id=user_synthetic_b",
        headers={"Authorization": f"Bearer {make_token(private)}"},
    )
    assert response.status_code == 200
    assert response.json() == {"subject": "user_synthetic_a"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": 1},
        {"azp": "https://untrusted.invalid"},
        {"iss": "https://another-instance.invalid"},
        {"sub": ""},
        {"sid": ""},
        {"nbf": 4_000_000_000},
    ],
)
def test_invalid_session_claims_are_rejected(signing_keys, overrides):
    private, public = signing_keys
    response = TestClient(create_app(configured_settings(public))).get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(private, **overrides)}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "A valid Bearer session is required."}


@pytest.mark.parametrize("missing", ["exp", "sub", "sid", "iss", "azp"])
def test_required_claims_cannot_be_omitted(signing_keys, missing):
    private, public = signing_keys
    claims = jwt.decode(make_token(private), options={"verify_signature": False})
    claims.pop(missing)
    token = jwt.encode(claims, private, algorithm="RS256")
    response = TestClient(create_app(configured_settings(public))).get(
        "/v1/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_signature_must_match_configured_instance(signing_keys):
    _, public = signing_keys
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    response = TestClient(create_app(configured_settings(public))).get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(wrong_key)}"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("token", ["ak_synthetic", "oat_synthetic", "m2m_synthetic", "not-a-jwt"])
def test_non_session_credentials_are_rejected_without_network(signing_keys, token):
    response = TestClient(create_app(configured_settings(signing_keys[1]))).get(
        "/v1/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_cookie_alone_is_not_a_backend_credential(signing_keys):
    private, public = signing_keys
    client = TestClient(create_app(configured_settings(public)))
    client.cookies.set("__session", make_token(private))
    assert client.get("/v1/me").status_code == 401


def test_configured_audience_is_verified(signing_keys):
    private, public = signing_keys
    settings = replace(configured_settings(public), clerk_audience="hoso-api")
    client = TestClient(create_app(settings))
    assert client.get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(private, aud='other-api')}"}
    ).status_code == 401
    assert client.get(
        "/v1/me", headers={"Authorization": f"Bearer {make_token(private, aud='hoso-api')}"}
    ).status_code == 200


def test_unexpected_provider_exception_is_sanitized():
    class BrokenVerifier:
        def verify(self, token):
            raise RuntimeError(f"provider details containing {token}")

    response = TestClient(create_app(Settings(), session_verifier=BrokenVerifier())).get(
        "/v1/me", headers={"Authorization": "Bearer secret-sentinel"}
    )
    assert response.status_code == 503
    assert "secret-sentinel" not in response.text
    assert "provider details" not in response.text


def test_cors_allows_only_the_configured_origin():
    client = TestClient(create_app(Settings()))
    headers = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "PUT"}
    allowed = client.options("/v1/profile", headers=headers)
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = client.options(
        "/v1/profile", headers={**headers, "Origin": "https://untrusted.invalid"}
    )
    assert "access-control-allow-origin" not in denied.headers


@pytest.mark.parametrize("env_name", ["CORS_ALLOWED_ORIGINS", "CLERK_AUTHORIZED_PARTIES"])
def test_wildcard_origins_are_not_valid_configuration(monkeypatch, env_name):
    monkeypatch.setenv(env_name, "*")
    with pytest.raises(ValueError, match="explicit HTTP"):
        Settings.from_env()
