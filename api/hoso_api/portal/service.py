"""Sanitized service boundary for the scaffold's existing profile routes."""

from collections.abc import Callable
from threading import Lock

from ..auth import AuthenticatedUser
from ..profile import ProfileResponse, ProfileUpdate
from ..profile_v2_models import ProfileV2Response, ProfileV2Update
from .repository import ProfileMissing, ProfileRepository, RevisionConflict, StorageUnavailable


class ProfileService:
    def __init__(self, repository: ProfileRepository, *, cleanup: Callable[[], None] | None = None):
        self._repository = repository
        self._cleanup = cleanup
        self._closed = False
        self._close_lock = Lock()

    def close(self) -> None:
        """Dispose owned resources after requests drain; safe to call again.

        A failed cleanup may be retried, but the service stays closed to requests.
        This does not cancel or wait for an operation already in progress.
        """
        with self._close_lock:
            self._closed = True
            if self._cleanup is not None:
                try:
                    self._cleanup()
                except Exception:
                    raise StorageUnavailable() from None
                self._cleanup = None

    def read(self, user: AuthenticatedUser) -> ProfileResponse:
        try:
            if self._closed:
                raise StorageUnavailable()
            return self._repository.read(user)
        except ProfileMissing:
            raise
        except Exception:
            # Never expose or log SQL errors, credentials or profile values.
            raise StorageUnavailable() from None

    def write(self, user: AuthenticatedUser, payload: ProfileUpdate) -> ProfileResponse:
        try:
            if self._closed:
                raise StorageUnavailable()
            return self._repository.write(user, payload)
        except (ProfileMissing, RevisionConflict):
            raise
        except Exception:
            raise StorageUnavailable() from None

    def read_v2(self, user: AuthenticatedUser) -> ProfileV2Response:
        try:
            if self._closed:
                raise StorageUnavailable()
            return self._repository.read_v2(user)
        except ProfileMissing:
            raise
        except Exception:
            raise StorageUnavailable() from None

    def write_v2(self, user: AuthenticatedUser, payload: ProfileV2Update) -> ProfileV2Response:
        try:
            if self._closed:
                raise StorageUnavailable()
            return self._repository.write_v2(user, payload)
        except (ProfileMissing, RevisionConflict):
            raise
        except Exception:
            raise StorageUnavailable() from None
