"""Request boundaries for the independently published customer identity API."""
import asyncio

from starlette.requests import Request

from foundation.crypto.security import check_csrf, keyed_digest
from foundation.errors.public import PublicError, problem
from foundation.ids import uid


class IdentitySecurityMiddleware:
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        state = scope.setdefault("state", {})
        state["request_id"] = uid("req")
        peer = scope.get("client") or ("unknown", 0)
        state["client_hash"] = keyed_digest(peer[0], self.settings.secret_key)[:24]
        request = Request(scope)
        modifying = scope["method"] not in {"GET", "HEAD", "OPTIONS"}

        async def protected_send(message):
            if message["type"] == "http.response.start":
                headers = [(key, value) for key, value in message.get("headers", []) if key.lower() not in {b"x-request-id", b"cache-control", b"x-content-type-options"}]
                headers.extend([
                    (b"x-request-id", state["request_id"].encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                ])
                if self.settings.secure_cookies:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                message["headers"] = headers
            await send(message)

        try:
            origin = request.headers.get("origin")
            if origin and origin != self.settings.portal_origin:
                raise PublicError("ORIGIN_BLOCKED")
            if modifying:
                check_csrf(request, self.settings, "console")
            chunks = []
            size = 0
            if modifying:
                while True:
                    message = await asyncio.wait_for(receive(), timeout=15)
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > self.settings.max_body_bytes:
                        raise PublicError("PAYLOAD_TOO_LARGE")
                    chunks.append(chunk)
                    if not message.get("more_body"):
                        break
        except asyncio.TimeoutError:
            return await problem(request, PublicError("INVALID_INPUT"))(scope, receive, protected_send)
        except PublicError as error:
            return await problem(request, error)(scope, receive, protected_send)

        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if modifying and not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, protected_send)
