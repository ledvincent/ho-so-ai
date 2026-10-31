"""Synthetic, offline deterministic proposals. No profile/form write or model call."""

from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from hoso_api.chat.workflow import FIELDS, FIXED_VALUES, WORKFLOW, WORKFLOW_SHA256
from hoso_api.portal.repository import ProfileRepository, RevisionConflict
from hoso_api.profile_prefill import PrefillRequest, PrefillUnsupported, build_prefill
from hoso_api.profile_v2_models import ProfileV2Response


def profile(sources=None, legacy=None):
    groups = {key: {} for key in ("basics", "contact", "passport", "residence")}
    for path, value in (sources or {}).items():
        group, key = path.split(".", 1)
        groups[group][key] = value
    return ProfileV2Response(profile_id="synthetic-profile-a", revision=3,
                             details=groups, legacy=legacy or {})


def request(**overrides):
    return PrefillRequest.model_validate({
        "consent": True, "applicant_confirmed": True, "expected_revision": 3,
        "request_id": "synthetic-generation-1", "draft_revision": 4,
        "procedure_code": "1.001146", "form_sha256": WORKFLOW["form_sha256"],
        "schema_version": WORKFLOW_SHA256, "values": dict(FIXED_VALUES), **overrides,
    })


def dense_profile():
    return profile({
        "basics.full_legal_name": "Nguyễn Synthetic Demo",
        "basics.date_of_birth": "1995-06-15", "basics.sex_as_on_document": "M",
        "basics.nationality_at_birth": "Synthetic birth nationality",
        "basics.current_nationality": "Synthetic current nationality", "basics.occupation": "Synthetic occupation",
        "contact.phone_number": "+00 000 000 000", "contact.email": "synthetic@example.invalid",
        "passport.document_number": "SYNTHETIC-0001", "passport.document_type": "Synthetic ordinary passport",
        "passport.issue_date": "2020-01-01", "passport.expiry_date": "2035-01-01",
        "passport.issuing_authority": "Synthetic authority",
        "residence.temporary_address_in_vietnam": "12 Synthetic Street, Vietnam",
        "residence.permanent_address": "UNMAPPED-PRIVATE-PERMANENT-ADDRESS",
    }, {"nationality": "UNMAPPED-PRIVATE-LEGACY-NATIONALITY", "address": "UNMAPPED-PRIVATE-LEGACY-ADDRESS"})


def test_exact_fields_limits_and_mapping_without_cross_person_or_travel_defaults():
    result = build_prefill(dense_profile(), request())
    by_target = {item.target_field: item for item in result.proposals}
    assert len(result.proposals) == 14
    assert set(by_target) == {"applicant_full_name", "birth_date", "sex", "birth_nationality", "current_nationality", "occupation",
                              "passport_number", "passport_type", "passport_issuer", "passport_expiry", "residential_address", "contact"}
    assert by_target["applicant_full_name"].value == "NGUYỄN SYNTHETIC DEMO"
    assert by_target["applicant_full_name"].source_values == {"basics.full_legal_name": "Nguyễn Synthetic Demo"}
    assert by_target["applicant_full_name"].mapping == "uppercase"
    assert by_target["birth_date"].value == "1995-06-15"
    assert by_target["sex"].value == "male"
    assert by_target["birth_nationality"].value == "Synthetic birth nationality"
    assert by_target["current_nationality"].value == "Synthetic current nationality"
    assert all(item.target_field not in {"entry_date", "entry_port", "entry_purpose", "permitted_until", "extension_until", "request_type", "signed_on", "place_signed"} for item in result.proposals)
    assert all(not item.target_field.startswith(("sponsor_", "organisation_")) for item in result.proposals)
    assert len({item.proposal_id for item in result.proposals}) == len(result.proposals)
    assert all(len(item.value) <= FIELDS[item.target_field]["max_length"] for item in result.proposals)


def test_response_echoes_the_exact_profile_draft_document_and_schema_snapshot():
    result = build_prefill(profile(), request())
    assert result.model_dump() == {
        "request_id": "synthetic-generation-1", "draft_revision": 4,
        "procedure_code": "1.001146", "form_sha256": WORKFLOW["form_sha256"], "schema_version": WORKFLOW_SHA256,
        "profile_id": "synthetic-profile-a", "profile_revision": 3, "review_status": "draft", "proposals": [], "unmapped": [],
    }


@pytest.mark.parametrize("field", ["consent", "applicant_confirmed"])
@pytest.mark.parametrize("value", [False, 1, 0, "true", None])
def test_both_consents_must_be_explicit_literal_boolean_true(field, value):
    with pytest.raises(ValidationError):
        request(**{field: value})


