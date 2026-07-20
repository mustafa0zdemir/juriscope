import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Protocol

from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiterBackend(Protocol):
    def check(self, key: str, limit: int, window_seconds: int) -> None: ...

    def clear(self) -> None: ...

    def ping(self) -> bool: ...


def raise_rate_limit_error(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Çok fazla istek gönderildi. Lütfen kısa bir süre sonra tekrar deneyin",
        headers={"Retry-After": str(max(1, retry_after))},
    )


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        threshold = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= threshold:
                timestamps.popleft()
            if len(timestamps) >= limit:
                raise_rate_limit_error(window_seconds)
            timestamps.append(now)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()

    def ping(self) -> bool:
        return True


class RedisRateLimiter:
    _INCREMENT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

    def __init__(self, client: Redis, key_prefix: str = "rate-limit") -> None:
        self._client = client
        self._key_prefix = key_prefix

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        redis_key = f"{self._key_prefix}:{key}"
        result = self._client.eval(
            self._INCREMENT_SCRIPT,
            1,
            redis_key,
            window_seconds,
        )
        request_count, ttl = int(result[0]), int(result[1])
        if request_count > limit:
            raise_rate_limit_error(ttl if ttl > 0 else window_seconds)

    def clear(self) -> None:
        keys = list(self._client.scan_iter(match=f"{self._key_prefix}:*", count=100))
        if keys:
            self._client.delete(*keys)

    def ping(self) -> bool:
        return bool(self._client.ping())


class RateLimitService:
    def __init__(
        self,
        fallback: RateLimiterBackend,
        primary: RateLimiterBackend | None = None,
        retry_seconds: int = 30,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._retry_seconds = retry_seconds
        self._primary_disabled_until = 0.0
        self._state_lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        if self._primary is not None and monotonic() >= self._primary_disabled_until:
            try:
                self._primary.check(key, limit, window_seconds)
                return
            except HTTPException:
                raise
            except RedisError as exc:
                with self._state_lock:
                    self._primary_disabled_until = monotonic() + self._retry_seconds
                logger.warning(
                    "Redis rate-limit servisine erişilemedi; in-memory fallback kullanılıyor: %s",
                    exc,
                )

        self._fallback.check(key, limit, window_seconds)

    def clear(self) -> None:
        self._fallback.clear()
        if self._primary is not None:
            try:
                self._primary.clear()
            except RedisError:
                logger.debug("Redis rate-limit anahtarları temizlenemedi", exc_info=True)

    def status(self) -> str:
        if self._primary is None:
            return "disabled"
        try:
            return "available" if self._primary.ping() else "unavailable"
        except RedisError:
            return "unavailable"


def create_auth_rate_limiter() -> RateLimitService:
    fallback = InMemoryRateLimiter()
    if not settings.redis_enabled:
        return RateLimitService(fallback=fallback)

    client = Redis.from_url(
        settings.redis_url,
        password=settings.redis_password or None,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        decode_responses=True,
    )
    return RateLimitService(
        fallback=fallback,
        primary=RedisRateLimiter(client=client, key_prefix="auth-rate-limit"),
        retry_seconds=settings.redis_retry_seconds,
    )
