"""Exact e162 bridge regression using public schemas and fictional profile data."""

from copy import deepcopy
from hashlib import sha256

import pytest

from hoso_api.chat.workflow import ASSET_PATH as LEGACY_ASSET, FIXED_VALUES, WORKFLOW, WORKFLOW_SHA256, schema_response
from hoso_api.portal.repository import RevisionConflict
from hoso_api.profile_prefill import PrefillRequest, PrefillUnsupported, build_prefill
from hoso_api.profile_prefill_compat import (
    ASSET_PATH, DATE_ORDER, DOCUMENT_ID, DOCUMENT_SCHEMA_SHA256,
    DOCUMENT_TEMPLATE_VERSION, ORIGINAL_SHA256, load_document_schema,
    supports_prefill_schema, verify_document_compatibility,
)
from hoso_api.profile_v2_models import ProfileV2Response


def profile():
    return ProfileV2Response(profile_id="synthetic-compat-profile", revision=3, details={
        "basics": {"full_legal_name": "Nguyễn Synthetic Demo", "date_of_birth": "1995-06-15"},
        "contact": {"email": "synthetic@example.invalid"},
        "passport": {"expiry_date": "2035-01-01"}, "residence": {},
    }, legacy={})


def request(**updates):
    return PrefillRequest.model_validate({
        "consent": True, "applicant_confirmed": True, "expected_revision": 3,
        "request_id": "synthetic-compat-1", "draft_revision": 4,
        "procedure_code": "1.001146", "form_sha256": ORIGINAL_SHA256,
        "schema_version": DOCUMENT_TEMPLATE_VERSION, "values": dict(FIXED_VALUES),
        **updates,
    })


def test_exact_public_document_bytes_identity_and_comparison_are_pinned():
    document = load_document_schema()
    before_document, before_legacy = deepcopy(document), deepcopy(WORKFLOW)
    assert sha256(ASSET_PATH.read_bytes()).hexdigest() == DOCUMENT_SCHEMA_SHA256
    assert document["document_id"] == DOCUMENT_ID
    assert document["template_version"] == DOCUMENT_TEMPLATE_VERSION
    assert document["template_sha256"] == ORIGINAL_SHA256
    assert len(document["fields"]) == 43
    assert document["download_available"] is False
    verify_document_compatibility(document, WORKFLOW)
    assert document == before_document and WORKFLOW == before_legacy


def test_legacy_bytes_chat_schema_and_response_are_unchanged_for_new_bridge():
    assert WORKFLOW_SHA256 == "50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3"
    assert sha256(LEGACY_ASSET.read_bytes()).hexdigest() == WORKFLOW_SHA256
    assert schema_response()["schema_version"] == WORKFLOW_SHA256
    assert not any("uppercase" in field for field in WORKFLOW["fields"])
    old = build_prefill(profile(), request(schema_version=WORKFLOW_SHA256)).model_dump()
    new = build_prefill(profile(), request()).model_dump()
    assert old["schema_version"] == WORKFLOW_SHA256
    assert new["schema_version"] == DOCUMENT_TEMPLATE_VERSION
    new["schema_version"] = WORKFLOW_SHA256
    assert new == old
    assert next(item["value"] for item in old["proposals"] if item["target_field"] == "applicant_full_name") == "NGUYỄN SYNTHETIC DEMO"


@pytest.mark.parametrize("version", [
    "e" * 64, DOCUMENT_SCHEMA_SHA256,
    "ddb9c985573e0245d0c52588b0c74685c613a9a0aef668a2416da92697a3115c",
])
def test_unknown_and_raw_file_hashes_are_not_document_template_versions(version):
    assert not supports_prefill_schema(version)
    with pytest.raises(PrefillUnsupported):
        build_prefill(profile(), request(schema_version=version))


@pytest.mark.parametrize("updates", [{"procedure_code": "1.004194"}, {"form_sha256": "f" * 64}])
def test_exact_template_version_does_not_authorize_other_procedure_or_original(updates):
    with pytest.raises(PrefillUnsupported):
        build_prefill(profile(), request(**updates))


