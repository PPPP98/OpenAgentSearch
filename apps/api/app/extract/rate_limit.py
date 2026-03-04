from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Callable
from urllib.parse import urlsplit


class DomainRateLimitExceeded(Exception):
    def __init__(self, domain: str, retry_after_seconds: float) -> None:
        self.domain = domain
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"rate limit exceeded for domain={domain}")


@dataclass
class _BucketState:
    tokens: float
    last_updated: float


class DomainTokenBucketLimiter:
    def __init__(
        self,
        *,
        tokens_per_second: float = 1.0,
        burst: int = 3,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if tokens_per_second <= 0:
            raise ValueError("tokens_per_second must be > 0")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        self._tokens_per_second = tokens_per_second
        self._burst = float(burst)
        self._clock = clock
        self._lock = asyncio.Lock()
        self._buckets: dict[str, _BucketState] = {}

    async def acquire(self, normalized_url: str) -> None:
        domain = _extract_domain(normalized_url)
        now = self._clock()

        async with self._lock:
            state = self._buckets.get(domain)
            if state is None:
                state = _BucketState(tokens=self._burst, last_updated=now)
                self._buckets[domain] = state

            elapsed = max(0.0, now - state.last_updated)
            replenished = elapsed * self._tokens_per_second
            state.tokens = min(self._burst, state.tokens + replenished)
            state.last_updated = now

            if state.tokens >= 1.0:
                state.tokens -= 1.0
                return

            missing = 1.0 - state.tokens
            retry_after_seconds = missing / self._tokens_per_second
            raise DomainRateLimitExceeded(
                domain=domain,
                retry_after_seconds=max(0.001, retry_after_seconds),
            )


def _extract_domain(url: str) -> str:
    hostname = urlsplit(url).hostname
    if not hostname:
        raise ValueError("normalized_url must include hostname")
    return hostname.lower()
