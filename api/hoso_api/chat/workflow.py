"""Read Vincent's exact pinned draft; do not derive a competing field schema."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata


WORKFLOW_SHA256 = "50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3"
PROCEDURE_CODE = "1.001146"
ASSET_PATH = Path(__file__).with_name("assets") / "na5-workflow.json"


class InvalidDraft(ValueError):
    pass


def load_workflow() -> dict:
    raw = ASSET_PATH.read_bytes()
    if sha256(raw).hexdigest() != WORKFLOW_SHA256:
        raise RuntimeError("Pinned workflow hash does not match.")
    workflow = json.loads(raw)
    if workflow["procedure_code"] != PROCEDURE_CODE or len(workflow["fields"]) != 43 or workflow["review_status"] != "draft":
        raise RuntimeError("Pinned workflow identity does not match.")
    return workflow


WORKFLOW = load_workflow()
FIELDS = {field["id"]: field for field in WORKFLOW["fields"]}
FIXED_VALUES = dict(WORKFLOW["fixed_values"])


def active(field: dict, values: dict[str, str | None]) -> bool:
    return not field.get("inactive", False) and all(values.get(key) == expected for key, expected in field.get("when", {}).items())


def editable(field: dict, values: dict[str, str | None]) -> bool:
    return active(field, values) and not field.get("manual", False) and field["type"] != "manual" and field["id"] not in FIXED_VALUES


def validate_value(field: dict, value: str | None) -> None:
    if value is None or value == "":
        return
    if not isinstance(value, str) or len(value) > field["max_length"]:
        raise InvalidDraft("Invalid value length or type.")
    if not value.strip():
        raise InvalidDraft("Whitespace is not a field value.")
    allowed_controls = {"\n", "\t"} if field.get("multiline", False) else set()
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in allowed_controls for char in value):
        raise InvalidDraft("Invalid control character.")
    if field["type"] == "choice" and value not in field["options"]:
        raise InvalidDraft("Invalid choice.")
    if field["type"] == "date":
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise InvalidDraft("Use a complete ISO date.")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise InvalidDraft("Invalid calendar date.") from None


def validate_draft(values: dict[str, str | None]) -> dict[str, str | None]:
    if set(values) - set(FIELDS):
        raise InvalidDraft("Unknown workflow field.")
    effective = {**FIXED_VALUES, **values}
    if any(effective.get(key) != fixed for key, fixed in FIXED_VALUES.items()):
        raise InvalidDraft("Fixed workflow value cannot change.")
    for key, value in values.items():
        validate_value(FIELDS[key], value)
        if value not in (None, "") and not active(FIELDS[key], effective):
            raise InvalidDraft("Inactive branch values must be cleared.")
    return effective


def next_missing(values: dict[str, str | None]) -> str | None:
    return next((field["id"] for field in WORKFLOW["fields"] if field.get("required", False)
                 and editable(field, values) and not values.get(field["id"])), None)


def question(field_id: str, *, clarify: bool = False) -> str:
    field = FIELDS[field_id]
    prefix = "Please clarify: " if clarify else ""
    if field["type"] == "choice":
        return prefix + f"Which {field['label']} applies: {' or '.join(field['options'])}?"
    if field["type"] == "date":
        return prefix + f"What is your {field['label']} (YYYY-MM-DD)?"
    return prefix + f"What is your {field['label']}?"


def schema_response() -> dict:
    return {
        "procedure_code": PROCEDURE_CODE,
        "schema_version": WORKFLOW_SHA256,
        "review_status": "draft",
        "fixed_values": dict(FIXED_VALUES),
        "fields": deepcopy(WORKFLOW["fields"]),
    }
