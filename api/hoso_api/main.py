"""FastAPI application factory. No database or identity calls during startup."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .auth import ClerkSessionVerifier, CurrentUser, SessionVerifier
from .profile import router as profile_router
from .settings import Settings


class MeResponse(BaseModel):
    subject: str


def create_app(
    settings: Settings | None = None,
    *,
    session_verifier: SessionVerifier | None = None,
) -> FastAPI:
    config = settings if settings is not None else Settings.from_env()
    app = FastAPI(title="Ho So AI application API", version="0.1.0")
    app.state.settings = config
    app.state.session_verifier = (
        session_verifier if session_verifier is not None else ClerkSessionVerifier(config)
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def prevent_private_response_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default error payload includes the submitted input. Profiles
        # and later form values may contain PII, so return only stable error types.
        known_locations = {
            "body", "query", "path", "header", "fields", "expected_revision",
            "full_name", "date_of_birth", "nationality", "address", "phone_number",
            "email", "values", "revision", "template_version", "acknowledged", "template_id",
        }
        issues = [
            {
                "loc": [
                    part if isinstance(part, int) or part in known_locations else "unknown_field"
                    for part in error["loc"]
                ],
                "type": error["type"],
                "msg": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "detail": "Invalid request data.",
                "errors": issues,
            },
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/me", response_model=MeResponse, tags=["identity"])
    def me(user: CurrentUser) -> MeResponse:
        return MeResponse(subject=user.subject)

    app.include_router(profile_router)
    try:
        from .forms.routes import create_router
    except ModuleNotFoundError as exc:
        if exc.name not in {"hoso_api.forms", "hoso_api.forms.routes"}:
            raise
    else:
        app.include_router(create_router(demo_enabled=config.demo_forms_enabled))
    return app


app = create_app()
