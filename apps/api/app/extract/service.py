from collections.abc import Callable

from ..core.types import ExtractRequest, ExtractResult
from .cache import RedisExtractCache
from .extractor import chunk_passages, extract_document
from .fetcher import HttpFetcher
from .security import validate_public_url


class ExtractService:
    def __init__(
        self,
        *,
        fetcher: HttpFetcher | None = None,
        cache: RedisExtractCache | None = None,
        url_validator: Callable[[str], str] = validate_public_url,
    ) -> None:
        self._fetcher = fetcher or HttpFetcher()
        self._cache = cache or RedisExtractCache(redis_url=None)
        self._url_validator = url_validator

    async def extract(self, request: ExtractRequest) -> tuple[ExtractResult, bool]:
        normalized_url = self._url_validator(request.url)
        cached_result = await self._cache.get(normalized_url)
        if cached_result is not None:
            return cached_result, True

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
        await self._cache.set(result)
        return result, False
