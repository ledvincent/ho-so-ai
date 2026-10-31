"""FastAPI composition with lazy profile storage and application-lifetime cleanup."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .auth import AuthenticationUnavailable, ClerkSessionVerifier, CurrentUser, SessionVerifier, require_user
from .profile import router as profile_router
from .portal.service import ProfileService
from .settings import Settings


class MeResponse(BaseModel):
    subject: str


def create_app(
    settings: Settings | None = None,
    *,
    session_verifier: SessionVerifier | None = None,
    profile_service: ProfileService | None = None,
    chat_provider: object | None = None,
) -> FastAPI:
    config = settings if settings is not None else Settings.from_env()

    if config.auth_provider not in {"clerk", "local"}:
        raise ValueError("Unsupported identity provider.")

    class UnavailableVerifier:
        def verify(self, token):
            raise AuthenticationUnavailable()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from .portal.postgres import build_profile_service
        from .portal.repository import StorageUnavailable

        service = profile_service
        owned = service is None
        local_services = None
        if config.auth_provider == "local":
            from .local_auth.runtime import build_local_services
            try:
                local_services = await run_in_threadpool(build_local_services, config)
            except AuthenticationUnavailable:
                local_services = None
            if local_services is not None:
                app.state.local_auth_store = local_services.store
                app.state.session_verifier = local_services.verifier
                service = profile_service if profile_service is not None else local_services.profiles
        elif owned:
            try:
                # Engine construction is lazy: no connection, schema or migration.
                service = build_profile_service(config)
            except StorageUnavailable:
                # Keep the process available; protected profile requests return 503.
                # Never log connection strings or underlying driver exceptions.
                service = None
        app.state.profile_service = service
        try:
            yield
        finally:
            app.state.profile_service = None
            if local_services is not None:
                app.state.local_auth_store = None
                app.state.session_verifier = UnavailableVerifier()
                await run_in_threadpool(local_services.close)
            elif owned and service is not None:
                try:
                    # Public lifecycle API supplied by the portal owner.
                    await run_in_threadpool(service.close)
                except Exception:
                    raise RuntimeError("Profile storage cleanup failed.") from None

    app = FastAPI(title="Ho So AI application API", version="0.1.0", lifespan=lifespan)
    # Explicit injection is caller-owned. The production service is only built in
    # lifespan, so importing this module cannot allocate a database engine.
    app.state.profile_service = profile_service
    app.state.local_auth_store = None
    if chat_provider is None and config.openai_api_key:
        from .chat.provider import OpenAIChatProvider
        chat_provider = OpenAIChatProvider(api_key=config.openai_api_key, model=config.assistant_model)
    app.state.chat_provider = chat_provider
    app.state.settings = config
    app.state.session_verifier = (
        UnavailableVerifier() if config.auth_provider == "local" else (session_verifier if session_verifier is not None else ClerkSessionVerifier(config))
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    if config.auth_provider == "local":
        from .checkpoint_http import LocalRequestBoundary
        app.add_middleware(LocalRequestBoundary, public_origin=config.public_origin)

    @app.middleware("http")
    async def prevent_private_response_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/v1/", "/v2/")):
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
            "request_id", "draft_revision", "procedure_code", "intent", "message", "focus_field",
            "details", "basics", "contact", "passport", "residence", "legacy",
            "full_legal_name", "sex_as_on_document", "nationality_at_birth",
            "current_nationality", "occupation", "document_number", "document_type",
            "issue_date", "expiry_date", "issuing_authority", "temporary_address_in_vietnam",
            "permanent_address", "consent", "applicant_confirmed", "form_sha256", "schema_version",
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
    from .profile_v2 import router as profile_v2_router
    app.include_router(profile_v2_router)
    if config.auth_provider == "local":
        from .local_auth.routes import create_router as create_auth_router
        app.include_router(create_auth_router(public_origin=config.public_origin))

    def chat_rate_limit(request: Request, user: CurrentUser):
        if config.auth_provider == "local" and request.method == "POST":
            from .local_auth.store import RateLimited
            try:
                request.app.state.local_auth_store.check_rate_limit("chat:" + user.subject, 12, 60)
            except RateLimited as exc:
                raise HTTPException(429, detail={"code": "RATE_LIMITED"}, headers={"Retry-After": str(exc.retry_after)}) from None
            except Exception:
                raise HTTPException(503, detail={"code": "ASSISTANT_UNAVAILABLE"}) from None

    from .chat.routes import create_router as create_chat_router
    app.include_router(create_chat_router(), dependencies=[Depends(chat_rate_limit)])
    try:
        from .forms.routes import create_router
    except ModuleNotFoundError as exc:
        if exc.name not in {"hoso_api.forms", "hoso_api.forms.routes"}:
            raise
    else:
        app.include_router(create_router(demo_enabled=config.demo_forms_enabled),
                           dependencies=[Depends(require_user)] if config.auth_provider == "local" else [])
    return app


app = create_app()
