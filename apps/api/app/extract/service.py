from collections.abc import Callable

from ..core.domain_policy import DomainPolicyStore
from ..core.types import ExtractRequest, ExtractResult
from .cache import RedisExtractCache
from .extractor import chunk_passages, extract_document
from .fetcher import HttpFetcher
from .policy import DomainPolicyBlocked
from .rate_limit import DomainTokenBucketLimiter
from .security import validate_public_url


class ExtractService:
    def __init__(
        self,
        *,
        fetcher: HttpFetcher | None = None,
        cache: RedisExtractCache | None = None,
        url_validator: Callable[[str], str] = validate_public_url,
        domain_limiter: DomainTokenBucketLimiter | None = None,
        domain_policy_store: DomainPolicyStore | None = None,
    ) -> None:
        self._fetcher = fetcher or HttpFetcher()
        self._cache = cache or RedisExtractCache(redis_url=None)
        self._url_validator = url_validator
        self._domain_limiter = domain_limiter
        self._domain_policy_store = domain_policy_store or DomainPolicyStore()

    async def extract(self, request: ExtractRequest) -> tuple[ExtractResult, bool]:
        normalized_url = self._url_validator(request.url)
        cached_result = await self._cache.get(normalized_url)
        if cached_result is not None:
            return cached_result, True

        policy_resolution = self._domain_policy_store.resolve_url(normalized_url)
        if not policy_resolution.policy.allow:
            raise DomainPolicyBlocked(policy_resolution.domain)

        if self._domain_limiter is not None:
            await self._domain_limiter.acquire(normalized_url)

        fetched = await self._fetcher.fetch_html(normalized_url)
        document = extract_document(fetched.content, max_chars=request.max_chars)
        passages = chunk_passages(document.markdown)

        result = ExtractResult(
            url=fetched.final_url,
            markdown=document.markdown,
            passages=passages,
            title=document.title,
            content_hash=document.content_hash,
        )
        ttl_seconds = policy_resolution.policy.ttl_sec
        await self._set_cache(result, ttl_seconds=ttl_seconds)
        return result, False

    async def _set_cache(self, result: ExtractResult, *, ttl_seconds: int | None) -> None:
        if ttl_seconds is None:
            await self._cache.set(result)
            return
        try:
            await self._cache.set(result, ttl_seconds=ttl_seconds)
        except TypeError:
            await self._cache.set(result)
