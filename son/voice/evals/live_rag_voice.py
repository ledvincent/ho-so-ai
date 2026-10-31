"""Voice gateway for a separately running Vincent API. No credential loading."""
import argparse
from http.cookies import SimpleCookie
import time
from fastapi import HTTPException, Request
from fake_assistant_api import create_fixture_app
from voice_app.rag_client import RagConversation


def create_live_app(assistant_url, *, transport=None, voice_transport=None):
    # Validate configuration before accepting calls.
    RagConversation(assistant_url)
    app = create_fixture_app(gateway_port=8003, cookie_name="hoso_rag_voice", allow_fixture=False, voice_transport=voice_transport)
    app.title = "Ho So AI — live RAG voice gateway"
    app.description = "Voice consumer of Vincent's separately running API. No personal tools or source approval."
    app.router.routes = [route for route in app.router.routes if getattr(route, "path", "") not in {"/assistant/chat", "/health"}]
    conversations = {}

    @app.get("/health")
    def health():
        return {"status":"ok", "mode":"rag_voice_gateway", "upstream_verified":False}

    @app.middleware("http")
    async def lifecycle(request, call_next):
        if request.method in {"POST", "DELETE"} and request.headers.get("origin") not in {"http://127.0.0.1:8003", "http://localhost:8003"}:
            return await call_next(request)  # Let the origin gate reject before mutation.
        now = time.monotonic()
        for token, (created, _) in list(conversations.items()):
            if now-created > 600:
                conversations.pop(token, None)
        token = request.cookies.get("hoso_rag_voice")
        if request.method == "DELETE" and request.url.path in {"/api/voice/session", "/api/voice/realtime"}:
            conversations.pop(token, None)
        response = await call_next(request)
        if request.method == "POST" and request.url.path == "/api/voice/session" and response.status_code == 200:
            conversations.pop(token, None)
            cookie = SimpleCookie(response.headers.get("set-cookie", ""))
            if "hoso_rag_voice" in cookie and len(conversations) < 1000:
                conversations[cookie["hoso_rag_voice"].value] = (now, RagConversation(assistant_url, transport=transport))
        if "x-hoso-synthetic-fixture" in response.headers:
            del response.headers["x-hoso-synthetic-fixture"]
        return response

    @app.post("/api/voice/rag")
    async def rag(request: Request):
        token = request.cookies.get("hoso_rag_voice")
        entry = conversations.get(token)
        if not entry:
            raise HTTPException(401, "voice_session_required")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 6000:
                raise HTTPException(413)
        import json
        try:
            args = json.loads(body)
            if set(args) - {"question", "clarification_answer", "reset"} or type(args.get("reset", False)) is not bool:
                raise ValueError()
            question = args["question"]
            choice = args.get("clarification_answer")
            if choice is not None and not isinstance(choice, str):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422) from None
        async def cancelled():
            return conversations.get(token) is not entry or await request.is_disconnected()
        # Cancellation is checked before state commits, under the conversation
        # lock. Keep the last completed context so the next spoken turn works.
        return await entry[1].ask(question, clarification_answer=choice,
                                 reset=args.get("reset", False), cancelled=cancelled)
    # The concrete route precedes the diagnostic gateway's allowlisted fallback.
    app.router.routes.insert(0, app.router.routes.pop())
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assistant-url", required=True, help="API origin, no credentials; for example https://backend.example")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_live_app(args.assistant_url), host="127.0.0.1", port=8003, access_log=False)
