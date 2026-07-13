"""
Sliding-window rate limiter backed by Redis.

Algorithm: fixed-window counter with atomic INCR + EXPIRE.
Simple, fast, and correct for our use-case. A true sliding-window
would require a sorted set per key (ZADD/ZRANGEBYSCORE) which is
~5x more expensive per request. The fixed window is acceptable here
because all windows are short (≤ 60s) and the limits are generous
relative to normal human/API usage.

Key format:
    rl:{zone}:{identifier}:{window_bucket}

where window_bucket = int(unix_ts // window_seconds), so all requests
within the same window share the same counter key, and the key expires
automatically one window after the current one.

Usage:
    limiter = RateLimiter(zone="auth_writes", limit=10, window_seconds=60)
    result  = await limiter.check("192.168.1.1")
    if not result.allowed:
        raise RateLimitExceeded(result)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from app.infrastructure.cache.redis_client import get_redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int        # seconds until the window resets
    zone: str
    identifier: str


class RateLimiter:
    """
    Fixed-window rate limiter for one zone.

    Args:
        zone:           Human-readable name for logging and headers.
        limit:          Maximum requests allowed in the window.
        window_seconds: Window duration in seconds.
    """

    def __init__(self, zone: str, limit: int, window_seconds: int) -> None:
        self.zone           = zone
        self.limit          = limit
        self.window_seconds = window_seconds

    async def check(self, identifier: str) -> RateLimitResult:
        """
        Atomically increment the counter for this identifier and window.
        Returns a RateLimitResult immediately — never raises.
        """
        now    = time.time()
        bucket = math.floor(now / self.window_seconds)
        key    = f"rl:{self.zone}:{identifier}:{bucket}"
        # Time until this window expires
        retry_after = self.window_seconds - int(now % self.window_seconds)

        try:
            redis = await get_redis()
            # Pipeline: INCR + EXPIRE in one round trip
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds * 2)   # 2x for safety margin
            results = await pipe.execute()
            count = int(results[0])
        except Exception:
            # Redis unavailable — fail open so the app keeps serving
            return RateLimitResult(
                allowed=True,
                limit=self.limit,
                remaining=self.limit,
                retry_after=retry_after,
                zone=self.zone,
                identifier=identifier,
            )

        allowed   = count <= self.limit
        remaining = max(0, self.limit - count)

        return RateLimitResult(
            allowed=allowed,
            limit=self.limit,
            remaining=remaining,
            retry_after=retry_after if not allowed else 0,
            zone=self.zone,
            identifier=identifier,
        )


def rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    """Standard headers to attach to every response (allowed or blocked)."""
    return {
        "X-RateLimit-Limit":     str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Zone":      result.zone,
        **({"Retry-After": str(result.retry_after)} if not result.allowed else {}),
    }