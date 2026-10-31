"""Process-local authorization. All identity verification is supplied by the host.

Only trusted server code may construct this service, register tools, or provide a
verifier. Conversation/request IDs and spoken consent are never credentials.
"""

from dataclasses import dataclass, field
import math
import secrets
from threading import Lock
import time
from types import MappingProxyType
from typing import Callable, Mapping, Protocol


class AccessDenied(Exception):
    def __init__(self):
        super().__init__("Access denied")


class CapacityReached(Exception):
    def __init__(self):
        super().__init__("Authorization capacity reached")


class ToolFailure(Exception):
    """Allowlisted, value-free adapter outcomes that may cross dispatch."""

    def __init__(self, code: str):
        if code not in {"PROFILE_NOT_FOUND", "PROFILE_UNAVAILABLE", "PROFILE_RESPONSE_INVALID", "AUTH_UNAVAILABLE"}:
            raise ValueError("Unknown tool failure code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class VerifiedIdentity:
    """Verifier output, never deserialize from client JSON.

    expires_at uses the service's monotonic clock, not a JWT epoch timestamp.
    The verifier must revalidate session revocation on every invocation.
    """

    subject: str
    auth_session: str
    expires_at: float


class IdentityVerifier(Protocol):
    def __call__(self, credential: object) -> VerifiedIdentity: ...


def _deny_identity(credential: object) -> VerifiedIdentity:
    raise AccessDenied()


@dataclass(frozen=True)
class Scope:
    tool: str
    fields: frozenset[str]

    def __post_init__(self):
        if not isinstance(self.tool, str) or not self.tool:
            raise ValueError("A tool name is required")
        if not isinstance(self.fields, frozenset) or not self.fields:
            raise ValueError("Fields must be a nonempty frozenset")
        if any(not isinstance(item, str) or not item for item in self.fields):
            raise ValueError("Invalid field")


@dataclass(frozen=True, repr=False)
class ToolContext:
    """Trusted dispatch context; the backend must still check record ownership."""

    owner: str
    conversation_id: str
    procedure: str
    fields: frozenset[str]
    auth_session: str


@dataclass(frozen=True)
class Tool:
    """Server-owned policy and synchronous callback; never supplied by the model.

    Callback must return only requested fields, never accept a client owner/ID,
    never reenter Authorization, and complete quickly (dispatch holds the lock).
    """

    allowed: Mapping[str, frozenset[str]]
    run: Callable[[ToolContext], Mapping[str, object]] = field(repr=False)

    def __post_init__(self):
        policies = dict(self.allowed)
        for procedure, fields in policies.items():
            if not isinstance(procedure, str) or not procedure:
                raise ValueError("Invalid procedure policy")
            Scope("validation", fields)
        if not callable(self.run):
            raise ValueError("Tool callback required")
        object.__setattr__(self, "allowed", MappingProxyType(policies))


@dataclass(frozen=True, repr=False)
class RequestView:
    request_id: str
    conversation_id: str
    procedure: str
    scope: Scope
    state: str
    expires_at: float


@dataclass(repr=False)
class _Conversation:
    owner: str
    auth_session: str
    procedure: str
    expires_at: float
    requests: dict[str, RequestView] = field(default_factory=dict)


class Authorization:
    def __init__(
        self, *, tools: Mapping[str, Tool], verifier: IdentityVerifier = _deny_identity,
        clock=time.monotonic, conversation_ttl=600, request_ttl=120, grant_ttl=600,
        max_conversations=1000, max_per_auth_session=4, max_requests=20,
    ):
        for value in (conversation_ttl, request_ttl, grant_ttl):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("TTLs must be finite and positive")
        for value in (max_conversations, max_per_auth_session, max_requests):
            if type(value) is not int or value <= 0:
                raise ValueError("Capacity must be a positive integer")
        self._tools = MappingProxyType(dict(tools))
        self._verifier = verifier
        self._clock = clock
        self._conversation_ttl = conversation_ttl
        self._request_ttl = request_ttl
        self._grant_ttl = grant_ttl
        self._max_conversations = max_conversations
        self._max_per_auth_session = max_per_auth_session
        self._max_requests = max_requests
        self._conversations: dict[str, _Conversation] = {}
        self._lock = Lock()

    def _identity(self, credential):
        try:
            identity = self._verifier(credential)
            if (
                not isinstance(identity, VerifiedIdentity)
                or not isinstance(identity.subject, str) or not identity.subject
                or not isinstance(identity.auth_session, str) or not identity.auth_session
                or not math.isfinite(identity.expires_at)
                or identity.expires_at <= self._clock()
            ):
                raise AccessDenied()
            return identity
        except Exception:
            # Verifier failures fail closed without exposing credentials or errors.
            raise AccessDenied() from None

    def _prune(self):
        now = self._clock()
        self._conversations = {
            key: value for key, value in self._conversations.items()
            if value.expires_at > now
        }

    def _conversation(self, identity, conversation_id):
        self._prune()
        conversation = self._conversations.get(conversation_id)
        if (
            conversation is None or conversation.owner != identity.subject
            or conversation.auth_session != identity.auth_session
        ):
            raise AccessDenied()
        return conversation

    def _request(self, conversation, request_id):
        request = conversation.requests.get(request_id)
        if request is None:
            raise AccessDenied()
        if request.state in ("pending", "approved") and request.expires_at <= self._clock():
            request = self._transition(conversation, request, "expired", request.expires_at)
        return request

    @staticmethod
    def _transition(conversation, request, state, expires_at):
        updated = RequestView(
            request.request_id, request.conversation_id, request.procedure,
            request.scope, state, expires_at,
        )
        conversation.requests[request.request_id] = updated
        return updated

    def start(self, credential: object, *, procedure: str) -> str:
        with self._lock:
            identity = self._identity(credential)
            self._prune()
            if not any(procedure in tool.allowed for tool in self._tools.values()):
                raise AccessDenied()
            count = sum(
                c.owner == identity.subject and c.auth_session == identity.auth_session
                for c in self._conversations.values()
            )
            if len(self._conversations) >= self._max_conversations or count >= self._max_per_auth_session:
                raise CapacityReached()
            conversation_id = secrets.token_urlsafe(32)
            self._conversations[conversation_id] = _Conversation(
                identity.subject, identity.auth_session, procedure,
                min(self._clock() + self._conversation_ttl, identity.expires_at),
            )
            return conversation_id

    def request(self, credential: object, conversation_id: str, *, scope: Scope) -> RequestView:
        with self._lock:
            identity = self._identity(credential)
            conversation = self._conversation(identity, conversation_id)
            tool = self._tools.get(scope.tool)
            if tool is None or not scope.fields <= tool.allowed.get(conversation.procedure, frozenset()):
                raise AccessDenied()
            if len(conversation.requests) >= self._max_requests:
                raise CapacityReached()
            # One current request/grant. Replacement cannot leave older rights active.
            for request in tuple(conversation.requests.values()):
                if request.state in ("pending", "approved"):
                    self._transition(conversation, request, "revoked", request.expires_at)
            request = RequestView(
                secrets.token_urlsafe(32), conversation_id, conversation.procedure,
                scope, "pending",
                min(self._clock() + self._request_ttl, conversation.expires_at, identity.expires_at),
            )
            conversation.requests[request.request_id] = request
            return request

    def inspect(self, credential: object, conversation_id: str, request_id: str) -> RequestView:
        with self._lock:
            identity = self._identity(credential)
            conversation = self._conversation(identity, conversation_id)
            return self._request(conversation, request_id)

    def decide(self, credential: object, conversation_id: str, request_id: str, *, approve: bool) -> RequestView:
        if type(approve) is not bool:
            raise AccessDenied()
        with self._lock:
            identity = self._identity(credential)
            conversation = self._conversation(identity, conversation_id)
            request = self._request(conversation, request_id)
            if request.state != "pending":
                raise AccessDenied()
            expires_at = min(self._clock() + self._grant_ttl, conversation.expires_at, identity.expires_at)
            return self._transition(conversation, request, "approved" if approve else "denied", expires_at)

    def revoke(self, credential: object, conversation_id: str, request_id: str) -> None:
        with self._lock:
            identity = self._identity(credential)
            conversation = self._conversation(identity, conversation_id)
            request = self._request(conversation, request_id)
            if request.state in ("pending", "approved"):
                self._transition(conversation, request, "revoked", request.expires_at)

    def end(self, credential: object, conversation_id: str) -> None:
        with self._lock:
            identity = self._identity(credential)
            self._conversation(identity, conversation_id)
            del self._conversations[conversation_id]

    def dispatch(self, credential: object, conversation_id: str, request_id: str, *, scope: Scope) -> dict[str, object]:
        """Check every call and execute the registered tool in the same critical section.

        Revocation/end cannot overtake an admitted tool call. They prohibit calls
        admitted afterwards, but cannot undo a read already in progress.
        """
        with self._lock:
            identity = self._identity(credential)
            conversation = self._conversation(identity, conversation_id)
            request = self._request(conversation, request_id)
            if (
                request.state != "approved" or scope.tool != request.scope.tool
                or not scope.fields <= request.scope.fields
            ):
                raise AccessDenied()
            tool = self._tools.get(scope.tool)
            if tool is None or not scope.fields <= tool.allowed.get(conversation.procedure, frozenset()):
                raise AccessDenied()
            try:
                result = tool.run(ToolContext(
                    identity.subject, conversation_id, conversation.procedure,
                    scope.fields, identity.auth_session,
                ))
            except ToolFailure:
                raise
            except Exception:
                # Adapter exceptions must not echo dossier values or credentials.
                raise AccessDenied() from None
            # Prevent an overbroad adapter response from reaching the caller/model.
            if not isinstance(result, Mapping) or set(result) != scope.fields:
                raise AccessDenied()
            return dict(result)
