"""Versioned own-profile routes and read-only, explicitly consented prefill."""

from fastapi import APIRouter, HTTPException, Request

from .auth import CurrentUser
from .portal.handlers import _call
from .portal.repository import RevisionConflict
from .profile_v2_models import ProfileV2Response, ProfileV2Update
from .profile_prefill import PrefillRequest, PrefillResponse, PrefillUnsupported, build_prefill

router = APIRouter(prefix="/v2/profile", tags=["profile-v2"])


@router.get("", response_model=ProfileV2Response)
def get_profile(request: Request, user: CurrentUser) -> ProfileV2Response:
    return _call(request, "read_v2", user)


@router.put("", response_model=ProfileV2Response)
def put_profile(request: Request, payload: ProfileV2Update, user: CurrentUser) -> ProfileV2Response:
    return _call(request, "write_v2", user, payload)


@router.post("/prefill", response_model=PrefillResponse)
def prefill(request: Request, payload: PrefillRequest, user: CurrentUser) -> PrefillResponse:
    # Pydantic enforces BOTH affirmative consent flags before this profile read.
    profile = _call(request, "read_v2", user)
    try:
        return build_prefill(profile, payload)
    except RevisionConflict:
        raise HTTPException(409, detail={"code": "PROFILE_REVISION_CONFLICT"}) from None
    except PrefillUnsupported:
        raise HTTPException(409, detail={"code": "PREFILL_UNSUPPORTED"}) from None
    except ValueError:
        raise HTTPException(422, detail={"code": "PREFILL_INVALID_DRAFT"}) from None
