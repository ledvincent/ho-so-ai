"""The narrow CHAT-01 request/response, independent of account profile storage."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .workflow import FIELDS, InvalidDraft, PROCEDURE_CODE, validate_draft


class AssistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    request_id: Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")]
    draft_revision: Annotated[int, Field(ge=0, strict=True)]
    procedure_code: Literal["1.001146"]
    intent: Literal["form_answer", "procedure_question"]
    message: Annotated[str, Field(max_length=2000)] = ""
    focus_field: str | None = None
    values: dict[str, str | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_workflow_context(self):
        if self.focus_field is not None and self.focus_field not in FIELDS:
            raise ValueError("Unknown focus field.")
        try:
            validate_draft(self.values)
        except InvalidDraft:
            raise ValueError("Invalid draft values for the active workflow.") from None
        return self


class ProposedChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field_id: str
    value: str


class AssistResponse(BaseModel):
    request_id: str
    draft_revision: int
    procedure_code: Literal["1.001146"] = PROCEDURE_CODE
    schema_version: str
    status: Literal["proposed", "needs_clarification", "question", "complete"]
    assistant_text: str
    proposed_changes: list[ProposedChange]
    next_field: str | None
    review_status: Literal["draft"] = "draft"


class EvidenceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    field_id: Annotated[str, Field(min_length=1, max_length=80)]
    value: Annotated[str, Field(min_length=1, max_length=600)]
    evidence: Annotated[str, Field(min_length=1, max_length=2000)]


class ProviderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    ambiguous: bool
    proposals: Annotated[list[EvidenceProposal], Field(max_length=1)]
