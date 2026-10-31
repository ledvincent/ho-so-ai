"""Deterministic, consented NA5 draft proposals; no persistence or model access."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .chat.workflow import FIELDS, PROCEDURE_CODE, WORKFLOW, WORKFLOW_SHA256, InvalidDraft, editable, validate_draft, validate_value
from .portal.repository import RevisionConflict
from .profile_prefill_compat import supports_prefill_schema, validate_compatible_date_order
from .profile_v2_models import ProfileV2Response


class PrefillUnsupported(Exception):
    """The requested form/workflow is outside this exact approved consumer seam."""


class PrefillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    consent: Literal[True]
    applicant_confirmed: Literal[True]
    expected_revision: Annotated[int, Field(ge=1, strict=True)]
    request_id: Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")]
    draft_revision: Annotated[int, Field(ge=0, strict=True)]
    procedure_code: Annotated[str, Field(pattern=r"^[0-9]\.[0-9]{6}$")]
    form_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    schema_version: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    values: Annotated[dict[str, str | None], Field(max_length=43)]

    @field_validator("consent", "applicant_confirmed", mode="before")
    @classmethod
    def explicit_true_only(cls, value):
        # Literal[True] alone can accept integer 1; consent must be an actual bool.
        if value is not True:
            raise ValueError("Explicit confirmation is required.")
        return value


Mapping = Literal["direct", "uppercase", "document_sex", "phone_only", "email_only", "phone_email"]
UnmappedReason = Literal[
    "unsupported_sex", "no_matching_applicant_field", "legacy_meaning_ambiguous",
    "target_value_too_long", "target_multiline_not_supported", "target_validation_failed", "target_not_editable",
]


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    proposal_id: str
    source_fields: Annotated[list[str], Field(min_length=1, max_length=2)]
    source_values: dict[str, str]
    target_field: str
    value: str
    mapping: Mapping
    existing_value: str | None
    requires_overwrite: bool


class Unmapped(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    source_field: str
    reason: UnmappedReason


class PrefillResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    request_id: str
    draft_revision: int
    procedure_code: str
    form_sha256: str
    schema_version: str
    profile_id: str
    profile_revision: int
    review_status: Literal["draft"] = "draft"
    proposals: list[Proposal]
    unmapped: list[Unmapped]


# Source paths are relative to `details`, except the explicitly named legacy group.
_DIRECT = (
    ("basics.date_of_birth", "birth_date"),
    ("basics.nationality_at_birth", "birth_nationality"),
    ("basics.current_nationality", "current_nationality"),
    ("basics.occupation", "occupation"),
    ("passport.document_number", "passport_number"),
    ("passport.document_type", "passport_type"),
    ("passport.issuing_authority", "passport_issuer"),
    ("passport.expiry_date", "passport_expiry"),
    ("residence.temporary_address_in_vietnam", "residential_address"),
)


def build_prefill(profile: ProfileV2Response, payload: PrefillRequest) -> PrefillResponse:
    """Inspect a caller-owned snapshot and return proposals without changing it.

    The route owns authentication, profile retrieval and response privacy. This
    function neither reads account storage nor sends any values to another service.
    """
    if payload.consent is not True or payload.applicant_confirmed is not True:
        raise ValueError("Explicit consent and applicant confirmation are required.")
    if (payload.procedure_code != PROCEDURE_CODE or payload.form_sha256 != WORKFLOW["form_sha256"]
            or not supports_prefill_schema(payload.schema_version) or WORKFLOW["review_status"] != "draft" or len(FIELDS) != 43):
        raise PrefillUnsupported()
    if profile.revision != payload.expected_revision:
        raise RevisionConflict()
    try:
        saved = ProfileV2Response.model_validate(profile.model_dump())
        values = validate_draft(payload.values)
        validate_compatible_date_order(payload.schema_version, values)
    except (ValidationError, InvalidDraft, TypeError, ValueError):
        raise ValueError("Profile or draft values are invalid.") from None

    details = saved.details.model_dump()
    proposals: list[Proposal] = []
    unmapped: list[Unmapped] = []
    recorded_unmapped: set[tuple[str, str]] = set()

    def read(path: str) -> str | None:
        group, key = path.split(".", 1)
        return details[group][key]

    def exclude(path: str, reason: UnmappedReason) -> None:
        if (path, reason) not in recorded_unmapped:
            unmapped.append(Unmapped(source_field=path, reason=reason))
            recorded_unmapped.add((path, reason))

    def propose(paths: list[str], target: str, value: str, mapping: Mapping, *, combined=False) -> None:
        field = FIELDS.get(target)
        reason: UnmappedReason | None = None
        if field is None or not editable(field, values):
            reason = "target_not_editable"
        elif len(value) > field["max_length"]:
            reason = "target_value_too_long"
        elif not field.get("multiline", False) and any(character in value for character in "\n\r\t\v\f\u0085\u2028\u2029"):
            reason = "target_multiline_not_supported"
        else:
            try:
                validate_value(field, value)
                if not value.strip():
                    raise InvalidDraft()
            except InvalidDraft:
                reason = "target_validation_failed"
        if reason:
            # Combined contact is optional: valid individual alternatives remain
            # mapped even when their concatenation cannot fit the one target.
            if not combined:
                for path in paths:
                    exclude(path, reason)
            return
        existing = payload.values.get(target)
        proposal_id = "na5:contact.phone_email" if combined else "na5:" + paths[0]
        proposals.append(Proposal(
            proposal_id=proposal_id, source_fields=paths,
            source_values={path: read(path) for path in paths},
            target_field=target, value=value, mapping=mapping,
            existing_value=existing,
            requires_overwrite=existing not in (None, "") and existing != value,
        ))

    legal_name = read("basics.full_legal_name")
    if legal_name not in (None, ""):
        propose(["basics.full_legal_name"], "applicant_full_name", legal_name.upper(), "uppercase")
    for path, target in _DIRECT:
        value = read(path)
        if value not in (None, ""):
            propose([path], target, value, "direct")
    document_sex = read("basics.sex_as_on_document")
    if document_sex in {"M", "F"}:
        propose(["basics.sex_as_on_document"], "sex", {"M": "male", "F": "female"}[document_sex], "document_sex")
    elif document_sex not in (None, ""):
        exclude("basics.sex_as_on_document", "unsupported_sex")

    phone, email = read("contact.phone_number"), read("contact.email")
    if phone not in (None, ""):
        propose(["contact.phone_number"], "contact", phone, "phone_only")
    if email not in (None, ""):
        propose(["contact.email"], "contact", email, "email_only")
    contact_alternatives = {proposal.mapping for proposal in proposals if proposal.target_field == "contact"}
    if "phone_only" in contact_alternatives and "email_only" in contact_alternatives:
        propose(["contact.phone_number", "contact.email"], "contact", phone + " / " + email, "phone_email", combined=True)

    for path in ("passport.issue_date", "residence.permanent_address"):
        if read(path) not in (None, ""):
            exclude(path, "no_matching_applicant_field")
    for key, value in saved.legacy.model_dump().items():
        if value not in (None, ""):
            exclude("legacy." + key, "legacy_meaning_ambiguous")
    field_order = {field_id: position for position, field_id in enumerate(FIELDS)}
    proposals.sort(key=lambda proposal: field_order[proposal.target_field])
    return PrefillResponse(
        request_id=payload.request_id, draft_revision=payload.draft_revision,
        procedure_code=payload.procedure_code, form_sha256=payload.form_sha256,
        schema_version=payload.schema_version,
        profile_id=saved.profile_id, profile_revision=saved.revision,
        proposals=proposals, unmapped=unmapped,
    )
