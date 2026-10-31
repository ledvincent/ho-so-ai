"""HTTP contracts for the synthetic forms preview and download."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from hoso_api.profile import ProfileFields


class FormRenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    values: ProfileFields
    revision: Annotated[int, Field(ge=1, strict=True)]
    acknowledged: bool = False
    template_version: Annotated[str, Field(min_length=1, max_length=100)]


class FieldMetadata(BaseModel):
    id: str
    label: str
    type: str = "text"
    required: bool = False
    max_length: int
    page: int
    x: float
    width: float
    rule_y: list[float]
    padding: float
    font_size: float
    rule_clearance: float


class FormMetadata(BaseModel):
    id: str
    template_version: str
    title: str
    synthetic: bool
    source: str
    review_status: str
    notice: str
    coordinate_unit: str = "PDF point (1/72 inch)"
    coordinate_origin: str = "top-left of unrotated page; x right, y down"
    page_numbering: str = "zero-based"
    pages: list[dict[str, float | int]]
    fields: list[FieldMetadata]
