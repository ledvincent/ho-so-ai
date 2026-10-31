"""Code-owned question selection and proposal validation; no profile persistence."""

import re

from pydantic import ValidationError

from .provider import AssistantInvalidOutput, AssistantProvider, AssistantTimeout, AssistantUnavailable
from .schemas import AssistRequest, AssistResponse, ProposedChange, ProviderOutput
from .workflow import FIELDS, InvalidDraft, WORKFLOW_SHA256, editable, next_missing, question, validate_draft, validate_value


def _response(request: AssistRequest, status: str, text: str, next_field: str | None,
              changes: list[ProposedChange] | None = None) -> AssistResponse:
    return AssistResponse(request_id=request.request_id, draft_revision=request.draft_revision,
                          schema_version=WORKFLOW_SHA256, status=status, assistant_text=text,
                          proposed_changes=changes or [], next_field=next_field)


def assist(request: AssistRequest, provider: AssistantProvider | None) -> AssistResponse:
    values = validate_draft(request.values)
    selected = request.focus_field or next_missing(values)
    if selected is None:
        return _response(request, "complete", "The active workflow fields are complete. Review the draft and complete any signatures manually.", None)
    field = FIELDS[selected]
    if not editable(field, values):
        next_field = next_missing(values)
        text = "This field is fixed, manual, or outside the active branch."
        if next_field:
            text += " " + question(next_field)
        return _response(request, "needs_clarification", text, next_field)
    if not request.message.strip():
        return _response(request, "question", question(selected), selected)
    if field["type"] == "date" and len(set(re.findall(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b", request.message))) > 1:
        return _response(request, "needs_clarification", question(selected, clarify=True), selected)
    if field["type"] == "choice" and sum(bool(re.search(r"(?<!\w)" + re.escape(option) + r"(?!\w)", request.message, re.IGNORECASE)) for option in field["options"]) > 1:
        return _response(request, "needs_clarification", question(selected, clarify=True), selected)
    if provider is None:
        raise AssistantUnavailable()
    # Intentionally omit all existing values, identity and the complete workflow.
    metadata = {key: field[key] for key in ("id", "label", "type", "max_length", "multiline", "options") if key in field}
    try:
        raw = provider.propose(metadata, request.message)
        output = ProviderOutput.model_validate(raw)
    except (AssistantTimeout, AssistantUnavailable, AssistantInvalidOutput):
        raise
    except ValidationError:
        raise AssistantInvalidOutput() from None
    except Exception:
        raise AssistantUnavailable() from None
    if output.ambiguous or not output.proposals:
        return _response(request, "needs_clarification", question(selected, clarify=True), selected)
    proposal = output.proposals[0]
    if proposal.field_id != selected or not editable(FIELDS.get(proposal.field_id, {}), values):
        raise AssistantInvalidOutput()
    # Match complete tokens: e.g. "male" must not be accepted from "female".
    if proposal.evidence not in request.message or not re.search(r"(?<!\w)" + re.escape(proposal.value) + r"(?!\w)", proposal.evidence):
        raise AssistantInvalidOutput()
    try:
        validate_value(field, proposal.value)
    except InvalidDraft:
        raise AssistantInvalidOutput() from None
    if not proposal.value.strip():
        raise AssistantInvalidOutput()
    proposed_values = {**values, selected: proposal.value}
    next_field = next_missing(proposed_values)
    text = "A proposed value is ready for your review."
    if next_field:
        text += " " + question(next_field)
    else:
        text += " Review the completed draft and complete signatures manually."
    return _response(request, "proposed", text, next_field, [ProposedChange(field_id=selected, value=proposal.value)])
