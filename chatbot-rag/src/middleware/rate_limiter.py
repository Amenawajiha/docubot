"""In-memory rate limiting middleware for tiered access control."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple, Optional
import threading

from src.utils.config_loader import get_config
from src.utils.log_helper import logger


class InMemoryRateLimiter:
    """
    Track requests per user in memory using timestamps.
    
    Memory structure:
    {
        "user_123": {
            "requests": [2026-04-17 10:00:01, 2026-04-17 10:00:05, ...],
            "tier": "anonymous",
            "concurrent": 0
        }
    }
    """
    
    def __init__(self):
        """Initialize the rate limiter."""
        self.user_data = defaultdict(lambda: {
            "requests": [],
            "tier": "anonymous",
            "concurrent": 0
        })
        self.cleanup_interval = 3600  # Cleanup every hour
        self.last_cleanup = datetime.now()
        
        # === NEW: Thread safety for concurrent WebSocket connections ===
        self.lock = threading.Lock()
        
        # === NEW: Enable/disable rate limiting via config ===
        self.enabled = get_config("rate_limiting.enabled", default=True)
    
    def _cleanup_old_data(self):
        """Remove users with no recent activity to prevent memory bloat."""
        now = datetime.now()
        
        # Only cleanup every hour
        if (now - self.last_cleanup).seconds < self.cleanup_interval:
            return
        
        cutoff = now - timedelta(hours=24)
        removed = 0
        
        # Remove users with all requests older than 24 hours
        users_to_remove = []
        for user_id, data in self.user_data.items():
            if data["requests"]:
                latest = max(data["requests"])
                if latest < cutoff:
                    users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.user_data[user_id]
            removed += 1
        
        self.last_cleanup = now
        if removed > 0:
            logger.info(f"Rate limiter cleanup: removed {removed} inactive users")
    
    def _get_user_tier_config(self, tier: str) -> dict:
        """Get rate limit config for user tier."""
        config = get_config("rate_limiting.tiers", default={})
        return config.get(tier, {
            "requests_per_minute": 3,
            "requests_per_hour": 50,
            "concurrent": 1
        })
    
    def check_rate_limit(
        self,
        user_id: str,
        is_authenticated: bool,
        user_role: str = "user"
    ) -> Tuple[bool, str]:
        """
        Check if user is within rate limits at CONNECTION time.
        This includes concurrent connection checks.
        
        Args:
            user_id: Unique user identifier
            is_authenticated: Whether user provided valid JWT
            user_role: User role (user, uploader, admin)
        
        Returns:
            (allowed: bool, message: str)
        """
        if not self.enabled:
            return True, "OK"
        
        with self.lock:
            # Determine tier
            if user_role == "admin":
                tier = "admin"
            elif is_authenticated:
                tier = "authenticated"
            else:
                tier = "anonymous"
            
            self.user_data[user_id]["tier"] = tier
            config = self._get_user_tier_config(tier)
            
            now = datetime.now()
            
            # === CHECK 1: Per-Minute Limit ===
            minute_ago = now - timedelta(minutes=1)
            recent_requests = [
                ts for ts in self.user_data[user_id]["requests"]
                if ts > minute_ago
            ]
            
            requests_per_minute = config.get("requests_per_minute", 3)
            if len(recent_requests) >= requests_per_minute:
                logger.warning(
                    f"Rate limit (minute) exceeded for {user_id} [{tier}]: "
                    f"{len(recent_requests)}/{requests_per_minute}"
                )
                return False, (
                    f"Too many requests. "
                    f"Limit: {requests_per_minute}/minute. "
                    f"Try again in {60 - (now - recent_requests[0]).seconds}s"
                )
            
            # === CHECK 2: Per-Hour Limit (if configured) ===
            requests_per_hour = config.get("requests_per_hour", -1)
            if requests_per_hour > 0:
                hour_ago = now - timedelta(hours=1)
                hourly_requests = [
                    ts for ts in self.user_data[user_id]["requests"]
                    if ts > hour_ago
                ]
                
                if len(hourly_requests) >= requests_per_hour:
                    logger.warning(
                        f"Rate limit (hour) exceeded for {user_id} [{tier}]: "
                        f"{len(hourly_requests)}/{requests_per_hour}"
                    )
                    return False, (
                        f"Hourly limit reached: {requests_per_hour}/hour. "
                        f"Try again later"
                    )
            
            # === CHECK 3: Concurrent Connections ===
            concurrent_limit = config.get("concurrent", 1)
            if self.user_data[user_id]["concurrent"] >= concurrent_limit:
                logger.warning(
                    f"Concurrent limit exceeded for {user_id} [{tier}]: "
                    f"{self.user_data[user_id]['concurrent']}/{concurrent_limit}"
                )
                return False, (
                    f"Too many active connections. "
                    f"Limit: {concurrent_limit}. "
                    f"Close other tabs or wait for previous request to finish"
                )
            
            # === ALL CHECKS PASSED ===
            # Record this request
            self.user_data[user_id]["requests"].append(now)
            self.user_data[user_id]["concurrent"] += 1
            
            logger.debug(
                f"Rate limit check passed for {user_id} [{tier}] "
                f"({len(recent_requests) + 1}/{requests_per_minute}/min)"
            )
            
            return True, "OK"
    
    def check_message_rate_limit(
        self,
        user_id: str,
        tier: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Check rate limit for individual messages within an active connection.
        Only checks per-minute and per-hour limits (not concurrent).
        
        This is called for EACH MESSAGE sent by the user, not just on connection.
        
        Args:
            user_id: Unique user identifier
            tier: User tier (already determined at connection time)
        
        Returns:
            (allowed: bool, message: str, metadata: dict with retry info)
        
        Example:
            allowed, msg, metadata = rate_limiter.check_message_rate_limit(
                user_id="123",
                tier="authenticated"
            )
            if not allowed:
                await websocket.send_json({
                    "type": "error",
                    "content": msg,
                    "retry_after": metadata["retry_after"]
                })
        """
        if not self.enabled:
            return True, "OK", None
        
        with self.lock:
            config = self._get_user_tier_config(tier)
            now = datetime.now()
            
            # === CHECK 1: Per-Minute Limit ===
            minute_ago = now - timedelta(minutes=1)
            recent_requests = [
                ts for ts in self.user_data[user_id]["requests"]
                if ts > minute_ago
            ]
            
            requests_per_minute = config.get("requests_per_minute", 3)
            if len(recent_requests) >= requests_per_minute:
                oldest = min(recent_requests)
                retry_after = int((oldest + timedelta(minutes=1) - now).total_seconds())
                
                logger.warning(
                    f"Message rate limit (minute) exceeded for {user_id} [{tier}]: "
                    f"{len(recent_requests)}/{requests_per_minute}"
                )
                
                return False, (
                    f"Rate limit: {requests_per_minute} messages/minute. "
                    f"Retry after {retry_after}s"
                ), {
                    "tier": tier,
                    "limit": requests_per_minute,
                    "retry_after": max(1, retry_after),
                    "window": "minute"
                }
            
            # === CHECK 2: Per-Hour Limit ===
            hour_ago = now - timedelta(hours=1)
            hourly_requests = [
                ts for ts in self.user_data[user_id]["requests"]
                if ts > hour_ago
            ]
            
            requests_per_hour = config.get("requests_per_hour", -1)
            if requests_per_hour > 0 and len(hourly_requests) >= requests_per_hour:
                oldest = min(hourly_requests)
                retry_after = int((oldest + timedelta(hours=1) - now).total_seconds())
                
                logger.warning(
                    f"Message rate limit (hour) exceeded for {user_id} [{tier}]: "
                    f"{len(hourly_requests)}/{requests_per_hour}"
                )
                
                return False, (
                    f"Hourly limit: {requests_per_hour} messages/hour. "
                    f"Retry after {retry_after // 60}m"
                ), {
                    "tier": tier,
                    "limit": requests_per_hour,
                    "retry_after": retry_after,
                    "window": "hour"
                }
            
            # === ALL CHECKS PASSED ===
            # Record the message
            self.user_data[user_id]["requests"].append(now)
            
            logger.debug(
                f"Message rate limit check passed for {user_id} [{tier}]: "
                f"({len(recent_requests) + 1}/{requests_per_minute}/min)"
            )
            
            return True, "OK", {
                "tier": tier,
                "remaining_minute": max(0, requests_per_minute - len(recent_requests) - 1),
                "remaining_hour": max(0, requests_per_hour - len(hourly_requests) - 1) if requests_per_hour > 0 else None
            }
    
    def release_connection(self, user_id: str):
        """Release a concurrent connection slot when WebSocket closes."""
        with self.lock:
            if user_id in self.user_data:
                self.user_data[user_id]["concurrent"] = max(
                    0,
                    self.user_data[user_id]["concurrent"] - 1
                )
                logger.debug(f"Released connection for {user_id}")
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get current usage stats for a user (for debugging/admin)."""
        with self.lock:
            if user_id not in self.user_data:
                return {}
            
            now = datetime.now()
            data = self.user_data[user_id]
            
            # Count requests in different windows
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            requests = data["requests"]
            
            return {
                "user_id": user_id,
                "tier": data["tier"],
                "concurrent_connections": data["concurrent"],
                "requests_last_minute": len([r for r in requests if r > minute_ago]),
                "requests_last_hour": len([r for r in requests if r > hour_ago]),
                "requests_last_day": len([r for r in requests if r > day_ago]),
                "first_request": min(requests) if requests else None,
                "last_request": max(requests) if requests else None,
            }


# Global instance
rate_limiter = InMemoryRateLimiter()