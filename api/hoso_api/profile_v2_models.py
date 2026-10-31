"""Versioned, app-owned reusable details; no official-form mapping or consent."""

from datetime import date
import re
from typing import Literal, Self
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .profile import ProfileFields


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


def _new_text(value: str | None, *, address: bool = False) -> str | None:
    if value is not None and any(
        unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        and not (address and char in {"\n", "\r"})
        for char in value
    ):
        raise ValueError("Control, format and surrogate characters are not allowed.")
    return value


def _calendar_date(value: str | None) -> str | None:
    if value is not None:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("Use a complete ISO calendar date.")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("Use a valid ISO calendar date.") from None
    return value


class ProfileAdditionalBasics(_StrictModel):
    sex_as_on_document: Literal["M", "F", "X", "unspecified"] | None = None
    nationality_at_birth: str | None = Field(default=None, max_length=80)
    current_nationality: str | None = Field(default=None, max_length=80)
    occupation: str | None = Field(default=None, max_length=120)

    @field_validator("nationality_at_birth", "current_nationality", "occupation")
    @classmethod
    def validate_new_text(cls, value: str | None) -> str | None:
        return _new_text(value)


class ProfileBasics(ProfileAdditionalBasics):
    full_legal_name: str | None = Field(default=None, max_length=120)
    date_of_birth: str | None = Field(default=None, max_length=10)

    @field_validator("full_legal_name")
    @classmethod
    def validate_shared_name(cls, value: str | None) -> str | None:
        return ProfileFields(full_name=value).full_name

    @field_validator("date_of_birth")
    @classmethod
    def validate_shared_birth_date(cls, value: str | None) -> str | None:
        return ProfileFields(date_of_birth=value).date_of_birth


class ProfileContact(_StrictModel):
    phone_number: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("phone_number")
    @classmethod
    def validate_shared_phone(cls, value: str | None) -> str | None:
        return ProfileFields(phone_number=value).phone_number

    @field_validator("email")
    @classmethod
    def validate_shared_email(cls, value: str | None) -> str | None:
        return ProfileFields(email=value).email


class ProfilePassport(_StrictModel):
    document_number: str | None = Field(default=None, max_length=64)
    document_type: str | None = Field(default=None, max_length=80)
    issue_date: str | None = Field(default=None, max_length=10)
    expiry_date: str | None = Field(default=None, max_length=10)
    issuing_authority: str | None = Field(default=None, max_length=160)

    @field_validator("document_number", "document_type", "issuing_authority")
    @classmethod
    def validate_new_text(cls, value: str | None) -> str | None:
        return _new_text(value)

    @field_validator("issue_date", "expiry_date")
    @classmethod
    def validate_document_date(cls, value: str | None) -> str | None:
        return _calendar_date(value)

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.issue_date is not None and self.expiry_date is not None and self.expiry_date < self.issue_date:
            raise ValueError("Passport expiry must not precede its issue date.")
        return self


class ProfileResidence(_StrictModel):
    temporary_address_in_vietnam: str | None = Field(default=None, max_length=500)
    permanent_address: str | None = Field(default=None, max_length=500)

    @field_validator("*")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        return _new_text(value, address=True)


class ProfileDetails(_StrictModel):
    basics: ProfileBasics
    contact: ProfileContact
    passport: ProfilePassport
    residence: ProfileResidence


class ProfileDetailsExtension(_StrictModel):
    """Storage-only new fields; shared core aliases cannot enter this JSON."""

    basics: ProfileAdditionalBasics = Field(default_factory=ProfileAdditionalBasics)
    passport: ProfilePassport = Field(default_factory=ProfilePassport)
    residence: ProfileResidence = Field(default_factory=ProfileResidence)


class ProfileLegacy(_StrictModel):
    nationality: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("nationality")
    @classmethod
    def validate_shared_nationality(cls, value: str | None) -> str | None:
        return ProfileFields(nationality=value).nationality

    @field_validator("address")
    @classmethod
    def validate_shared_address(cls, value: str | None) -> str | None:
        return ProfileFields(address=value).address


class ProfileV2Update(_StrictModel):
    expected_revision: int = Field(ge=0)
    details: ProfileDetails


class ProfileV2Response(_StrictModel):
    schema_version: Literal["profile.v2"] = "profile.v2"
    profile_id: str = Field(min_length=1, max_length=256)
    revision: int = Field(ge=1)
    details: ProfileDetails
    legacy: ProfileLegacy
