"""Authenticated CHAT-01 seam. No account writes, procedural retrieval or citations."""

from fastapi import APIRouter, HTTPException, Request, Response

from ..auth import CurrentUser
from .provider import AssistantInvalidOutput, AssistantTimeout, AssistantUnavailable
from .schemas import AssistRequest, AssistResponse
from .service import assist
from .workflow import schema_response


def create_router() -> APIRouter:
    router = APIRouter(prefix="/v1/chat", tags=["draft-form-assistance"])

    @router.get("/schema")
    def get_schema(user: CurrentUser, response: Response) -> dict:
        response.headers["Cache-Control"] = "no-store"
        return schema_response()

    @router.post("/assist", response_model=AssistResponse)
    def post_assist(payload: AssistRequest, user: CurrentUser, request: Request, response: Response) -> AssistResponse:
        response.headers["Cache-Control"] = "no-store"
        if payload.intent == "procedure_question":
            raise HTTPException(503, detail={"code": "RETRIEVAL_UNAVAILABLE"})
        try:
            return assist(payload, getattr(request.app.state, "chat_provider", None))
        except AssistantTimeout:
            raise HTTPException(504, detail={"code": "ASSISTANT_TIMEOUT"}) from None
        except AssistantInvalidOutput:
            raise HTTPException(502, detail={"code": "ASSISTANT_INVALID_OUTPUT"}) from None
        except AssistantUnavailable:
            raise HTTPException(503, detail={"code": "ASSISTANT_UNAVAILABLE"}) from None

    return router
