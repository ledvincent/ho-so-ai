"""Explicit, hash-pinned NA5 document compatibility for profile proposals only."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from .chat.workflow import InvalidDraft, PROCEDURE_CODE, WORKFLOW, WORKFLOW_SHA256


DOCUMENT_ID = "na5-provincial-stay-extension"
DOCUMENT_SCHEMA_SHA256 = "ee00fc00c540cd53eca1b762ef8c2e7cdece87122d97f2bb05e97caed78a3e6f"
DOCUMENT_TEMPLATE_VERSION = "0ea9956659b50098c275e687533954cfa68f1541eab40ad167cf8627def4014b"
ORIGINAL_SHA256 = "a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751"
ASSET_PATH = Path(__file__).with_name("chat") / "assets" / "na5-document-e162.json"
DATE_ORDER = (
    ("birth_date", "entry_date"),
    ("entry_date", "permitted_until"),
    ("permitted_until", "extension_until"),
    ("extension_until", "passport_expiry"),
)


def verify_document_compatibility(document: dict, legacy: dict) -> None:
    """Reject any field change except the one evidenced uppercase annotation.

    This pure check supports regression tests. Production additionally checks the
    exact public schema bytes before calling it; it never trusts browser schemas.
    """
    expected = {
        "document_id": DOCUMENT_ID,
        "procedure_code": PROCEDURE_CODE,
        "form_id": "NA5",
        "revision": legacy.get("revision_reference"),
        "effective_from": legacy.get("effective_from"),
        "review_status": "draft",
        "applicability": "unresolved",
        "download_available": False,
        "template_version": DOCUMENT_TEMPLATE_VERSION,
        "template_sha256": ORIGINAL_SHA256,
        "page_count": 3,
    }
    if (
        legacy.get("procedure_code") != PROCEDURE_CODE
        or legacy.get("form_sha256") != ORIGINAL_SHA256
        or legacy.get("review_status") != "draft"
        or any(document.get(key) != value for key, value in expected.items())
        or document.get("fixed_values") != legacy.get("fixed_values")
        or document.get("date_order") != [list(pair) for pair in DATE_ORDER]
    ):
        raise RuntimeError("Pinned document compatibility does not match.")
    fields = deepcopy(document.get("fields"))
    old_fields = legacy.get("fields")
    if not isinstance(fields, list) or not isinstance(old_fields, list) or len(fields) != 43 or len(old_fields) != 43:
        raise RuntimeError("Pinned document compatibility does not match.")
    names = [field for field in fields if isinstance(field, dict) and field.get("id") == "applicant_full_name"]
    if len(names) != 1 or names[0].pop("uppercase", None) is not True or fields != old_fields:
        raise RuntimeError("Pinned document compatibility does not match.")


def load_document_schema(path: Path = ASSET_PATH) -> dict:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != DOCUMENT_SCHEMA_SHA256:
        raise RuntimeError("Pinned document schema hash does not match.")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise RuntimeError("Pinned document compatibility does not match.")
    verify_document_compatibility(document, WORKFLOW)
    return document


# Loading this module verifies the additional version before any request can use
# it. The legacy workflow has its own independent byte/identity pin and loader.
_CHECKED_DOCUMENT = load_document_schema()


def supports_prefill_schema(schema_version: str) -> bool:
    return schema_version in (WORKFLOW_SHA256, DOCUMENT_TEMPLATE_VERSION)


def validate_compatible_date_order(schema_version: str, values: dict[str, str | None]) -> None:
    """Add e162's pairwise checks to its incoming draft without altering legacy."""
    if schema_version != DOCUMENT_TEMPLATE_VERSION:
        return
    for earlier, later in DATE_ORDER:
        if values.get(earlier) and values.get(later):
            try:
                valid = date.fromisoformat(values[earlier]) <= date.fromisoformat(values[later])
            except (TypeError, ValueError):
                raise InvalidDraft("Invalid date order.") from None
            if not valid:
                raise InvalidDraft("Invalid date order.")
