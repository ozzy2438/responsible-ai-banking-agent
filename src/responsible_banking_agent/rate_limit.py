from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

import psycopg

if TYPE_CHECKING:
    from .config import Settings


class RateLimitUnavailable(RuntimeError):
    pass


class RateLimiter(Protocol):
    def allow(self, subject_hash: str, route_group: str) -> bool: ...


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self.clock = clock
        self._buckets: dict[tuple[str, str, int], int] = {}
        self._lock = threading.Lock()

    def allow(self, subject_hash: str, route_group: str) -> bool:
        window = int(self.clock() // self.window_seconds)
        key = (subject_hash, route_group, window)
        with self._lock:
            self._buckets = {
                bucket: count for bucket, count in self._buckets.items() if bucket[2] >= window - 1
            }
            count = self._buckets.get(key, 0) + 1
            self._buckets[key] = count
        return count <= self.requests


class PostgresRateLimiter:
    def __init__(self, database_url: str, *, requests: int, window_seconds: int) -> None:
        self.database_url = database_url
        self.requests = requests
        self.window_seconds = window_seconds

    def allow(self, subject_hash: str, route_group: str) -> bool:
        try:
            with psycopg.connect(self.database_url) as connection:
                row = connection.execute(
                    "SELECT consume_rate_limit(%s, %s, %s, %s)",
                    (subject_hash, route_group, self.requests, self.window_seconds),
                ).fetchone()
        except psycopg.Error as exc:
            raise RateLimitUnavailable("Rate limit store is unavailable") from exc
        if row is None:
            raise RateLimitUnavailable("Rate limit store returned no decision")
        return bool(row[0])


def hash_rate_limit_subject(key: str, subject: str) -> str:
    return hmac.new(key.encode(), subject.encode(), hashlib.sha256).hexdigest()


def build_rate_limiter(settings: Settings) -> RateLimiter:
    if settings.rate_limit_backend == "memory":
        return InMemoryRateLimiter(
            requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return PostgresRateLimiter(
        settings.database_url,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