@pytest.mark.parametrize("field", ["consent", "applicant_confirmed"])
def test_missing_consent_is_not_an_opt_in(field):
    payload = request().model_dump()
    del payload[field]
    with pytest.raises(ValidationError):
        PrefillRequest.model_validate(payload)


@pytest.mark.parametrize("updates", [
    {"request_id": "unsafe id"}, {"request_id": "x" * 81}, {"request_id": ""},
    {"draft_revision": -1}, {"draft_revision": True}, {"expected_revision": 0}, {"expected_revision": True},
    {"profile_id": "synthetic-client-selected-profile"}, {"values": {"birth_date": 20000101}},
])
def test_strict_request_bounds_reject_extra_identity_and_coerced_types(updates):
    with pytest.raises(ValidationError):
        request(**updates)


@pytest.mark.parametrize("updates", [
    {"procedure_code": "1.004194"}, {"form_sha256": "f" * 64}, {"schema_version": "e" * 64},
])
def test_other_procedures_forms_or_workflow_versions_are_unsupported(updates):
    with pytest.raises(PrefillUnsupported) as failure:
        build_prefill(dense_profile(), request(**updates))
    assert str(failure.value) == ""


def test_stale_profile_revision_uses_existing_conflict_without_values_in_errors():
    with pytest.raises(RevisionConflict) as failure:
        build_prefill(dense_profile(), request(expected_revision=2))
    assert str(failure.value) == ""


@pytest.mark.parametrize("values", [
    {"unknown": "synthetic-private-draft"}, {"request_type": "visa_issuance"},
    {"host_type": "family", "organisation_name": "synthetic-private-draft"},
    {"host_type": "organisation", "sponsor_full_name": "synthetic-private-draft"},
    {"host_type": "family", "sponsor_kind": "vietnamese_citizen", "sponsor_card_number": "synthetic-private-draft"},
    {"birth_date": "2026-02-30"},
])
def test_invalid_unknown_or_stale_inactive_drafts_fail_without_echo(values):
    with pytest.raises(ValueError) as failure:
        build_prefill(dense_profile(), request(values=values))
    assert str(failure.value) == "Profile or draft values are invalid."
    assert "synthetic-private-draft" not in str(failure.value)


@pytest.mark.parametrize("source,target,value", [
    ("basics.full_legal_name", "applicant_full_name", "X" * 101),
    ("basics.nationality_at_birth", "birth_nationality", "X" * 51),
    ("basics.current_nationality", "current_nationality", "X" * 51),
    ("basics.occupation", "occupation", "X" * 101),
    ("passport.document_number", "passport_number", "X" * 31),
    ("passport.document_type", "passport_type", "X" * 51),
    ("passport.issuing_authority", "passport_issuer", "X" * 101),
    ("residence.temporary_address_in_vietnam", "residential_address", "X" * 251),
    ("contact.email", "contact", "x" * 151),
])
def test_valid_profile_values_over_target_limit_are_unmapped_never_truncated(source, target, value):
    saved = profile({source: value})
    result = build_prefill(saved, request())
    assert not any(item.target_field == target for item in result.proposals)
    assert [(item.source_field, item.reason) for item in result.unmapped] == [(source, "target_value_too_long")]
    group, key = source.split(".")
    assert getattr(getattr(saved.details, group), key) == value


def test_uppercase_expansion_is_measured_after_transformation_and_preserves_source():
    saved = profile({"basics.full_legal_name": "ß" * 51})
    result = build_prefill(saved, request())
    assert result.proposals == []
    assert result.unmapped[0].reason == "target_value_too_long"
    assert saved.details.basics.full_legal_name == "ß" * 51
    accepted = build_prefill(profile({"basics.full_legal_name": "é" * 100}), request())
    assert accepted.proposals[0].value == "É" * 100


@pytest.mark.parametrize("value,expected", [("M", "male"), ("F", "female"), ("X", None), ("unspecified", None)])
def test_document_sex_has_only_explicit_M_F_mappings(value, expected):
    result = build_prefill(profile({"basics.sex_as_on_document": value}), request())
    if expected:
        assert [(item.target_field, item.value, item.mapping) for item in result.proposals] == [("sex", expected, "document_sex")]
    else:
        assert result.proposals == []
        assert [(item.source_field, item.reason) for item in result.unmapped] == [("basics.sex_as_on_document", "unsupported_sex")]


