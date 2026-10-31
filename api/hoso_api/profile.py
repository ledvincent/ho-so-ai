"""App-owned profile shapes. Storage and owner checks belong to AUTH-01.

These fields are application data, not an approved mapping to an official form.
"""

from datetime import date
import re

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .auth import CurrentUser


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    full_name: str | None = Field(default=None, max_length=120)
    date_of_birth: str | None = Field(default=None, max_length=10)
    nationality: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=300)
    phone_number: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("*")
    @classmethod
    def reject_control_characters(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        allowed = {"\n", "\t"} if info.field_name == "address" else set()
        if any((ord(char) < 32 or ord(char) == 127) and char not in allowed for char in value):
            raise ValueError("Control characters are not allowed.")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date(cls, value: str | None) -> str | None:
        if value:
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
                raise ValueError("Use an ISO calendar date.")
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValueError("Use a valid ISO calendar date.") from None
        return value or None


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    expected_revision: int = Field(ge=0)
    fields: ProfileFields


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    profile_id: str = Field(min_length=1, max_length=256)
    revision: int = Field(ge=1)
    fields: ProfileFields


router = APIRouter(prefix="/v1", tags=["profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(request: Request, user: CurrentUser) -> ProfileResponse:
    # Local imports avoid a cycle: the portal consumes these shared models.
    from .portal.handlers import read_profile

    return read_profile(request, user)


@router.put("/profile", response_model=ProfileResponse)
def put_profile(request: Request, payload: ProfileUpdate, user: CurrentUser) -> ProfileResponse:
    from .portal.handlers import write_profile

    return write_profile(request, user, payload)
