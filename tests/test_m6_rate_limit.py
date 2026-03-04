from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import ExtractRequest, ExtractResult
from app.extract.fetcher import FetchResult
from app.extract.rate_limit import DomainRateLimitExceeded, DomainTokenBucketLimiter
from app.extract.service import ExtractService


class _ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class _FakeFetcher:
    def __init__(self, html: str) -> None:
        self.html = html
        self.calls = 0

    async def fetch_html(self, url: str) -> FetchResult:
        self.calls += 1
        return FetchResult(final_url=url, content=self.html, content_type="text/html", status_code=200)


class _FakeCache:
    def __init__(self, initial: ExtractResult | None = None) -> None:
        self.value = initial

    async def get(self, normalized_url: str) -> ExtractResult | None:
        return self.value

    async def set(self, result: ExtractResult) -> None:
        self.value = result


class _AlwaysDenyLimiter:
    async def acquire(self, normalized_url: str) -> None:
        raise DomainRateLimitExceeded(domain="example.com", retry_after_seconds=1.5)


class _ExplodeLimiter:
    async def acquire(self, normalized_url: str) -> None:
        raise AssertionError("limiter should not be called when cache hit")


class DomainTokenBucketLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_after_burst_and_recovers_after_refill(self) -> None:
        clock = _ManualClock()
        limiter = DomainTokenBucketLimiter(tokens_per_second=1.0, burst=2, clock=clock.now)

        await limiter.acquire("https://example.com/a")
        await limiter.acquire("https://example.com/b")

        with self.assertRaises(DomainRateLimitExceeded) as ctx:
            await limiter.acquire("https://example.com/c")
        self.assertEqual(ctx.exception.domain, "example.com")
        self.assertGreater(ctx.exception.retry_after_seconds, 0.9)

        clock.advance(1.0)
        await limiter.acquire("https://example.com/d")


class ExtractServiceRateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_raises_when_limiter_denies_miss(self) -> None:
        service = ExtractService(
            fetcher=_FakeFetcher("<html><p>hello</p></html>"),
            cache=_FakeCache(),
            url_validator=lambda value: value,
            domain_limiter=_AlwaysDenyLimiter(),
        )

        with self.assertRaises(DomainRateLimitExceeded):
            await service.extract(ExtractRequest(url="https://example.com"))

    async def test_cache_hit_bypasses_limiter(self) -> None:
        cached_result = ExtractResult(
            url="https://example.com",
            markdown="cached text",
            passages=("cached text",),
            title="Cached",
            content_hash="b" * 64,
        )
        service = ExtractService(
            fetcher=_FakeFetcher("<html><p>ignored</p></html>"),
            cache=_FakeCache(initial=cached_result),
            url_validator=lambda value: value,
            domain_limiter=_ExplodeLimiter(),
        )

        result, cached = await service.extract(ExtractRequest(url="https://example.com"))

        self.assertTrue(cached)
        self.assertEqual(result.markdown, "cached text")


if __name__ == "__main__":
    unittest.main()
