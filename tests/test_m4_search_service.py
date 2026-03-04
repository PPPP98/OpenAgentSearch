from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import ExtractResult, SearchRequest, SearchResult
from app.search.service import SearchService


class _FakeProvider:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.calls = 0

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        self.calls += 1
        return self._results[: request.limit]


class _FakeExtractService:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, request):
        self.calls += 1
        return (
            ExtractResult(
                url=request.url,
                markdown=f"markdown for {request.url}",
                passages=(f"passage for {request.url}",),
                title="Extracted",
                content_hash="b" * 64,
            ),
            False,
        )


class _FakeCache:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self.set_calls = 0

    async def get(self, cache_key: str):
        return self._store.get(cache_key)

    async def set(self, cache_key: str, payload: dict):
        self._store[cache_key] = payload
        self.set_calls += 1


def _sample_results() -> list[SearchResult]:
    return [
        SearchResult(url="https://example.com/a", title="A", snippet="a"),
        SearchResult(url="https://example.com/b", title="B", snippet="b"),
        SearchResult(url="https://example.com/c", title="C", snippet="c"),
    ]


class SearchServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_speed_mode_returns_serp_only(self) -> None:
        provider = _FakeProvider(_sample_results())
        extractor = _FakeExtractService()
        cache = _FakeCache()
        service = SearchService(provider=provider, extract_service=extractor, cache=cache)

        payload, cached = await service.search(
            SearchRequest(query="agent", limit=2),
            mode="speed",
        )

        self.assertFalse(cached)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(extractor.calls, 0)
        self.assertEqual(cache.set_calls, 1)
        self.assertEqual(len(payload["results"]), 2)
        self.assertNotIn("extract", payload["results"][0])

    async def test_query_cache_hits_on_repeat(self) -> None:
        provider = _FakeProvider(_sample_results())
        extractor = _FakeExtractService()
        cache = _FakeCache()
        service = SearchService(provider=provider, extract_service=extractor, cache=cache)
        request = SearchRequest(query="agent", limit=2)

        first_payload, first_cached = await service.search(request, mode="speed")
        second_payload, second_cached = await service.search(request, mode="speed")

        self.assertFalse(first_cached)
        self.assertTrue(second_cached)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first_payload, second_payload)

    async def test_balanced_mode_extracts_top_n(self) -> None:
        provider = _FakeProvider(_sample_results())
        extractor = _FakeExtractService()
        cache = _FakeCache()
        service = SearchService(provider=provider, extract_service=extractor, cache=cache)

        payload, cached = await service.search(
            SearchRequest(query="agent", limit=3),
            mode="balanced",
            extract_top_n=2,
            max_extract_chars=4000,
        )

        self.assertFalse(cached)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(extractor.calls, 2)
        self.assertIsNotNone(payload["results"][0]["extract"])
        self.assertIsNotNone(payload["results"][1]["extract"])
        self.assertIsNone(payload["results"][2]["extract"])
        self.assertIsNone(payload["results"][2]["extract_error"])


if __name__ == "__main__":
    unittest.main()
