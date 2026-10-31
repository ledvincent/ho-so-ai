"""SQLite users, revocable opaque sessions and bounded persistent rate limits."""

from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Callable
from uuid import uuid4

from ..auth import AuthenticatedUser, AuthenticationUnavailable, InvalidSession
from .hashing import check_password, hash_password

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
_USERNAME = re.compile(r"[a-z0-9][a-z0-9_.-]{2,63}\Z", re.ASCII)
_MAX_RATE_BUCKETS = 2048


class InvalidCredentials(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, int(retry_after))
        super().__init__("Too many requests.")


@dataclass(frozen=True, slots=True)
class LocalUser:
    id: str
    username: str

    def public(self) -> dict:
        return {"id": self.id, "username": self.username, "identity_provider": "local"}


@dataclass(frozen=True, slots=True)
class LocalSession:
    user: LocalUser
    session_id: str
    expires_at: int
    session_token: str | None = field(default=None, repr=False)

    def public(self, *, include_token: bool = False) -> dict:
        result = {"user": self.user.public(), "expires_at": self.expires_at}
        if include_token:
            result["session_token"] = self.session_token
        return result


def normalized_username(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidCredentials()
    value = value.casefold()
    if _USERNAME.fullmatch(value) is None:
        raise InvalidCredentials()
    return value


class LocalAuthStore:
    def __init__(
        self, path: str | Path, *, ttl_seconds: int = 3600,
        clock: Callable[[], float] = time.time,
    ):
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.is_symlink():
            raise AuthenticationUnavailable()
        if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 86_400:
            raise AuthenticationUnavailable()
        # Refuse symlink parents instead of silently storing credentials elsewhere.
        if any(parent.is_symlink() for parent in self.path.parents):
            raise AuthenticationUnavailable()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._closed = False
        self._initialize()

    @contextmanager
    def connection(self):
        if self._closed:
            raise AuthenticationUnavailable()
        connection = None
        try:
            connection = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
        except sqlite3.Error:
            raise AuthenticationUnavailable() from None
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def transaction(self):
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _initialize(self) -> None:
        with self.transaction() as connection:
            for statement in (
                """CREATE TABLE IF NOT EXISTS local_auth_metadata (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), namespace TEXT NOT NULL,
                    dummy_salt BLOB NOT NULL, dummy_hash BLOB NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS local_auth_users (
                    subject TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    password_salt BLOB NOT NULL, password_hash BLOB NOT NULL,
                    created_at INTEGER NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS local_auth_sessions (
                    token_hash BLOB PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL REFERENCES local_auth_users(subject),
                    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    revoked_at INTEGER)""",
                """CREATE INDEX IF NOT EXISTS local_auth_session_owner
                    ON local_auth_sessions(subject, created_at)""",
                """CREATE TABLE IF NOT EXISTS local_auth_rates (
                    bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at INTEGER NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS profiles (
                    owner_subject TEXT PRIMARY KEY, profile_id TEXT NOT NULL UNIQUE,
                    revision INTEGER NOT NULL CHECK(revision>0), full_name TEXT,
                    date_of_birth TEXT, nationality TEXT, address TEXT,
                    phone_number TEXT, email TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}')""",
            ):
                connection.execute(statement)
            metadata = connection.execute("SELECT * FROM local_auth_metadata WHERE singleton=1").fetchone()
            if metadata is None:
                if connection.execute("SELECT 1 FROM local_auth_users LIMIT 1").fetchone():
                    raise AuthenticationUnavailable()
                salt, dummy_hash = hash_password(secrets.token_urlsafe(32))
                connection.execute(
                    "INSERT INTO local_auth_metadata VALUES (1,?,?,?)",
                    (uuid4().hex, salt, dummy_hash),
                )
                metadata = connection.execute("SELECT * FROM local_auth_metadata WHERE singleton=1").fetchone()
            if (
                not isinstance(metadata["namespace"], str)
                or re.fullmatch(r"[0-9a-f]{32}", metadata["namespace"]) is None
                or len(metadata["dummy_salt"]) != 16 or len(metadata["dummy_hash"]) != 32
            ):
                raise AuthenticationUnavailable()
            self.namespace = metadata["namespace"]
            self._dummy_salt, self._dummy_hash = metadata["dummy_salt"], metadata["dummy_hash"]
            connection.execute("""CREATE TRIGGER IF NOT EXISTS local_auth_namespace_immutable
                BEFORE UPDATE OF namespace ON local_auth_metadata
                BEGIN SELECT RAISE(ABORT, 'Local identity namespace is immutable'); END""")
            connection.execute("""CREATE TRIGGER IF NOT EXISTS local_auth_namespace_not_deleted
                BEFORE DELETE ON local_auth_metadata
                BEGIN SELECT RAISE(ABORT, 'Local identity namespace is immutable'); END""")

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def create_user(self, username: str, password: str, *, demo_password: bool = False) -> LocalUser:
        username = normalized_username(username)
        if not demo_password and len(password) < 12:
            raise ValueError("Use at least 12 password characters.")
        with self.connection() as connection:
            existing = connection.execute(
                "SELECT subject,username FROM local_auth_users WHERE username=?", (username,)
            ).fetchone()
        if existing:
            return LocalUser(existing["subject"], existing["username"])
        salt, password_hash = hash_password(password)
        subject = f"local:{self.namespace}:{uuid4()}"
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO local_auth_users VALUES (?,?,?,?,?) ON CONFLICT(username) DO NOTHING",
                (subject, username, salt, password_hash, int(self.clock())),
            )
            row = connection.execute(
                "SELECT subject,username FROM local_auth_users WHERE username=?", (username,)
            ).fetchone()
        return LocalUser(row["subject"], row["username"])

    def _reserve(self, buckets: list[tuple[str, int, int]]) -> None:
        now = int(self.clock())
        with self.transaction() as connection:
            connection.execute("DELETE FROM local_auth_rates WHERE reset_at<=?", (now,))
            new_keys = set()
            for bucket, limit, window in buckets:
                key = hashlib.sha256(bucket.encode("utf-8")).hexdigest()
                row = connection.execute("SELECT count,reset_at FROM local_auth_rates WHERE bucket=?", (key,)).fetchone()
                if row and row["count"] >= limit:
                    raise RateLimited(row["reset_at"] - now)
                if row is None:
                    new_keys.add(key)
            count = connection.execute("SELECT count(*) FROM local_auth_rates").fetchone()[0]
            if count + len(new_keys) > _MAX_RATE_BUCKETS:
                raise RateLimited(max(window for _, _, window in buckets))
            for bucket, _, window in buckets:
                key = hashlib.sha256(bucket.encode("utf-8")).hexdigest()
                connection.execute(
                    "INSERT INTO local_auth_rates VALUES (?,1,?) "
                    "ON CONFLICT(bucket) DO UPDATE SET count=count+1", (key, now + window),
                )

    def check_rate_limit(self, bucket: str, limit: int, window_seconds: int) -> None:
        if (
            not isinstance(bucket, str) or not 1 <= len(bucket) <= 512
            or type(limit) is not int or not 1 <= limit <= 1000
            or type(window_seconds) is not int or not 1 <= window_seconds <= 3600
        ):
            raise AuthenticationUnavailable()
        self._reserve([("application:" + bucket, limit, window_seconds)])

    def login(self, username: str, password: str, *, client: str) -> LocalSession:
        username = normalized_username(username)
        if not isinstance(client, str) or not 1 <= len(client) <= 128:
            raise AuthenticationUnavailable()
        self._reserve([("login:user:" + username, 5, 300), ("login:client:" + client, 20, 300)])
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM local_auth_users WHERE username=?", (username,)).fetchone()
        valid = check_password(
            password, row["password_salt"] if row else self._dummy_salt,
            row["password_hash"] if row else self._dummy_hash,
        )
        if not valid or row is None:
            raise InvalidCredentials()
        now = int(self.clock())
        token = secrets.token_urlsafe(32)
        session_id = str(uuid4())
        with self.transaction() as connection:
            connection.execute("DELETE FROM local_auth_sessions WHERE expires_at<=? OR revoked_at IS NOT NULL", (now,))
            # Keep session storage bounded for each account as well as by expiry.
            connection.execute(
                "DELETE FROM local_auth_sessions WHERE subject=? AND session_id NOT IN "
                "(SELECT session_id FROM local_auth_sessions WHERE subject=? ORDER BY created_at DESC LIMIT 19)",
                (row["subject"], row["subject"]),
            )
            connection.execute(
                "INSERT INTO local_auth_sessions VALUES (?,?,?,?,?,NULL)",
                (hashlib.sha256(token.encode("ascii")).digest(), session_id, row["subject"], now, now + self.ttl_seconds),
            )
        return LocalSession(LocalUser(row["subject"], row["username"]), session_id, now + self.ttl_seconds, token)

    def session(self, token: str) -> LocalSession:
        if not isinstance(token, str) or TOKEN_PATTERN.fullmatch(token) is None:
            raise InvalidSession()
        digest = hashlib.sha256(token.encode("ascii")).digest()
        with self.connection() as connection:
            row = connection.execute(
                "SELECT s.*,u.username FROM local_auth_sessions s JOIN local_auth_users u ON u.subject=s.subject "
                "WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>?",
                (digest, int(self.clock())),
            ).fetchone()
        if (
            row is None or not hmac.compare_digest(row["token_hash"], digest)
            or not row["subject"].startswith(f"local:{self.namespace}:")
        ):
            raise InvalidSession()
        return LocalSession(LocalUser(row["subject"], row["username"]), row["session_id"], row["expires_at"])

    def logout(self, token: str) -> None:
        self.session(token)
        with self.transaction() as connection:
            connection.execute(
                "UPDATE local_auth_sessions SET revoked_at=? WHERE token_hash=?",
                (int(self.clock()), hashlib.sha256(token.encode("ascii")).digest()),
            )


class LocalSessionVerifier:
    def __init__(self, store: LocalAuthStore):
        self.store = store

    def verify(self, token: str) -> AuthenticatedUser:
        session = self.store.session(token)
        return AuthenticatedUser(subject=session.user.id, session_id=session.session_id)
