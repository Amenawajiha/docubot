"""
Async Redis client — lazy pool initialisation.
This module provides a single function `get_redis()` that returns an async Redis client.
"""

from __future__ import annotations
 
import redis.asyncio as aioredis
 
from app.config import settings
 
_pool: aioredis.ConnectionPool | None = None
 
 
def _get_pool() -> aioredis.ConnectionPool:
    """Create the connection pool lazily on first use."""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool
 
 
async def get_redis() -> aioredis.Redis:
    """Return a Redis client backed by the shared lazy connection pool."""
    return aioredis.Redis(connection_pool=_get_pool())