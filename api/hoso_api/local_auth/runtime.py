"""Explicit loopback-only local runtime; reuses the app.v1 profile repository."""

from contextlib import contextmanager
from dataclasses import dataclass
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlsplit

from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool

from ..auth import AuthenticationUnavailable
from ..portal.repository import ProfileRepository, StorageUnavailable, require_verified_user
from ..portal.service import ProfileService
from .store import LocalAuthStore, LocalSessionVerifier


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def valid_local_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return bool(
            parsed.scheme in {"http", "https"} and parsed.hostname
            and is_loopback(parsed.hostname) and parsed.port
            and not parsed.username and not parsed.password
            and not parsed.path and not parsed.query and not parsed.fragment
        )
    except (ValueError, TypeError):
        return False


def valid_auth_origin(origin: str | None, deployment_mode: str = "local") -> bool:
    """One explicit origin; hosted mode never changes the API peer boundary."""
    if deployment_mode == "local":
        return valid_local_origin(origin)
    if deployment_mode != "hosted-demo" or not isinstance(origin, str):
        return False
    try:
        parsed = urlsplit(origin)
        host, port = parsed.hostname, parsed.port
        if (
            parsed.scheme != "https" or not host or not 1 <= len(host) <= 253
            or parsed.username is not None or parsed.password is not None
            or parsed.path or parsed.query or parsed.fragment
            or host == "localhost" or host.endswith(".localhost")
            or len(host.split(".")) < 2
            or any(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label, re.ASCII) is None
                   for label in host.split("."))
        ):
            return False
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return False
        canonical = "https://" + host + (f":{port}" if port is not None and port != 443 else "")
        return canonical == origin
    except (ValueError, TypeError):
        return False


class SQLiteTransactions:
    def __init__(self, store: LocalAuthStore):
        self.store = store
        self.engine = create_engine(
            "sqlite://", poolclass=NullPool,
            connect_args={"check_same_thread": False, "timeout": 5},
            echo=False, hide_parameters=True,
        )

        @event.listens_for(self.engine, "connect")
        def attach(connection, _):
            connection.execute("ATTACH DATABASE ? AS hoso_portal", (str(store.path),))
            connection.execute("PRAGMA busy_timeout = 5000")

    @contextmanager
    def for_user(self, user):
        require_verified_user(user)
        if self.store.closed or not user.subject.startswith(f"local:{self.store.namespace}:"):
            raise StorageUnavailable()
        with self.engine.begin() as connection:
            active = connection.execute(text(
                "SELECT 1 FROM hoso_portal.local_auth_sessions WHERE session_id=:session "
                "AND subject=:subject AND revoked_at IS NULL AND expires_at>:now"
            ), {"session": user.session_id, "subject": user.subject, "now": int(self.store.clock())}).first()
            if active is None:
                raise StorageUnavailable()
            yield connection

    def close(self):
        self.engine.dispose()


@dataclass(slots=True)
class LocalServices:
    store: LocalAuthStore
    verifier: LocalSessionVerifier
    profiles: ProfileService

    def close(self):
        try:
            self.profiles.close()
        finally:
            self.store.close()


def build_local_services(settings) -> LocalServices | None:
    if settings.auth_provider != "local":
        return None
    deployment_mode = getattr(settings, "deployment_mode", "local")
    if (
        not settings.local_db_path or not Path(settings.local_db_path).is_absolute()
        or not is_loopback(settings.local_api_host)
        or not valid_auth_origin(settings.public_origin, deployment_mode)
        or (deployment_mode == "hosted-demo" and settings.local_demo_seed)
    ):
        raise AuthenticationUnavailable()
    try:
        store = LocalAuthStore(settings.local_db_path, ttl_seconds=settings.local_session_ttl_seconds)
    except Exception:
        raise AuthenticationUnavailable() from None
    try:
        if deployment_mode == "hosted-demo":
            # Refuse legacy demo accounts even when the seed flag is now off.
            # This applies to direct ASGI startup as well as the jury launcher.
            with store.connection() as connection:
                reserved = connection.execute(
                    "SELECT 1 FROM local_auth_users WHERE username IN ('admin', 'reviewer') LIMIT 1"
                ).fetchone()
            if reserved is not None:
                raise AuthenticationUnavailable()
        if settings.local_demo_seed:
            store.create_user("admin", "admin", demo_password=True)
            store.create_user("reviewer", "reviewer-demo", demo_password=True)
        transactions = SQLiteTransactions(store)
        profiles = ProfileService(ProfileRepository(transactions), cleanup=transactions.close)
        return LocalServices(store, LocalSessionVerifier(store), profiles)
    except Exception:
        store.close()
        raise AuthenticationUnavailable() from None
