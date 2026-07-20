from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from app.services.rate_limit_service import (
    InMemoryRateLimiter,
    RateLimitService,
    RedisRateLimiter,
)


def test_redis_rate_limiter_uses_atomic_counter() -> None:
    client = Mock()
    client.eval.return_value = [2, 48]
    limiter = RedisRateLimiter(client)

    limiter.check("auth:127.0.0.1", limit=10, window_seconds=60)

    client.eval.assert_called_once()


def test_redis_rate_limiter_returns_retry_after() -> None:
    client = Mock()
    client.eval.return_value = [11, 37]
    limiter = RedisRateLimiter(client)

    with pytest.raises(HTTPException) as error:
        limiter.check("auth:127.0.0.1", limit=10, window_seconds=60)

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "37"}


def test_rate_limit_service_falls_back_when_redis_is_unavailable() -> None:
    primary = Mock()
    primary.check.side_effect = ConnectionError("redis unavailable")
    fallback = InMemoryRateLimiter()
    limiter = RateLimitService(primary=primary, fallback=fallback, retry_seconds=30)

    limiter.check("auth:127.0.0.1", limit=1, window_seconds=60)

    with pytest.raises(HTTPException) as error:
        limiter.check("auth:127.0.0.1", limit=1, window_seconds=60)

    assert error.value.status_code == 429
    assert primary.check.call_count == 1


def test_rate_limit_status_reports_redis_failure() -> None:
    primary = Mock()
    primary.ping.side_effect = ConnectionError("redis unavailable")
    limiter = RateLimitService(primary=primary, fallback=InMemoryRateLimiter())

    assert limiter.status() == "unavailable"