def test_permanent_issue_date_and_ambiguous_legacy_values_never_fill_any_other_field():
    saved = profile({"passport.issue_date": "2020-01-01", "residence.permanent_address": "synthetic-private-permanent"},
                    {"nationality": "synthetic-private-nationality", "address": "synthetic-private-address"})
    result = build_prefill(saved, request())
    assert result.proposals == []
    assert {(item.source_field, item.reason) for item in result.unmapped} == {
        ("passport.issue_date", "no_matching_applicant_field"), ("residence.permanent_address", "no_matching_applicant_field"),
        ("legacy.nationality", "legacy_meaning_ambiguous"), ("legacy.address", "legacy_meaning_ambiguous"),
    }
    assert "synthetic-private" not in result.model_dump_json()


def test_multiline_address_is_not_silently_flattened():
    saved = profile({"residence.temporary_address_in_vietnam": "Synthetic line one\nSynthetic line two"})
    result = build_prefill(saved, request())
    assert result.proposals == []
    assert result.unmapped[0].reason == "target_multiline_not_supported"
    assert "\n" in saved.details.residence.temporary_address_in_vietnam


def test_contact_proposals_are_three_explicit_alternatives_with_distinct_sources():
    result = build_prefill(profile({"contact.phone_number": "+00 000 000", "contact.email": "synthetic@example.invalid"}), request())
    assert [(item.mapping, item.value) for item in result.proposals] == [
        ("phone_only", "+00 000 000"), ("email_only", "synthetic@example.invalid"), ("phone_email", "+00 000 000 / synthetic@example.invalid"),
    ]
    assert {item.target_field for item in result.proposals} == {"contact"}
    assert result.proposals[2].source_fields == ["contact.phone_number", "contact.email"]
    assert result.proposals[2].source_values == {"contact.phone_number": "+00 000 000", "contact.email": "synthetic@example.invalid"}


def test_overlong_combination_keeps_individual_contact_alternatives_without_joining():
    result = build_prefill(profile({"contact.phone_number": "1" * 32, "contact.email": "e" * 120}), request())
    assert [item.mapping for item in result.proposals] == ["phone_only", "email_only"]
    assert result.unmapped == []


def test_invalid_shared_whitespace_does_not_create_a_combined_contact():
    result = build_prefill(profile({"contact.phone_number": " ", "contact.email": "synthetic@example.invalid"}), request())
    assert [item.mapping for item in result.proposals] == ["email_only"]
    assert [(item.source_field, item.reason) for item in result.unmapped] == [("contact.phone_number", "target_validation_failed")]


def test_existing_values_are_reported_and_only_different_nonempty_values_need_overwrite():
    result = build_prefill(profile({"basics.full_legal_name": "Synthetic Name", "basics.date_of_birth": "1995-06-15", "contact.phone_number": "000"}),
                           request(values={**FIXED_VALUES, "applicant_full_name": "EXISTING NAME", "birth_date": "1995-06-15", "contact": ""}))
    by_target = {item.target_field: item for item in result.proposals}
    assert (by_target["applicant_full_name"].existing_value, by_target["applicant_full_name"].requires_overwrite) == ("EXISTING NAME", True)
    assert by_target["birth_date"].requires_overwrite is False
    assert by_target["contact"].requires_overwrite is False


@pytest.mark.parametrize("changes", [{"manual": True}, {"when": {"host_type": "family"}}, {"inactive": True}])
def test_even_a_known_target_must_be_active_editable_and_nonmanual(monkeypatch, changes):
    monkeypatch.setitem(FIELDS, "occupation", {**FIELDS["occupation"], **changes})
    result = build_prefill(profile({"basics.occupation": "Synthetic occupation"}), request())
    assert result.proposals == []
    assert result.unmapped[0].reason == "target_not_editable"


def test_pure_mapping_is_deterministic_and_does_not_mutate_read_or_write_or_call_a_model(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Prefill must not access storage or network.")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    monkeypatch.setattr(ProfileRepository, "read", forbidden)
    monkeypatch.setattr(ProfileRepository, "write", forbidden)
    saved, payload = dense_profile(), request()
    before_profile, before_request, before_fields = saved.model_dump(), payload.model_dump(), deepcopy(FIELDS)
    first = build_prefill(saved, payload)
    assert build_prefill(saved, payload) == first
    assert saved.model_dump() == before_profile
    assert payload.model_dump() == before_request
    assert FIELDS == before_fields


def test_mutated_internal_consent_and_bad_saved_values_fail_without_private_error_text():
    payload = request()
    payload.applicant_confirmed = False
    with pytest.raises(ValueError, match="Explicit consent and applicant confirmation are required"):
        build_prefill(profile(), payload)
    saved = profile()
    saved.details.basics.full_legal_name = "synthetic-private-marker" * 20
    with pytest.raises(ValueError) as failure:
        build_prefill(saved, request())
    assert str(failure.value) == "Profile or draft values are invalid."
    assert "synthetic-private-marker" not in str(failure.value)
