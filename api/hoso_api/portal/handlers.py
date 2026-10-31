"""Call from the existing profile.py handlers after scaffold-owner integration.

No router is registered here. Until that integration, the real routes stay 501.
"""

from fastapi import HTTPException, Request

from ..auth import AuthenticatedUser
from ..profile import ProfileResponse, ProfileUpdate
from .repository import ProfileMissing, RevisionConflict


def _call(request: Request, operation: str, *args) -> ProfileResponse:
    try:
        service = request.app.state.profile_service
        return getattr(service, operation)(*args)
    except ProfileMissing:
        raise HTTPException(404, detail={"code": "PROFILE_NOT_FOUND"}) from None
    except RevisionConflict:
        raise HTTPException(409, detail={"code": "PROFILE_REVISION_CONFLICT"}) from None
    except Exception:
        raise HTTPException(503, detail={"code": "PROFILE_UNAVAILABLE"}) from None


def read_profile(request: Request, user: AuthenticatedUser) -> ProfileResponse:
    return _call(request, "read", user)


def write_profile(
    request: Request, user: AuthenticatedUser, payload: ProfileUpdate
) -> ProfileResponse:
    return _call(request, "write", user, payload)
