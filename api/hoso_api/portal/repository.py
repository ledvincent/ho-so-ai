"""Owner-scoped profile SQL. No client-selected owner or profile identifier.

The transaction provider must install the verified subject on its connection.
SQL predicates still enforce the owner independently of PostgreSQL RLS.
"""

from contextlib import AbstractContextManager
from typing import Protocol
from uuid import uuid4

from sqlalchemy import Connection, JSON, bindparam, text

from ..auth import AuthenticatedUser
from ..profile import ProfileFields, ProfileResponse, ProfileUpdate
from ..profile_v2_models import (
    ProfileBasics, ProfileContact, ProfileDetails, ProfileDetailsExtension,
    ProfileLegacy, ProfileV2Response, ProfileV2Update,
)


class ProfileMissing(Exception):
    pass


class RevisionConflict(Exception):
    pass


class StorageUnavailable(Exception):
    pass


class Transactions(Protocol):
    def for_user(self, user: AuthenticatedUser) -> AbstractContextManager[Connection]: ...


# The six fields and their validation come from the shared Pydantic model.
_FIELDS = tuple(ProfileFields.model_fields)
_COLUMNS = ", ".join(("profile_id", "revision", *_FIELDS))
_READ = text(f"SELECT {_COLUMNS} FROM hoso_portal.profiles WHERE owner_subject = :subject")
_CREATE = text(
    f"INSERT INTO hoso_portal.profiles (owner_subject, profile_id, revision, {', '.join(_FIELDS)}) "
    f"VALUES (:subject, :profile_id, 1, {', '.join(':' + field for field in _FIELDS)}) "
    f"ON CONFLICT (owner_subject) DO NOTHING RETURNING {_COLUMNS}"
)
_UPDATE = text(
    "UPDATE hoso_portal.profiles SET "
    + ", ".join(f"{field} = :{field}" for field in _FIELDS)
    + ", revision = revision + 1 "
    + "WHERE owner_subject = :subject AND revision = :expected_revision "
    + f"RETURNING {_COLUMNS}"
)

# Separate statements leave app.v1 usable on a database not yet provisioned for v2.
_V2_COLUMNS = _COLUMNS + ", details_json"
_READ_V2 = text(f"SELECT {_V2_COLUMNS} FROM hoso_portal.profiles WHERE owner_subject = :subject")
_CORE_FIELDS = ("full_name", "date_of_birth", "phone_number", "email")
_CREATE_V2 = text(
    f"INSERT INTO hoso_portal.profiles (owner_subject, profile_id, revision, {', '.join(_CORE_FIELDS)}, details_json) "
    f"VALUES (:subject, :profile_id, 1, {', '.join(':' + field for field in _CORE_FIELDS)}, :details_json) "
    f"ON CONFLICT (owner_subject) DO NOTHING RETURNING {_V2_COLUMNS}"
).bindparams(bindparam("details_json", type_=JSON))
_UPDATE_V2 = text(
    "UPDATE hoso_portal.profiles SET "
    + ", ".join(f"{field} = :{field}" for field in _CORE_FIELDS)
    + ", details_json = :details_json, revision = revision + 1 "
    + "WHERE owner_subject = :subject AND revision = :expected_revision "
    + f"RETURNING {_V2_COLUMNS}"
).bindparams(bindparam("details_json", type_=JSON))


def require_verified_user(user: AuthenticatedUser) -> None:
    # Only the shared verifier establishes authenticity. This protects internal
    # call sites from accidentally passing a raw browser value instead.
    if not isinstance(user, AuthenticatedUser) or any(
        not isinstance(value, str) or not value.strip() or len(value) > 256
        for value in (user.subject, user.session_id)
    ):
        raise StorageUnavailable()


def _response(row) -> ProfileResponse:
    return ProfileResponse(
        profile_id=row["profile_id"],
        revision=row["revision"],
        fields=ProfileFields(**{field: row[field] for field in _FIELDS}),
    )


