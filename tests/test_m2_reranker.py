from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import SearchRequest, SearchResult
from app.search.rerank import DeterministicReranker, RerankConfig
from app.search.service import SearchService


class DeterministicRerankerTests(unittest.TestCase):
    def test_tie_break_is_deterministic_by_url(self) -> None:
        reranker = DeterministicReranker(
            RerankConfig(
                title_weight=0.0,
                snippet_weight=0.0,
                domain_weight=0.0,
                path_weight=0.0,
                diversity_weight=0.0,
                source_score_weight=0.0,
                domain_priors={},
            )
        )
        request = SearchRequest(query="agent")
        results = [
            SearchResult(url="https://example.com/b", title="t"),
            SearchResult(url="https://example.com/a", title="t"),
        ]

        ranked = reranker.rerank(request, results)
        self.assertEqual([item.url for item in ranked], ["https://example.com/a", "https://example.com/b"])

    def test_diversity_penalty_pushes_duplicate_domain_down(self) -> None:
        reranker = DeterministicReranker(
            RerankConfig(
                title_weight=1.0,
                snippet_weight=0.0,
                domain_weight=0.0,
                path_weight=0.0,
                diversity_weight=0.8,
                source_score_weight=0.0,
                domain_priors={},
            )
        )
        request = SearchRequest(query="agent search")
        results = [
            SearchResult(url="https://a.com/1", title="agent search"),
            SearchResult(url="https://a.com/2", title="agent search"),
            SearchResult(url="https://b.com/1", title="agent"),
        ]

        ranked = reranker.rerank(request, results)
        self.assertEqual(ranked[0].url, "https://a.com/1")
        self.assertEqual(ranked[1].url, "https://b.com/1")
        self.assertEqual(ranked[2].url, "https://a.com/2")


class _Provider:
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        return [
            SearchResult(url="https://example.com/1", title="first"),
            SearchResult(url="https://example.com/2", title="second"),
            SearchResult(url="https://example.com/3", title="third"),
        ]


class _Reranker:
    def __init__(self) -> None:
        self.called = False

    def rerank(self, request: SearchRequest, results: list[SearchResult]) -> list[SearchResult]:
        self.called = True
        return list(reversed(results))


class SearchServiceRerankerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_service_applies_reranker_before_limit(self) -> None:
        reranker = _Reranker()
        service = SearchService(
            provider=_Provider(),
            extract_service=None,
            cache=None,
            reranker=reranker,
        )

        payload, cached = await service.search(
            SearchRequest(query="agent", limit=1),
            mode="speed",
        )

        self.assertFalse(cached)
        self.assertTrue(reranker.called)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["url"], "https://example.com/3")


if __name__ == "__main__":
    unittest.main()
