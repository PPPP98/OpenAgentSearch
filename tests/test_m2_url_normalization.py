from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import SearchResult
from app.core.urls import dedupe_search_results, normalize_url


class UrlNormalizationTests(unittest.TestCase):
    def test_normalize_url_canonicalizes_common_variants(self) -> None:
        raw = "HTTPS://Example.COM:443/a/../b/?utm_source=news&a=1&b=2#fragment"
        self.assertEqual(normalize_url(raw), "https://example.com/b/?a=1&b=2")

    def test_normalize_url_removes_default_http_port(self) -> None:
        self.assertEqual(
            normalize_url("http://Example.com:80/path?q=2"),
            "http://example.com/path?q=2",
        )

    def test_normalize_url_rejects_non_http_scheme(self) -> None:
        with self.assertRaises(ValueError):
            normalize_url("ftp://example.com/file.txt")

    def test_dedupe_search_results_uses_canonical_url(self) -> None:
        results = [
            SearchResult(url="https://example.com/path?utm_source=x&a=1", title="first"),
            SearchResult(url="https://EXAMPLE.com:443/path?a=1", title="duplicate"),
            SearchResult(url="https://example.com/path?a=2", title="second"),
        ]

        deduped = dedupe_search_results(results)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0].title, "first")
        self.assertEqual(deduped[0].url, "https://example.com/path?a=1")
        self.assertEqual(deduped[1].title, "second")
        self.assertEqual(deduped[1].url, "https://example.com/path?a=2")


if __name__ == "__main__":
    unittest.main()