def _response_v2(row) -> ProfileV2Response:
    # Validate legacy/core values with their original rules, without tightening
    # old v1-valid rows or interpreting generic nationality/address as explicit.
    core = _response(row).fields
    raw = row["details_json"]
    extension = (
        ProfileDetailsExtension.model_validate_json(raw)
        if isinstance(raw, str) else ProfileDetailsExtension.model_validate(raw)
    )
    return ProfileV2Response(
        profile_id=row["profile_id"], revision=row["revision"],
        details=ProfileDetails(
            basics=ProfileBasics(
                **extension.basics.model_dump(),
                full_legal_name=core.full_name, date_of_birth=core.date_of_birth,
            ),
            contact=ProfileContact(phone_number=core.phone_number, email=core.email),
            passport=extension.passport, residence=extension.residence,
        ),
        legacy=ProfileLegacy(nationality=core.nationality, address=core.address),
    )


class ProfileRepository:
    def __init__(self, transactions: Transactions):
        self._transactions = transactions

    def read(self, user: AuthenticatedUser) -> ProfileResponse:
        require_verified_user(user)
        with self._transactions.for_user(user) as connection:
            row = connection.execute(_READ, {"subject": user.subject}).mappings().one_or_none()
            if row is None:
                raise ProfileMissing()
            return _response(row)

    def write(self, user: AuthenticatedUser, payload: ProfileUpdate) -> ProfileResponse:
        require_verified_user(user)
        # Validate again at the internal boundary; Pydantic models are mutable.
        payload = ProfileUpdate.model_validate(payload.model_dump())
        parameters = {**payload.fields.model_dump(), "subject": user.subject}
        with self._transactions.for_user(user) as connection:
            if payload.expected_revision == 0:
                row = connection.execute(
                    _CREATE, {**parameters, "profile_id": str(uuid4())}
                ).mappings().one_or_none()
                if row is None:
                    raise RevisionConflict()
            else:
                row = connection.execute(
                    _UPDATE, {**parameters, "expected_revision": payload.expected_revision}
                ).mappings().one_or_none()
                if row is None:
                    exists = connection.execute(
                        text("SELECT 1 FROM hoso_portal.profiles WHERE owner_subject = :subject"),
                        {"subject": user.subject},
                    ).first()
                    if exists is None:
                        raise ProfileMissing()
                    raise RevisionConflict()
            return _response(row)

    def read_v2(self, user: AuthenticatedUser) -> ProfileV2Response:
        require_verified_user(user)
        with self._transactions.for_user(user) as connection:
            row = connection.execute(_READ_V2, {"subject": user.subject}).mappings().one_or_none()
            if row is None:
                raise ProfileMissing()
            return _response_v2(row)

    def write_v2(self, user: AuthenticatedUser, payload: ProfileV2Update) -> ProfileV2Response:
        require_verified_user(user)
        payload = ProfileV2Update.model_validate(payload.model_dump())
        details = payload.details
        extension = ProfileDetailsExtension.model_validate({
            "basics": details.basics.model_dump(exclude={"full_legal_name", "date_of_birth"}),
            "passport": details.passport.model_dump(),
            "residence": details.residence.model_dump(),
        })
        parameters = {
            "subject": user.subject,
            "full_name": details.basics.full_legal_name,
            "date_of_birth": details.basics.date_of_birth,
            "phone_number": details.contact.phone_number,
            "email": details.contact.email,
            "details_json": extension.model_dump(),
        }
        with self._transactions.for_user(user) as connection:
            if payload.expected_revision == 0:
                row = connection.execute(
                    _CREATE_V2, {**parameters, "profile_id": str(uuid4())}
                ).mappings().one_or_none()
                if row is None:
                    raise RevisionConflict()
            else:
                row = connection.execute(
                    _UPDATE_V2, {**parameters, "expected_revision": payload.expected_revision}
                ).mappings().one_or_none()
                if row is None:
                    exists = connection.execute(
                        text("SELECT 1 FROM hoso_portal.profiles WHERE owner_subject = :subject"),
                        {"subject": user.subject},
                    ).first()
                    if exists is None:
                        raise ProfileMissing()
                    raise RevisionConflict()
            return _response_v2(row)