@pytest.mark.parametrize("key,value", [
    ("label", "Changed label"), ("max_length", 99), ("type", "date"),
    ("manual", True), ("inactive", True), ("when", {"host_type": "family"}),
    ("options", ["Changed option"]), ("uppercase", False),
])
def test_any_unproven_field_change_fails_compatibility(key, value):
    document = load_document_schema()
    document["fields"][0][key] = value
    with pytest.raises(RuntimeError, match="Pinned document compatibility does not match"):
        verify_document_compatibility(document, WORKFLOW)


@pytest.mark.parametrize("mutation", ["extra-uppercase", "reorder", "remove", "new-field"])
def test_only_applicant_uppercase_annotation_and_exact_43_ordered_fields_are_allowed(mutation):
    document = load_document_schema()
    if mutation == "extra-uppercase":
        document["fields"][1]["uppercase"] = True
    elif mutation == "reorder":
        document["fields"][0], document["fields"][1] = document["fields"][1], document["fields"][0]
    elif mutation == "remove":
        document["fields"].pop()
    else:
        document["fields"][-1] = {**document["fields"][-1], "id": "unsupported_field"}
    with pytest.raises(RuntimeError):
        verify_document_compatibility(document, WORKFLOW)


@pytest.mark.parametrize("key,value", [
    ("document_id", "other-document"), ("procedure_code", "1.004194"), ("form_id", "OTHER"),
    ("template_sha256", "e" * 64), ("template_version", "e" * 64),
    ("review_status", "reviewed"), ("applicability", "accepted"), ("download_available", True),
    ("revision", "other-revision"), ("effective_from", "2000-01-01"), ("page_count", 1),
    ("date_order", []), ("fixed_values", {}),
])
def test_different_document_identity_or_extra_contract_rules_fail_closed(key, value):
    document = load_document_schema()
    document[key] = value
    with pytest.raises(RuntimeError):
        verify_document_compatibility(document, WORKFLOW)


def test_changed_public_schema_bytes_fail_even_if_json_semantics_match(tmp_path):
    changed = tmp_path / "changed-public-schema.json"
    changed.write_bytes(ASSET_PATH.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="Pinned document schema hash does not match"):
        load_document_schema(changed)


@pytest.mark.parametrize("earlier,later", DATE_ORDER)
def test_new_draft_enforces_each_present_date_pair_with_generic_error(earlier, later):
    values = {**FIXED_VALUES, earlier: "2030-01-02", later: "2030-01-01"}
    with pytest.raises(ValueError) as failure:
        build_prefill(profile(), request(values=values))
    assert str(failure.value) == "Profile or draft values are invalid."
    assert "2030" not in str(failure.value)
    # Existing callers retain their previous partial-draft behavior.
    assert build_prefill(profile(), request(schema_version=WORKFLOW_SHA256, values=values)).schema_version == WORKFLOW_SHA256


@pytest.mark.parametrize("values", [
    {}, {"birth_date": "1995-06-15"}, {"entry_date": "2026-01-01"},
    {"birth_date": "2026-01-01", "entry_date": "2026-01-01"},
    {"birth_date": "1995-06-15", "entry_date": "2026-01-01", "permitted_until": "2026-02-01",
     "extension_until": "2026-03-01", "passport_expiry": "2035-01-01"},
])
def test_new_partial_equal_or_ordered_drafts_are_supported_without_mutation(values):
    payload = request(values={**FIXED_VALUES, **values})
    saved = profile()
    before = saved.model_dump(), payload.model_dump()
    assert build_prefill(saved, payload).schema_version == DOCUMENT_TEMPLATE_VERSION
    assert (saved.model_dump(), payload.model_dump()) == before


def test_new_document_still_requires_current_caller_owned_profile_revision():
    with pytest.raises(RevisionConflict):
        build_prefill(profile(), request(expected_revision=2))
