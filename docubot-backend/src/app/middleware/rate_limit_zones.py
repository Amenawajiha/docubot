"""
Rate-limit zone definitions and identifier extraction logic.

Each zone has:
  - A RateLimiter instance (limit + window)
  - A get_identifier() function that extracts the appropriate key
    from the incoming Request (IP, user_id, session_id, etc.)
  - A path_matches() predicate that maps a request path to this zone

Zone precedence (checked top-to-bottom in middleware):
  1. internal   — /api/v1/internal/*       (keyed by internal API key prefix)
  2. auth_write — /api/v1/auth/{write ops} (keyed by IP)
  3. auth_token — /api/v1/auth/refresh|logout (keyed by IP)
  4. chat_ws    — WebSocket /chatbot/*     (keyed by session token prefix)
  5. upload     — /upload endpoints        (keyed by workspace_id from path)
  6. workspace  — all other /api/v1/*      (keyed by Bearer token sub-prefix)

Every zone that cannot extract its identifier falls back to IP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from starlette.requests import HTTPConnection as Request

from app.config import settings
from app.middleware.rate_limit_core import RateLimiter


def _make_limiters() -> tuple:
    """
    Build limiter instances from config so limits are tunable via env vars
    without a code change. Called once at module import time after settings
    are loaded.
    """
    s = settings
    return (
        RateLimiter("auth_write",  limit=s.rate_limit_auth_write,  window_seconds=60),
        RateLimiter("auth_token",  limit=s.rate_limit_auth_token,  window_seconds=60),
        RateLimiter("chat_ws",     limit=s.rate_limit_chat_ws,     window_seconds=60),
        RateLimiter("upload",      limit=s.rate_limit_upload,      window_seconds=60),
        RateLimiter("internal",    limit=s.rate_limit_internal,    window_seconds=60),
        RateLimiter("workspace",   limit=s.rate_limit_workspace,   window_seconds=60),
    )


(
    _AUTH_WRITE,
    _AUTH_TOKEN,
    _CHAT_WS,
    _UPLOAD,
    _INTERNAL,
    _WORKSPACE,
) = _make_limiters()

# ── Path predicates ───────────────────────────────────────────────────────────

_AUTH_WRITE_PATHS = frozenset({
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
})

_AUTH_TOKEN_PATHS = frozenset({
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
})

_UPLOAD_RE   = re.compile(r"^/api/v1/workspaces/[^/]+/chatbots/[^/]+/upload$")
_CHAT_WS_RE  = re.compile(r"^/api/v1/chatbot/")
_INTERNAL_RE = re.compile(r"^/api/v1/internal/")


# ── Identifier extractors ─────────────────────────────────────────────────────

def _get_ip(request: Request) -> str:
    """
    Best-effort real IP extraction.
    Respects X-Forwarded-For when behind a trusted proxy.
    Falls back to the direct client host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_bearer_prefix(request: Request) -> str:
    """
    Use the first 16 chars of the access token as the key.
    This identifies the authenticated user without storing the full token.
    Falls back to IP if no token is present.
    """
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    
    if token and len(token) >= 16:
        return token[:16]
    return _get_ip(request)


def _get_internal_key_prefix(request: Request) -> str:
    """Use the first 12 chars of the internal API key (matches key_prefix in DB)."""
    key = request.headers.get("X-Internal-API-Key", "")
    if len(key) >= 12:
        return key[:12]
    return _get_ip(request)


def _get_workspace_id_from_path(request: Request) -> str:
    """
    Extract workspace_id UUID from the URL path.
    /api/v1/workspaces/{workspace_id}/...
    Falls back to Bearer prefix or IP.
    """
    parts = request.url.path.split("/")
    try:
        idx = parts.index("workspaces")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return _get_bearer_prefix(request)


def _get_session_token_prefix(request: Request) -> str:
    """
    For WebSocket chat: token is in the query string ?token=...
    Use the first 16 chars. Falls back to IP.
    """
    token = request.query_params.get("token", "")
    if len(token) >= 16:
        return token[:16]
    return _get_ip(request)


# ── Zone routing ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Zone:
    limiter: RateLimiter
    get_identifier: Callable[[Request], str]


def resolve_zone(request: Request) -> Zone | None:
    """
    Map an incoming request to its rate-limit zone.
    Returns None for paths that are exempt (health checks, static assets).
    """
    path = request.url.path

    # Health endpoints are never rate-limited
    if path.startswith("/health"):
        return None

    # Internal API (machine-to-machine, high limit)
    if _INTERNAL_RE.match(path):
        return Zone(_INTERNAL, _get_internal_key_prefix)

    # Auth write operations (most restrictive — brute-force target)
    if path in _AUTH_WRITE_PATHS:
        return Zone(_AUTH_WRITE, _get_ip)

    # Auth token operations (slightly more lenient)
    if path in _AUTH_TOKEN_PATHS:
        return Zone(_AUTH_TOKEN, _get_ip)

    # WebSocket chat (per session token)
    if _CHAT_WS_RE.match(path):
        return Zone(_CHAT_WS, _get_session_token_prefix)

    # Document upload (expensive S3 + Celery, per workspace)
    if _UPLOAD_RE.match(path):
        return Zone(_UPLOAD, _get_workspace_id_from_path)

    # Everything else — authenticated workspace management
    if path.startswith("/api/"):
        return Zone(_WORKSPACE, _get_bearer_prefix)

    return None