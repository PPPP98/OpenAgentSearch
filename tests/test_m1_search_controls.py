from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.types import SearchRequest
from app.providers.searxng import SearxngProvider
from app.search.service import _build_cache_key


class SearchControlTypeTests(unittest.TestCase):
    def test_search_request_normalizes_controls(self) -> None:
        request = SearchRequest(query=" agent ", language="EN", time_range="MONTH", safesearch=2)
        self.assertEqual(request.query, "agent")
        self.assertEqual(request.language, "en")
        self.assertEqual(request.time_range, "month")
        self.assertEqual(request.safesearch, 2)

    def test_search_request_rejects_invalid_controls(self) -> None:
        with self.assertRaises(ValueError):
            SearchRequest(query="agent", language="english")
        with self.assertRaises(ValueError):
            SearchRequest(query="agent", time_range="week")
        with self.assertRaises(ValueError):
            SearchRequest(query="agent", safesearch=5)


class SearchControlProviderTests(unittest.TestCase):
    def test_provider_params_include_controls(self) -> None:
        request = SearchRequest(
            query="agent",
            page=2,
            language="ko-kr",
            time_range="day",
            safesearch=0,
        )
        params = SearxngProvider._build_params(request)

        self.assertEqual(params["q"], "agent")
        self.assertEqual(params["pageno"], 2)
        self.assertEqual(params["language"], "ko-kr")
        self.assertEqual(params["time_range"], "day")
        self.assertEqual(params["safesearch"], 0)

    def test_cache_key_changes_when_controls_change(self) -> None:
        base = SearchRequest(query="agent", language="all", time_range="", safesearch=1)
        changed = SearchRequest(query="agent", language="en", time_range="month", safesearch=2)

        key_base = _build_cache_key(base, mode="speed", extract_top_n=0, max_extract_chars=1000)
        key_changed = _build_cache_key(changed, mode="speed", extract_top_n=0, max_extract_chars=1000)

        self.assertNotEqual(key_base, key_changed)


if __name__ == "__main__":
    unittest.main()
