"""Owner-scoped profile SQL. No client-selected owner or profile identifier.

The transaction provider must install the verified subject on its connection.
SQL predicates still enforce the owner independently of PostgreSQL RLS.
"""

from contextlib import AbstractContextManager
from typing import Protocol
from uuid import uuid4

from sqlalchemy import Connection, text

from ..auth import AuthenticatedUser
from ..profile import ProfileFields, ProfileResponse, ProfileUpdate


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
