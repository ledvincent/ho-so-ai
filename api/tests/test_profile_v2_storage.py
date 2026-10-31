"""PROFILE-01 storage acceptance: synthetic accounts and isolated SQLite only."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import json
import shutil
import sqlite3

import httpx
from pydantic import ValidationError
import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.local_auth.runtime import SQLiteTransactions
from hoso_api.local_auth.store import LocalAuthStore, LocalSessionVerifier
from hoso_api.portal.repository import ProfileMissing, ProfileRepository, RevisionConflict, StorageUnavailable
from hoso_api.portal.service import ProfileService
from hoso_api.profile import ProfileFields, ProfileUpdate
from hoso_api.profile_v2_models import ProfileDetails, ProfileV2Response, ProfileV2Update
from scripts.upgrade_isolated_profile_details import upgrade_isolated_database


NOW = 1_700_000_000
OLD_TABLE = """CREATE TABLE profiles (
    owner_subject TEXT PRIMARY KEY, profile_id TEXT NOT NULL UNIQUE,
    revision INTEGER NOT NULL CHECK(revision>0), full_name TEXT,
    date_of_birth TEXT, nationality TEXT, address TEXT,
    phone_number TEXT, email TEXT)"""


def details_dict():
    return {
        "basics": {
            "full_legal_name": "Synthetic Applicant", "date_of_birth": "1996-02-29",
            "sex_as_on_document": "X", "nationality_at_birth": "Synthetic birth nationality",
            "current_nationality": "Synthetic current nationality", "occupation": "Synthetic tester",
        },
        "contact": {"phone_number": "+00 000 000", "email": "synthetic@example.invalid"},
        "passport": {
            "document_number": "SYNTHETIC-ONLY", "document_type": "Synthetic travel document",
            "issue_date": "2020-01-02", "expiry_date": "2030-01-02",
            "issuing_authority": "Synthetic authority",
        },
        "residence": {
            "temporary_address_in_vietnam": "Synthetic address\nSecond line",
            "permanent_address": "Synthetic permanent address",
        },
    }


def update(revision=0, details=None):
    return ProfileV2Update(expected_revision=revision, details=details or details_dict())


@pytest.fixture(autouse=True)
def no_outbound_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Profile storage tests must not contact external services")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture(scope="module")
def seed_database(tmp_path_factory):
    path = tmp_path_factory.mktemp("profile01-synthetic-seed") / "profiles.sqlite3"
    store = LocalAuthStore(path, clock=lambda: NOW)
    store.create_user("synthetic-a", "synthetic-password-a")
    store.create_user("synthetic-b", "synthetic-password-b")
    a = store.login("synthetic-a", "synthetic-password-a", client="127.0.0.1")
    b = store.login("synthetic-b", "synthetic-password-b", client="127.0.0.1")
    store.close()
    return path, a.session_token, b.session_token


@pytest.fixture
def storage(seed_database, tmp_path):
    seed, token_a, token_b = seed_database
    path = tmp_path / "isolated-profiles.sqlite3"
    shutil.copyfile(seed, path)
    store = LocalAuthStore(path, clock=lambda: NOW)
    transactions = SQLiteTransactions(store)
    service = ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
    verifier = LocalSessionVerifier(store)
    yield store, transactions, service, verifier.verify(token_a), verifier.verify(token_b)
    service.close()
    store.close()


def test_fresh_store_has_additive_column_with_empty_default(storage):
    store, _, service, a, _ = storage
    with store.connection() as connection:
        columns = {row[1]: row for row in connection.execute("PRAGMA table_info(profiles)")}
    assert columns["details_json"][2:5] == ("TEXT", 1, "'{}'")
    first = service.write(a, ProfileUpdate(expected_revision=0, fields={"full_name": "Synthetic A"}))
    response = service.read_v2(a)
    assert response.profile_id == first.profile_id and response.revision == first.revision == 1
    assert response.details.basics.full_legal_name == "Synthetic A"
    assert response.details.basics.current_nationality is None


def test_v2_create_shares_v1_columns_identity_and_revision_without_json_duplicates(storage):
    store, _, service, a, _ = storage
    result = service.write_v2(a, update())
    old = service.read(a)
    assert result.schema_version == "profile.v2"
    assert result.profile_id == old.profile_id and result.revision == old.revision == 1
    assert old.fields.full_name == result.details.basics.full_legal_name
    assert old.fields.date_of_birth == result.details.basics.date_of_birth
    assert old.fields.phone_number == result.details.contact.phone_number
    assert old.fields.email == result.details.contact.email
    assert result.legacy.model_dump() == {"nationality": None, "address": None}
    with store.connection() as connection:
        row = connection.execute("SELECT details_json FROM profiles").fetchone()
    extension = json.loads(row[0])
    assert set(extension) == {"basics", "passport", "residence"}
    assert set(extension["basics"]) == {
        "sex_as_on_document", "nationality_at_birth", "current_nationality", "occupation",
    }
    for core_value in ("Synthetic Applicant", "1996-02-29", "+00 000 000", "synthetic@example.invalid"):
        assert core_value not in row[0]


def test_v1_and_v2_preserve_other_version_fields_and_invalidate_stale_revisions(storage):
    _, _, service, a, _ = storage
    first = service.write(a, ProfileUpdate(expected_revision=0, fields={
        "nationality": "Ambiguous synthetic nationality", "address": "Legacy synthetic address\n\tUnit",
    }))
    second = service.write_v2(a, update(1))
    assert second.legacy == service.read_v2(a).legacy
    assert second.legacy.nationality == "Ambiguous synthetic nationality"
    assert second.legacy.address == "Legacy synthetic address\n\tUnit"
    with pytest.raises(RevisionConflict):
        service.write(a, ProfileUpdate(expected_revision=1, fields={}))
    third = service.write(a, ProfileUpdate(expected_revision=2, fields={
        "full_name": "Updated through v1", "email": "new@example.invalid",
        "nationality": "Updated generic nationality", "address": "Updated generic address",
    }))
    reread = service.read_v2(a)
    assert reread.profile_id == first.profile_id == second.profile_id == third.profile_id
    assert reread.revision == 3
    assert reread.details.passport == second.details.passport
    assert reread.details.residence == second.details.residence
    assert reread.details.basics.occupation == second.details.basics.occupation
    assert reread.details.basics.full_legal_name == "Updated through v1"
    assert reread.details.contact.email == "new@example.invalid"
    assert reread.details.contact.phone_number is None
    assert reread.legacy.nationality == "Updated generic nationality"
    with pytest.raises(RevisionConflict):
        service.write_v2(a, update(2))
    assert service.read_v2(a) == reread


def test_v2_complete_snapshot_clears_omitted_values_but_preserves_legacy(storage):
    _, _, service, a, _ = storage
    service.write(a, ProfileUpdate(expected_revision=0, fields={"nationality": "Legacy only", "address": "Legacy address"}))
    first = service.write_v2(a, update(1))
    empty = ProfileDetails(basics={}, contact={}, passport={}, residence={})
    result = service.write_v2(a, ProfileV2Update(expected_revision=2, details=empty))
    assert result.details == empty
    assert result.legacy == first.legacy and result.revision == 3


def test_old_v1_valid_unicode_and_empty_date_remain_readable_in_v2(storage):
    _, _, service, a, _ = storage
    values = {
        "full_name": "Synthetic\u200d Name\u0085", "date_of_birth": "",
        "nationality": "Generic\u200f", "address": "Legacy\n\t\u200f",
        "phone_number": "Synthetic\u200d", "email": "Synthetic\u0085",
    }
    old = service.write(a, ProfileUpdate(expected_revision=0, fields=values))
    result = service.read_v2(a)
    assert result.details.basics.full_legal_name == old.fields.full_name
    assert result.details.basics.date_of_birth is None
    assert result.details.contact.phone_number == old.fields.phone_number
    assert result.details.contact.email == old.fields.email
    assert result.legacy.address == old.fields.address
    assert result.legacy.nationality == old.fields.nationality
    assert result.details.basics.current_nationality is None


def test_missing_and_conflicts_share_v1_semantics(storage):
    _, _, service, a, _ = storage
    with pytest.raises(ProfileMissing):
        service.read_v2(a)
    with pytest.raises(ProfileMissing):
        service.write_v2(a, update(1))
    first = service.write_v2(a, update())
    with pytest.raises(RevisionConflict):
        service.write_v2(a, update())
    with pytest.raises(RevisionConflict):
        service.write_v2(a, update(99))
    assert service.read_v2(a) == first


def test_accounts_sessions_and_owner_predicates_remain_shared(storage):
    store, _, service, a, b = storage
    first = service.write_v2(a, update())
    with pytest.raises(ProfileMissing):
        service.read_v2(b)
    other = details_dict()
    other["basics"]["full_legal_name"] = "Synthetic B"
    second = service.write_v2(b, update(details=other))
    assert first.profile_id != second.profile_id
    assert service.read_v2(a) == first and service.read_v2(b) == second
    for invalid in (
        {"subject": a.subject, "session_id": a.session_id},
        AuthenticatedUser(subject="", session_id=a.session_id),
        replace(a, subject=b.subject), replace(a, session_id="not-a-session"),
    ):
        with pytest.raises(StorageUnavailable):
            service.read_v2(invalid)
        with pytest.raises(StorageUnavailable):
            service.write_v2(invalid, update(1))
    with store.transaction() as connection:
        connection.execute("UPDATE local_auth_sessions SET revoked_at=? WHERE session_id=?", (NOW, a.session_id))
    with pytest.raises(StorageUnavailable):
        service.read_v2(a)
    with pytest.raises(StorageUnavailable):
        service.write_v2(a, update(1))
    assert service.read_v2(b) == second


def test_v2_session_expiry_blocks_write_before_mutation(storage):
    store, _, service, a, _ = storage
    service.write_v2(a, update())
    store.clock = lambda: NOW + 3600
    with pytest.raises(StorageUnavailable):
        service.write_v2(a, update(1))
    store.clock = lambda: NOW
    assert service.read_v2(a).revision == 1


@pytest.mark.parametrize("create_first", [False, True])
def test_failed_commit_rolls_back_v2_create_and_update_without_exposing_details(storage, create_first, caplog):
    _, transactions, service, a, _ = storage
    before = service.write_v2(a, update()) if create_first else None
    marker = "SYNTHETIC-RAW-FAILURE-MARKER"

    class FailingCommit:
        @contextmanager
        def for_user(self, user):
            with transactions.for_user(user) as connection:
                yield connection
                raise RuntimeError(marker)

    broken = ProfileService(ProfileRepository(FailingCommit()))
    with pytest.raises(StorageUnavailable) as error:
        broken.write_v2(a, update(1 if create_first else 0))
    assert str(error.value) == "" and marker not in caplog.text
    if before is None:
        with pytest.raises(ProfileMissing):
            service.read_v2(a)
    else:
        assert service.read_v2(a) == before


def test_mutated_payload_revalidated_before_storage(storage):
    _, _, service, a, _ = storage
    payload = update()
    payload.details.basics.occupation = "Synthetic\u200d"
    with pytest.raises(StorageUnavailable):
        service.write_v2(a, payload)
    with pytest.raises(ProfileMissing):
        service.read(a)


def test_closed_service_refuses_v2_reads_and_writes(storage):
    _, _, service, a, _ = storage
    service.close()
    with pytest.raises(StorageUnavailable):
        service.read_v2(a)
    with pytest.raises(StorageUnavailable):
        service.write_v2(a, update())


def test_old_schema_stays_v1_usable_until_explicit_isolated_upgrade(storage):
    store, _, service, a, _ = storage
    with store.transaction() as connection:
        connection.execute("DROP TABLE profiles")
        connection.execute(OLD_TABLE)
    reopened = LocalAuthStore(store.path, clock=lambda: NOW)
    reopened.close()
    with store.connection() as connection:
        assert "details_json" not in {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}
    first = service.write(a, ProfileUpdate(expected_revision=0, fields={"full_name": "Legacy synthetic profile", "address": "Preserve me"}))
    with pytest.raises(StorageUnavailable):
        service.read_v2(a)
    with pytest.raises(StorageUnavailable):
        service.write_v2(a, update(1))
    assert service.read(a) == first
    assert upgrade_isolated_database(store.path, confirm_isolated=True) is True
    assert upgrade_isolated_database(store.path, confirm_isolated=True) is False
    assert service.read(a) == first
    current = service.read_v2(a)
    assert current.profile_id == first.profile_id and current.revision == first.revision
    assert current.details.basics.full_legal_name == "Legacy synthetic profile"
    assert current.legacy.address == "Preserve me"
    assert service.write_v2(a, update(1)).revision == 2


@pytest.mark.parametrize("path_kind,confirmed", [("existing", False), ("relative", True), ("absent", True), ("wrong-schema", True)])
def test_isolated_upgrade_requires_explicit_confirmation_existing_absolute_expected_database(tmp_path, path_kind, confirmed):
    path = tmp_path / "isolated-only.sqlite3"
    if path_kind in {"existing", "wrong-schema"}:
        with sqlite3.connect(path) as connection:
            connection.execute(OLD_TABLE if path_kind == "existing" else "CREATE TABLE unrelated (id INTEGER)")
    target = "relative.sqlite3" if path_kind == "relative" else path
    with pytest.raises(ValueError):
        upgrade_isolated_database(target, confirm_isolated=confirmed)
    if path.exists():
        with sqlite3.connect(path) as connection:
            assert "details_json" not in {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}
    else:
        assert not path.exists()


@pytest.mark.parametrize("bad_json", ["null", "[]", "not-json", '{"contact":{"email":"duplicate@example.invalid"}}', '{"basics":{"full_legal_name":"duplicate"}}'])
def test_invalid_extension_fails_v2_closed_without_breaking_v1(storage, bad_json):
    store, _, service, a, _ = storage
    old = service.write(a, ProfileUpdate(expected_revision=0, fields={"full_name": "Synthetic A"}))
    with store.transaction() as connection:
        connection.execute("UPDATE profiles SET details_json=?", (bad_json,))
    with pytest.raises(StorageUnavailable):
        service.read_v2(a)
    assert service.read(a) == old


@pytest.mark.parametrize("group,field,limit", [
    ("basics", "full_legal_name", 120), ("basics", "nationality_at_birth", 80),
    ("basics", "current_nationality", 80), ("basics", "occupation", 120),
    ("contact", "phone_number", 32), ("contact", "email", 254),
    ("passport", "document_number", 64), ("passport", "document_type", 80),
    ("passport", "issuing_authority", 160),
    ("residence", "temporary_address_in_vietnam", 500), ("residence", "permanent_address", 500),
])
def test_text_limits_accept_boundary_and_reject_overflow(group, field, limit):
    payload = details_dict()
    payload[group][field] = "a" * limit
    assert getattr(getattr(ProfileDetails.model_validate(payload), group), field) == "a" * limit
    payload[group][field] += "a"
    with pytest.raises(ValidationError):
        ProfileDetails.model_validate(payload)


@pytest.mark.parametrize("value", ["", "2023-02-29", "2024-2-01", "2024-01-01T00:00:00", "0000-01-01", "2024-01-01\n"])
@pytest.mark.parametrize("field", ["issue_date", "expiry_date"])
def test_passport_dates_require_real_complete_iso_dates(field, value):
    payload = details_dict()
    payload["passport"][field] = value
    with pytest.raises(ValidationError):
        ProfileDetails.model_validate(payload)


def test_passport_date_order_and_optional_dates():
    payload = details_dict()
    payload["passport"].update(issue_date="2030-01-03", expiry_date="2030-01-02")
    with pytest.raises(ValidationError):
        ProfileDetails.model_validate(payload)
    payload["passport"].update(issue_date="2024-02-29", expiry_date="2024-02-29")
    assert ProfileDetails.model_validate(payload).passport.expiry_date == "2024-02-29"
    payload["passport"].update(issue_date=None, expiry_date=None)
    assert ProfileDetails.model_validate(payload).passport.issue_date is None


@pytest.mark.parametrize("value", ["M", "F", "X", "unspecified", None])
def test_document_sex_exact_supported_values(value):
    payload = details_dict()
    payload["basics"]["sex_as_on_document"] = value
    assert ProfileDetails.model_validate(payload).basics.sex_as_on_document == value


@pytest.mark.parametrize("value", ["male", "m", "", 1])
def test_document_sex_rejects_coercion(value):
    payload = details_dict()
    payload["basics"]["sex_as_on_document"] = value
    with pytest.raises(ValidationError):
        ProfileDetails.model_validate(payload)


@pytest.mark.parametrize("group,field", [
    ("basics", "nationality_at_birth"), ("basics", "current_nationality"),
    ("basics", "occupation"), ("passport", "document_number"),
    ("passport", "document_type"), ("passport", "issuing_authority"),
    ("residence", "temporary_address_in_vietnam"), ("residence", "permanent_address"),
])
@pytest.mark.parametrize("character", ["\x00", "\x7f", "\u0085", "\u200d", "\ufeff", "\ud800"])
def test_new_text_rejects_control_and_format_codepoints(group, field, character):
    payload = details_dict()
    payload[group][field] = "Synthetic" + character
    with pytest.raises(ValidationError):
        ProfileDetails.model_validate(payload)


def test_new_address_line_breaks_and_accents_are_preserved_without_flattening():
    payload = details_dict()
    payload["residence"]["temporary_address_in_vietnam"] = "Synthetic Địa chỉ\r\nLigne 2\nLigne 3"
    assert ProfileDetails.model_validate(payload).residence.temporary_address_in_vietnam == payload["residence"]["temporary_address_in_vietnam"]
    for group, field, value in [
        ("residence", "permanent_address", "Synthetic\tUnit"),
        ("basics", "occupation", "Synthetic\nRole"),
    ]:
        invalid = deepcopy(payload)
        invalid[group][field] = value
        with pytest.raises(ValidationError):
            ProfileDetails.model_validate(invalid)


@pytest.mark.parametrize("field", ["owner_subject", "subject", "profile_id", "revision", "legacy", "schema_version"])
def test_update_rejects_client_identity_and_read_only_fields(field):
    payload = {"expected_revision": 0, "details": details_dict(), field: "SYNTHETIC-UNTRUSTED"}
    with pytest.raises(ValidationError):
        ProfileV2Update.model_validate(payload)


def test_group_presence_nested_extras_and_strict_revision_are_validated():
    for group in ("basics", "contact", "passport", "residence"):
        missing = details_dict()
        del missing[group]
        with pytest.raises(ValidationError):
            ProfileDetails.model_validate(missing)
        extra = details_dict()
        extra[group]["owner_subject"] = "SYNTHETIC-UNTRUSTED"
        with pytest.raises(ValidationError):
            ProfileDetails.model_validate(extra)
    for revision in (True, "1", -1, 1.5):
        with pytest.raises(ValidationError):
            ProfileV2Update.model_validate({"expected_revision": revision, "details": details_dict()})
    assert set(ProfileFields.model_fields) == {"full_name", "date_of_birth", "nationality", "address", "phone_number", "email"}
    with pytest.raises(ValidationError):
        ProfileV2Response(profile_id="synthetic", revision=1, details=details_dict(), legacy={}, schema_version="profile.v1")
