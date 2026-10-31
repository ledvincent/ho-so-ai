"""Bounded anonymous public-dialogue state, not application authentication."""
from dataclasses import dataclass, field
import secrets
from threading import Lock
import time

from .dialogue import DialogueState, advance
from .languages import Language, MESSAGES


class MissingSession(Exception):
    pass


class CapacityReached(Exception):
    pass


class TurnLimit(Exception):
    pass


class AudioLimit(Exception):
    pass


@dataclass
class Session:
    expires_at: float
    language: Language = "vi"
    state: DialogueState = field(default_factory=lambda: DialogueState(awaiting_choice=True))
    turns: int = 0
    last_reply: str = ""
    audio_operations: int = 0
    audio_busy: bool = False


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

    def create(self, old_token=None, language: Language = "vi"):
        with self._lock:
            self._prune()
            # Restart invalidates the old dialogue cookie, not a user identity.
            if old_token:
                self._sessions.pop(old_token, None)
            if len(self._sessions) >= self.max_sessions:
                raise CapacityReached()
            token = secrets.token_urlsafe(32)
            self._sessions[token] = Session(self.clock() + self.ttl, language=language, last_reply=MESSAGES[language]["welcome"])
            return token

    def turn(self, token, utterance, language: Language | None = None):
        with self._lock:
            self._prune()
            session = self._sessions.get(token)
            if session is None:
                raise MissingSession()
            if session.turns >= self.max_turns:
                raise TurnLimit()
            session.language = language or session.language
            session.state, response = advance(session.state, utterance, session.language)
            session.last_reply = response["reply"]
            session.turns += 1
            return response

    def audio_begin(self, token):
        with self._lock:
            self._prune()
            session = self._sessions.get(token)
            if session is None:
                raise MissingSession()
            if session.audio_busy or session.audio_operations >= 20:
                raise AudioLimit()
            session.audio_busy = True
            session.audio_operations += 1
            return session.language, session.last_reply

    def audio_end(self, token):
        with self._lock:
            self._prune()
            session = self._sessions.get(token)
            if session is None:
                raise MissingSession()
            session.audio_busy = False

    def end(self, token):
        with self._lock:
            self._sessions.pop(token, None)
