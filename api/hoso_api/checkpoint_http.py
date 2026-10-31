"""Loopback/origin/body boundary for the explicit LOCAL checkpoint only."""

import json

from .local_auth.runtime import is_loopback, valid_auth_origin


class LocalRequestBoundary:
    def __init__(self, app, *, public_origin: str, deployment_mode: str = "local"):
        self.app = app
        self.public_origin = public_origin
        self.deployment_mode = deployment_mode

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(("/v1/", "/v2/")):
            return await self.app(scope, receive, send)

        async def reject(status, code):
            body = json.dumps({"detail": {"code": code}}).encode()
            await send({"type": "http.response.start", "status": status, "headers": [
                (b"content-type", b"application/json"), (b"cache-control", b"no-store"),
                (b"content-length", str(len(body)).encode()),
            ]})
            await send({"type": "http.response.body", "body": body})

        if not valid_auth_origin(self.public_origin, self.deployment_mode):
            return await reject(503, "AUTH_UNAVAILABLE")
        if not scope.get("client") or not is_loopback(scope["client"][0]):
            return await reject(403, "ORIGIN_FORBIDDEN")
        if scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await self.app(scope, receive, send)
        origins = [v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"origin"]
        types = [v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"content-type"]
        if origins != [self.public_origin] or len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "application/json":
            return await reject(403, "ORIGIN_FORBIDDEN")
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > 16384:
                return await reject(413, "REQUEST_TOO_LARGE")
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
