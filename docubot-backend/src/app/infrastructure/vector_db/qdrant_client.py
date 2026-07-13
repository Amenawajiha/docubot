"""
Qdrant async client — lazy singleton.

Provides one module-level client shared across the application.
The client is created on the first call to get_qdrant_client(),
not at import time, so the module is safe to import on Windows
before the event loop is running.
"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Return the shared lazy Qdrant client."""
    global _client
    if _client is None:
        kwargs: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        _client = AsyncQdrantClient(**kwargs)
    return _client


async def close_qdrant_client() -> None:
    """Call during app shutdown to release the HTTP connection pool."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None