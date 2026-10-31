"""Bounded anonymous public-dialogue state, not application authentication."""
from dataclasses import dataclass, field
import secrets
from threading import Lock
import time

from .dialogue import DialogueState, advance


class MissingSession(Exception):
    pass


class CapacityReached(Exception):
    pass


class TurnLimit(Exception):
    pass


@dataclass
class Session:
    expires_at: float
    state: DialogueState = field(default_factory=lambda: DialogueState(awaiting_choice=True))
    turns: int = 0


class PublicSessions:
    def __init__(self, *, clock=time.monotonic, ttl=600, max_sessions=1000, max_turns=60):
        self.clock = clock
        self.ttl = ttl
        self.max_sessions = max_sessions
        self.max_turns = max_turns
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def _prune(self):
        now = self.clock()
        self._sessions = {key: item for key, item in self._sessions.items() if item.expires_at > now}

    def create(self, old_token=None):
        with self._lock:
            self._prune()
            # Restart invalidates the old dialogue cookie, not a user identity.
            if old_token:
                self._sessions.pop(old_token, None)
            if len(self._sessions) >= self.max_sessions:
                raise CapacityReached()
            token = secrets.token_urlsafe(32)
            self._sessions[token] = Session(self.clock() + self.ttl)
            return token

    def turn(self, token, utterance):
        with self._lock:
            self._prune()
            session = self._sessions.get(token)
            if session is None:
                raise MissingSession()
            if session.turns >= self.max_turns:
                raise TurnLimit()
            session.state, response = advance(session.state, utterance)
            session.turns += 1
            return response

    def end(self, token):
        with self._lock:
            self._sessions.pop(token, None)
