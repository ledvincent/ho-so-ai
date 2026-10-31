"""Server-to-server local auth routes. Next owns browser cookies and token stripping."""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from ..auth import AuthenticationUnavailable, InvalidSession
from .runtime import is_loopback, valid_local_origin
from .store import InvalidCredentials, LocalAuthStore, RateLimited


def failure(status: int, code: str, **headers) -> HTTPException:
    return HTTPException(status, detail={"code": code}, headers={"Cache-Control": "no-store", **headers})


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024, repr=False)

    @field_validator("password")
    @classmethod
    def bounded_password(cls, value):
        if len(value.encode("utf-8")) > 1024:
            raise ValueError("Invalid password length.")
        return value


def local_store(request: Request) -> LocalAuthStore:
    if request.client is None or not is_loopback(request.client.host):
        raise failure(403, "ORIGIN_FORBIDDEN")
    store = getattr(request.app.state, "local_auth_store", None)
    if not isinstance(store, LocalAuthStore):
        raise failure(503, "AUTH_UNAVAILABLE")
    return store


async def json_body(request: Request, origin: str) -> dict:
    if (
        len(request.headers.getlist("origin")) != 1
        or request.headers.get("origin") != origin
        or request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json"
    ):
        raise failure(403, "ORIGIN_FORBIDDEN")
    data = bytearray()
    try:
        async for chunk in request.stream():
            if len(data) + len(chunk) > 4096:
                raise failure(413, "REQUEST_TOO_LARGE")
            data.extend(chunk)
        value = json.loads(data.decode("utf-8"))
    except HTTPException:
        raise
    except Exception:
        raise failure(422, "VALIDATION_ERROR") from None
    if not isinstance(value, dict):
        raise failure(422, "VALIDATION_ERROR")
    return value


def bearer_token(request: Request) -> str:
    headers = request.headers.getlist("authorization")
    if len(headers) != 1:
        raise failure(401, "UNAUTHENTICATED", **{"WWW-Authenticate": "Bearer"})
    scheme, _, token = headers[0].partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise failure(401, "UNAUTHENTICATED", **{"WWW-Authenticate": "Bearer"})
    return token


def create_router(*, public_origin: str | None) -> APIRouter:
    configured = valid_local_origin(public_origin)
    router = APIRouter(prefix="/v1/auth", tags=["local checkpoint auth"])

    def configured_store(request: Request) -> LocalAuthStore:
        if not configured:
            raise failure(503, "AUTH_UNAVAILABLE")
        return local_store(request)

    @router.post("/login")
    async def login(request: Request):
        store = configured_store(request)
        body = await json_body(request, public_origin)
        try:
            payload = LoginInput.model_validate(body)
        except ValidationError:
            raise failure(422, "VALIDATION_ERROR") from None
        try:
            session = await run_in_threadpool(
                store.login, payload.username, payload.password, client=request.client.host,
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(session.public(include_token=True), headers={"Cache-Control": "no-store"})
        except InvalidCredentials:
            raise failure(401, "INVALID_CREDENTIALS") from None
        except RateLimited as exc:
            raise failure(429, "RATE_LIMITED", **{"Retry-After": str(exc.retry_after)}) from None
        except Exception:
            raise failure(503, "AUTH_UNAVAILABLE") from None

    @router.get("/session")
    async def session(request: Request):
        store = configured_store(request)
        token = bearer_token(request)
        try:
            value = await run_in_threadpool(store.session, token)
            from fastapi.responses import JSONResponse
            return JSONResponse(value.public(), headers={"Cache-Control": "no-store"})
        except InvalidSession:
            raise failure(401, "UNAUTHENTICATED", **{"WWW-Authenticate": "Bearer"}) from None
        except Exception:
            raise failure(503, "AUTH_UNAVAILABLE") from None

    @router.post("/logout")
    async def logout(request: Request):
        store = configured_store(request)
        if await json_body(request, public_origin) != {}:
            raise failure(422, "VALIDATION_ERROR")
        token = bearer_token(request)
        try:
            await run_in_threadpool(store.logout, token)
            from fastapi.responses import JSONResponse
            return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})
        except InvalidSession:
            raise failure(401, "UNAUTHENTICATED", **{"WWW-Authenticate": "Bearer"}) from None
        except Exception:
            raise failure(503, "AUTH_UNAVAILABLE") from None

    return router
