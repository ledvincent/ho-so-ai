"""Read-only app.v1 consumer. Import Kim's delivered models; never copy them.

Requires hoso_api at the producer commit documented in README.md. This module
does not configure Clerk, create credentials, or establish current revocation.
The trusted host supplies the existing verifier and an API-origin HTTP client.
"""

from collections.abc import Mapping
import math

import httpx
from hoso_api.auth import (
    AuthenticatedUser, AuthenticationUnavailable, InvalidSession, SessionVerifier,
)
from hoso_api.profile import ProfileFields, ProfileResponse

from .authorization import AccessDenied, ToolContext, ToolFailure

PROFILE_READ_TOOL = "profile.read"


class ProfileReader:
    """One fixed GET route, with a credential passed only for the current call.

    Inject a dedicated httpx-compatible client configured for Kim's API origin.
    Never expose this class as a model tool directly: call only inside authorized
    dispatch with a server-derived context and the matching request credential.
    Do not log HTTP headers/bodies. No full ProfileResponse escapes this adapter.
    """

    def __init__(self, *, client: httpx.Client, verifier: SessionVerifier, timeout: float = 5):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("A finite positive timeout is required")
        self._client = client
        self._verifier = verifier
        self._timeout = timeout

    def read(self, credential: str, context: ToolContext) -> dict[str, str | None]:
        # This is an internal trusted context, never a client JSON principal.
        if (
            not isinstance(context, ToolContext)
            or not isinstance(credential, str) or not credential or len(credential) > 16_384
            or not isinstance(context.fields, frozenset) or not context.fields
            or not context.fields <= ProfileFields.model_fields.keys()
        ):
            raise AccessDenied()
        try:
            user = self._verifier.verify(credential)
        except InvalidSession:
            raise AccessDenied() from None
        except AuthenticationUnavailable:
            raise ToolFailure("AUTH_UNAVAILABLE") from None
        except Exception:
            raise ToolFailure("AUTH_UNAVAILABLE") from None
        if (
            not isinstance(user, AuthenticatedUser)
            or user.subject != context.owner or user.session_id != context.auth_session
        ):
            raise AccessDenied()
        try:
            response = self._client.get(
                "/v1/profile", headers={"Authorization": f"Bearer {credential}"},
                timeout=self._timeout, follow_redirects=False,
            )
        except Exception:
            raise ToolFailure("PROFILE_UNAVAILABLE") from None
        if response.status_code in (401, 403):
            raise AccessDenied()
        if response.status_code == 503:
            raise ToolFailure("PROFILE_UNAVAILABLE")
        # Never return upstream detail, including HTML, validation input or tokens.
        try:
            directives = {part.strip().lower() for part in response.headers.get("cache-control", "").split(",")}
            if "no-store" not in directives:
                raise ValueError()
            if response.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
                raise ValueError()
            if len(response.content) > 16_384:
                raise ValueError()
            payload = response.json()
            if response.status_code == 404 and payload == {"detail": {"code": "PROFILE_NOT_FOUND"}}:
                raise ToolFailure("PROFILE_NOT_FOUND")
            if response.status_code != 200 or not isinstance(payload, Mapping):
                raise ValueError()
            fields = payload.get("fields")
            if not isinstance(fields, Mapping) or set(fields) != set(ProfileFields.model_fields):
                raise ValueError()
            profile = ProfileResponse.model_validate(payload)
        except ToolFailure:
            raise
        except Exception:
            raise ToolFailure("PROFILE_RESPONSE_INVALID") from None
        # Do not expose profile_id, revision, or unapproved values to the model.
        return {name: getattr(profile.fields, name) for name in context.fields}
