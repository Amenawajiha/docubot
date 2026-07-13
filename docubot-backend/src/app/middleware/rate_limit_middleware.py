"""
RateLimitMiddleware — Starlette ASGI middleware that enforces per-zone limits.

Placement in the middleware stack matters. This must be added AFTER
CORSMiddleware so that CORS preflight OPTIONS requests (which always
come from the browser before the real request) are never blocked.

When a request is blocked:
  - HTTP endpoints receive 429 JSON with Retry-After header
  - WebSocket connections receive a close frame with code 1008
    (Policy Violation) before the handshake completes

When Redis is down:
  - The limiter fails open (allows the request) and logs a warning
  - This is the correct trade-off: Redis downtime should not take
    the API down with it

Response headers added to every non-blocked request:
  X-RateLimit-Limit     — max allowed in this window
  X-RateLimit-Remaining — how many are left in this window
  X-RateLimit-Zone      — which zone matched (for debugging)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from app.config import settings
from app.middleware.rate_limit_core import rate_limit_headers
from app.middleware.rate_limit_zones import resolve_zone

_log = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Pure ASGI middleware (not Starlette's BaseHTTPMiddleware) so that
    WebSocket connections are intercepted before the handshake completes.

    BaseHTTPMiddleware only wraps HTTP — it silently passes WebSocket
    scopes straight through to the app. We need to handle both.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        scope_type = scope["type"]

        # Rate limiting disabled (development / test mode)
        if not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        # Lifespan events — never touch them
        if scope_type == "lifespan":
            await self.app(scope, receive, send)
            return

        # Build a minimal HTTPConnection object for identifier extraction
        request = HTTPConnection(scope, receive)
        zone    = resolve_zone(request)

        if zone is None:
            # Exempt path — pass straight through
            await self.app(scope, receive, send)
            return

        identifier = zone.get_identifier(request)
        result     = await zone.limiter.check(identifier)
        headers    = rate_limit_headers(result)

        if result.allowed:
            if scope_type == "http":
                # Inject rate-limit headers into the response
                await self.app(scope, receive, _inject_headers(send, headers))
            else:
                # WebSocket — allowed, just proceed
                await self.app(scope, receive, send)
            return

        # ── Request is blocked ────────────────────────────────────────────────

        _log.warning(
            "Rate limit exceeded | zone=%s identifier=%s",
            result.zone,
            identifier,
        )

        if scope_type == "http":
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Too many requests. "
                        f"Limit: {result.limit} per {zone.limiter.window_seconds}s. "
                        f"Try again in {result.retry_after}s."
                    ),
                    "zone": result.zone,
                    "retry_after": result.retry_after,
                },
                headers=headers,
            )
            await response(scope, receive, send)

        elif scope_type == "websocket":
            # Accept then immediately close with Policy Violation
            ws = WebSocket(scope, receive, send)
            await ws.accept()
            await ws.close(
                code=1008,
                reason=f"Rate limit exceeded ({result.zone}). "
                       f"Try again in {result.retry_after}s.",
            )


def _inject_headers(
    send: Send, extra_headers: dict[str, str]
) -> Send:
    """
    Wrap the send callable so that rate-limit headers are injected into
    the HTTP response start message without touching the app code.
    """
    async def send_with_headers(message: Any) -> None:
        if message["type"] == "http.response.start":
            raw = list(message.get("headers", []))
            for key, value in extra_headers.items():
                raw.append((key.lower().encode(), value.encode()))
            message = {**message, "headers": raw}
        await send(message)

    return send_with_headers