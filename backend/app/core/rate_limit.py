from fastapi import Request

from app.config.settings import settings
from app.services.rate_limit_service import (
    InMemoryRateLimiter,
    RateLimitService,
    RedisRateLimiter,
    create_auth_rate_limiter,
)

auth_rate_limiter = create_auth_rate_limiter()


def enforce_auth_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    auth_rate_limiter.check(
        key=f"auth:{client_ip}",
        limit=settings.auth_rate_limit_requests,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )


__all__ = [
    "InMemoryRateLimiter",
    "RateLimitService",
    "RedisRateLimiter",
    "auth_rate_limiter",
    "enforce_auth_rate_limit",
]
