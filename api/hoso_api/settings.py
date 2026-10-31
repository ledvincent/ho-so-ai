"""Explicit application configuration; never load or log secret-bearing files."""

from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit


def _origins(value: str) -> tuple[str, ...]:
    origins = tuple(part.strip() for part in value.split(",") if part.strip())
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or "*" in origin
        ):
            raise ValueError("Origins must be explicit HTTP(S) origins without paths.")
    return origins


@dataclass(frozen=True, slots=True)
class Settings:
    clerk_jwt_key: str | None = field(default=None, repr=False)
    clerk_issuer: str | None = None
    clerk_authorized_parties: tuple[str, ...] = ()
    clerk_audience: str | None = None
    cors_allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    demo_forms_enabled: bool = False
    database_url: str | None = field(default=None, repr=False)
    auth_provider: str = "clerk"
    deployment_mode: str = "local"
    public_origin: str | None = None
    local_db_path: str | None = None
    local_api_host: str = "127.0.0.1"
    local_demo_seed: bool = False
    local_session_ttl_seconds: int = 3600
    openai_api_key: str | None = field(default=None, repr=False)
    assistant_model: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls) -> "Settings":
        flag = os.getenv("DEMO_FORMS_ENABLED", "false").strip().lower()
        if flag not in {"true", "false"}:
            raise ValueError("DEMO_FORMS_ENABLED must be true or false.")
        jwt_key = os.getenv("CLERK_JWT_KEY") or None
        provider = os.getenv("HOSO_AUTH_PROVIDER", "clerk")
        if provider not in {"clerk", "local"}:
            raise ValueError("Unsupported identity provider.")
        demo_seed = os.getenv("HOSO_LOCAL_DEMO_SEED", "false").lower()
        if demo_seed not in {"true", "false"}:
            raise ValueError("HOSO_LOCAL_DEMO_SEED must be true or false.")
        mode = os.getenv("HOSO_DEPLOYMENT_MODE", "local")
        if mode not in {"local", "hosted-demo"}:
            raise ValueError("Unsupported deployment mode.")
        if mode == "hosted-demo" and demo_seed == "true":
            raise ValueError("Weak demonstration seeding is unavailable in hosted mode.")
        origin = os.getenv("HOSO_PUBLIC_ORIGIN") or None
        if origin:
            _origins(origin)
        return cls(
            clerk_jwt_key=jwt_key.replace("\\n", "\n") if jwt_key else None,
            clerk_issuer=os.getenv("CLERK_ISSUER") or None,
            clerk_authorized_parties=_origins(os.getenv("CLERK_AUTHORIZED_PARTIES", "")),
            clerk_audience=os.getenv("CLERK_AUDIENCE") or None,
            cors_allowed_origins=_origins(
                os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
            ),
            demo_forms_enabled=flag == "true",
            database_url=os.getenv("DATABASE_URL") or None,
            auth_provider=provider,
            deployment_mode=mode,
            public_origin=origin,
            local_db_path=os.getenv("HOSO_LOCAL_DB_PATH") or None,
            local_api_host=os.getenv("HOSO_LOCAL_API_HOST", "127.0.0.1"),
            local_demo_seed=demo_seed == "true",
            local_session_ttl_seconds=int(os.getenv("HOSO_LOCAL_SESSION_TTL_SECONDS", "3600")),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            assistant_model=os.getenv("ASSISTANT_MODEL", "gpt-4o-mini"),
        )
