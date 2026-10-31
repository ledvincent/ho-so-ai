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

    @classmethod
    def from_env(cls) -> "Settings":
        flag = os.getenv("DEMO_FORMS_ENABLED", "false").strip().lower()
        if flag not in {"true", "false"}:
            raise ValueError("DEMO_FORMS_ENABLED must be true or false.")
        jwt_key = os.getenv("CLERK_JWT_KEY") or None
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
        )
