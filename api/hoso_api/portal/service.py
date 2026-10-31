"""Sanitized service boundary for the scaffold's existing profile routes."""

from ..auth import AuthenticatedUser
from ..profile import ProfileResponse, ProfileUpdate
from .repository import ProfileMissing, ProfileRepository, RevisionConflict, StorageUnavailable


class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self._repository = repository

    def read(self, user: AuthenticatedUser) -> ProfileResponse:
        try:
            return self._repository.read(user)
        except ProfileMissing:
            raise
        except Exception:
            # Never expose or log SQL errors, credentials or profile values.
            raise StorageUnavailable() from None

    def write(self, user: AuthenticatedUser, payload: ProfileUpdate) -> ProfileResponse:
        try:
            return self._repository.write(user, payload)
        except (ProfileMissing, RevisionConflict):
            raise
        except Exception:
            raise StorageUnavailable() from None
