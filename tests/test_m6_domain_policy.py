from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.domain_policy import DomainPolicyStore
from app.core.types import ExtractRequest, ExtractResult
from app.extract.fetcher import FetchResult
from app.extract.policy import DomainPolicyBlocked
from app.extract.service import ExtractService


class _FakeFetcher:
    def __init__(self, html: str) -> None:
        self.html = html
        self.calls = 0

    async def fetch_html(self, url: str) -> FetchResult:
        self.calls += 1
        return FetchResult(final_url=url, content=self.html, content_type="text/html", status_code=200)


class _FakeCache:
    def __init__(self) -> None:
        self.value: ExtractResult | None = None
        self.last_ttl: int | None = None

    async def get(self, normalized_url: str) -> ExtractResult | None:
        return self.value

    async def set(self, result: ExtractResult, *, ttl_seconds: int | None = None) -> None:
        self.value = result
        self.last_ttl = ttl_seconds


class DomainPolicyStoreTests(unittest.TestCase):
    def test_resolve_exact_and_wildcard(self) -> None:
        config_text = """
        {
          "default": {"allow": true, "ttl_sec": 600, "render_mode": "auto"},
          "domains": {
            "blocked.example.com": {"allow": false},
            "*.news.example.com": {"ttl_sec": 90}
          }
        }
        """
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(config_text)
            policy_path = tmp.name
        try:
            store = DomainPolicyStore.from_file(policy_path)
        finally:
            Path(policy_path).unlink(missing_ok=True)

        exact = store.resolve("blocked.example.com").policy
        wildcard = store.resolve("api.news.example.com").policy
        default = store.resolve("other.example.com").policy

        self.assertFalse(exact.allow)
        self.assertEqual(exact.ttl_sec, 600)
        self.assertEqual(wildcard.ttl_sec, 90)
        self.assertTrue(default.allow)
        self.assertEqual(default.ttl_sec, 600)

    def test_missing_file_falls_back_to_defaults(self) -> None:
        store = DomainPolicyStore.from_file("Z:/path/does/not/exist.json")
        resolved = store.resolve("example.com").policy
        self.assertTrue(resolved.allow)
        self.assertIsNone(resolved.ttl_sec)

    def test_exact_and_longer_wildcard_have_precedence(self) -> None:
        config_text = """
        {
          "default": {"ttl_sec": 600},
          "domains": {
            "*.example.com": {"ttl_sec": 300},
            "*.news.example.com": {"ttl_sec": 90},
            "api.news.example.com": {"ttl_sec": 15}
          }
        }
        """
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(config_text)
            policy_path = tmp.name
        try:
            store = DomainPolicyStore.from_file(policy_path)
        finally:
            Path(policy_path).unlink(missing_ok=True)

        self.assertEqual(store.resolve("api.news.example.com").policy.ttl_sec, 15)
        self.assertEqual(store.resolve("mobile.news.example.com").policy.ttl_sec, 90)
        self.assertEqual(store.resolve("shop.example.com").policy.ttl_sec, 300)
        self.assertEqual(store.resolve("other.net").policy.ttl_sec, 600)


class ExtractServiceDomainPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_policy_prevents_fetch(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(
                """
                {
                  "domains": {
                    "example.com": {"allow": false}
                  }
                }
                """
            )
            policy_path = tmp.name
        try:
            store = DomainPolicyStore.from_file(policy_path)
        finally:
            Path(policy_path).unlink(missing_ok=True)

        fetcher = _FakeFetcher("<html><p>hello</p></html>")
        cache = _FakeCache()
        service = ExtractService(
            fetcher=fetcher,
            cache=cache,
            url_validator=lambda value: value,
            domain_policy_store=store,
        )

        with self.assertRaises(DomainPolicyBlocked):
            await service.extract(ExtractRequest(url="https://example.com"))
        self.assertEqual(fetcher.calls, 0)

    async def test_policy_ttl_overrides_cache_ttl(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(
                """
                {
                  "domains": {
                    "example.com": {"ttl_sec": 42}
                  }
                }
                """
            )
            policy_path = tmp.name
        try:
            store = DomainPolicyStore.from_file(policy_path)
        finally:
            Path(policy_path).unlink(missing_ok=True)

        fetcher = _FakeFetcher("<html><head><title>T</title></head><body><p>hello</p></body></html>")
        cache = _FakeCache()
        service = ExtractService(
            fetcher=fetcher,
            cache=cache,
            url_validator=lambda value: value,
            domain_policy_store=store,
        )

        result, cached = await service.extract(ExtractRequest(url="https://example.com"))

        self.assertFalse(cached)
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(cache.last_ttl, 42)


if __name__ == "__main__":
    unittest.main()
