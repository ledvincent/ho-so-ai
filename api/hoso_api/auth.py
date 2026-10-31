"""Clerk session verification and the shared authenticated-subject dependency."""

from dataclasses import dataclass
from typing import Annotated, Protocol

from clerk_backend_api.security import AuthenticateRequestOptions, authenticate_request
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

from .settings import Settings


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    subject: str
    session_id: str


class InvalidSession(Exception):
    """The supplied credential did not establish an application identity."""


class AuthenticationUnavailable(Exception):
    """Authentication is unconfigured or cannot currently verify a session."""


class SessionVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class ClerkSessionVerifier:
    """Verify with the configured Clerk public key; do not fetch remote keys.

    The SDK verifies RS256 signatures, expiry and authorized parties. We also
    require an issuer, expiration, subject and session ID after verification.
    The SDK itself currently disables issuer verification.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def verify(self, token: str) -> AuthenticatedUser:
        settings = self.settings
        if not (
            settings.clerk_jwt_key
            and settings.clerk_issuer
            and settings.clerk_authorized_parties
        ):
            raise AuthenticationUnavailable()
        if not token or len(token) > 16_384:
            raise InvalidSession()
        # Pass only the Bearer credential; the backend deliberately ignores
        # browser cookies and accepts no machine/API-key token types.
        request = httpx.Request(
            "GET", "https://verification.invalid", headers={"Authorization": f"Bearer {token}"}
        )
        result = authenticate_request(
            request,
            AuthenticateRequestOptions(
                jwt_key=settings.clerk_jwt_key,
                authorized_parties=list(settings.clerk_authorized_parties),
                audience=settings.clerk_audience,
                clock_skew_in_ms=0,
                accepts_token=["session_token"],
            ),
        )
        claims = result.payload
        if not result.is_signed_in or not isinstance(claims, dict):
            raise InvalidSession()
        subject = claims.get("sub")
        session_id = claims.get("sid")
        if (
            claims.get("iss") != settings.clerk_issuer
            or type(claims.get("exp")) is not int
            or not isinstance(subject, str)
            or not subject.strip()
            or len(subject) > 256
            or not isinstance(session_id, str)
            or not session_id.strip()
            or len(session_id) > 256
        ):
            raise InvalidSession()
        return AuthenticatedUser(subject=subject, session_id=session_id)


bearer = HTTPBearer(auto_error=False)


def require_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Bearer session is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    verifier: SessionVerifier = request.app.state.session_verifier
    try:
        return verifier.verify(credentials.credentials)
    except InvalidSession:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Bearer session is required.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception:
        # Never return provider errors, token contents or configuration values.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable.",
        ) from None


CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]
