from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import ExtractRequest, ExtractResult
from app.extract.fetcher import FetchResult
from app.extract.service import ExtractService


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
        self.set_calls = 0

    async def get(self, normalized_url: str) -> ExtractResult | None:
        return self.value

    async def set(self, result: ExtractResult) -> None:
        self.value = result
        self.set_calls += 1


class ExtractServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_returns_markdown_passages_with_limit(self) -> None:
        html = """
        <html><head><title>Doc</title></head><body>
        <p>Hello world</p><p>Another paragraph with enough text for chunking behavior.</p>
        </body></html>
        """
        fetcher = _FakeFetcher(html)
        cache = _FakeCache()
        service = ExtractService(
            fetcher=fetcher,
            cache=cache,
            url_validator=lambda value: value,
        )

        result, cached = await service.extract(ExtractRequest(url="https://example.com", max_chars=40))

        self.assertFalse(cached)
        self.assertEqual(result.url, "https://example.com")
        self.assertLessEqual(len(result.markdown), 40)
        self.assertGreaterEqual(len(result.passages), 1)
        self.assertIsNotNone(result.content_hash)
        self.assertEqual(fetcher.calls, 1)
        self.assertEqual(cache.set_calls, 1)

    async def test_extract_uses_cache_before_fetch(self) -> None:
        cached_result = ExtractResult(
            url="https://example.com",
            markdown="cached text",
            passages=("cached text",),
            title="Cached",
            content_hash="a" * 64,
        )
        fetcher = _FakeFetcher("<html><p>ignored</p></html>")
        cache = _FakeCache(initial=cached_result)
        service = ExtractService(
            fetcher=fetcher,
            cache=cache,
            url_validator=lambda value: value,
        )

        result, cached = await service.extract(ExtractRequest(url="https://example.com"))

        self.assertTrue(cached)
        self.assertEqual(result.markdown, "cached text")
        self.assertEqual(fetcher.calls, 0)
        self.assertEqual(cache.set_calls, 0)


if __name__ == "__main__":
    unittest.main()
