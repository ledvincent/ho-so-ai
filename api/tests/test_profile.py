"""Profile contract checks only; no persistence or authorization claims."""

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.main import create_app
from hoso_api.profile import ProfileFields, ProfileResponse, ProfileUpdate
from hoso_api.settings import Settings


class SyntheticVerifier:
    def verify(self, token):
        return AuthenticatedUser(subject="user_synthetic_a", session_id="sess_synthetic_a")


def client():
    return TestClient(create_app(Settings(), session_verifier=SyntheticVerifier()))


def test_profile_fields_include_null_for_all_missing_values():
    assert ProfileFields().model_dump() == {
        "full_name": None,
        "date_of_birth": None,
        "nationality": None,
        "address": None,
        "phone_number": None,
        "email": None,
    }


def test_unicode_and_address_line_breaks_are_preserved():
    fields = ProfileFields(full_name="Synthetic Nguyễn", address="Demo line 1\nDemo line 2")
    assert fields.full_name == "Synthetic Nguyễn"
    assert fields.address == "Demo line 1\nDemo line 2"


@pytest.mark.parametrize("value", ["2026-02-30", "2026-2-01", "20260201", "not-a-date"])
def test_birth_date_must_be_a_real_iso_date(value):
    with pytest.raises(ValidationError):
        ProfileFields(date_of_birth=value)


def test_birth_date_accepts_null_and_normalizes_empty():
    assert ProfileFields(date_of_birth=None).date_of_birth is None
    assert ProfileFields(date_of_birth="").date_of_birth is None
    assert ProfileFields(date_of_birth="2000-02-29").date_of_birth == "2000-02-29"


@pytest.mark.parametrize(
    "field,limit",
    [("full_name", 120), ("nationality", 80), ("address", 300), ("phone_number", 32), ("email", 254)],
)
def test_profile_text_is_bounded_without_truncation(field, limit):
    assert getattr(ProfileFields(**{field: "x" * limit}), field) == "x" * limit
    with pytest.raises(ValidationError):
        ProfileFields(**{field: "x" * (limit + 1)})


@pytest.mark.parametrize("field,value", [("full_name", "Demo\x00"), ("email", "demo\nvalue"), ("address", "Demo\x7f")])
def test_control_characters_are_rejected(field, value):
    with pytest.raises(ValidationError):
        ProfileFields(**{field: value})


def test_profile_contract_rejects_client_identity_and_boolean_revisions():
    with pytest.raises(ValidationError):
        ProfileUpdate(expected_revision=0, fields={}, user_id="user_synthetic_b")
    with pytest.raises(ValidationError):
        ProfileUpdate(expected_revision=True, fields={})
    with pytest.raises(ValidationError):
        ProfileFields(full_name=123)
    with pytest.raises(ValidationError):
        ProfileResponse(profile_id="synthetic-profile", revision=0, fields={})
    assert ProfileUpdate(expected_revision=0, fields={}).expected_revision == 0


def test_profile_routes_require_authentication():
    api = TestClient(create_app(Settings()))
    assert api.get("/v1/profile").status_code == 401
    assert api.put("/v1/profile", json={"expected_revision": 0, "fields": {}}).status_code == 401


def test_authenticated_profile_routes_are_explicitly_unimplemented():
    api = client()
    headers = {"Authorization": "Bearer synthetic-test-only"}
    assert api.get("/v1/profile", headers=headers).status_code == 501
    response = api.put(
        "/v1/profile", headers=headers, json={"expected_revision": 0, "fields": {"full_name": "Synthetic"}}
    )
    assert response.status_code == 501
    assert response.json() == {"detail": "Profile persistence is not implemented."}


def test_invalid_request_does_not_echo_profile_values_or_validation_exception():
    response = client().put(
        "/v1/profile",
        headers={"Authorization": "Bearer token-sentinel"},
        json={"expected_revision": 0, "fields": {"full_name": "private-sentinel" * 20}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["detail"] == "Invalid request data."
    assert "private-sentinel" not in response.text
    assert "token-sentinel" not in response.text
    assert "input" not in response.text


def test_unknown_field_names_do_not_echo_caller_supplied_personal_data():
    response = client().put(
        "/v1/profile",
        headers={"Authorization": "Bearer synthetic-test-only"},
        json={"expected_revision": 0, "fields": {"private-sentinel-in-key": "synthetic"}},
    )
    assert response.status_code == 422
    assert "private-sentinel-in-key" not in response.text
    assert response.json()["errors"][0]["loc"] == ["body", "fields", "unknown_field"]
