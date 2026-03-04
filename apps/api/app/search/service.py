import json
from typing import Any, Literal, Protocol

from ..core.types import ExtractRequest, SearchRequest, SearchResult


class SearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        ...


class ExtractorService(Protocol):
    async def extract(self, request: ExtractRequest) -> tuple[Any, bool]:
        ...


class SearchCache(Protocol):
    async def get(self, cache_key: str) -> dict[str, Any] | None:
        ...

    async def set(self, cache_key: str, payload: dict[str, Any]) -> None:
        ...


class SearchService:
    def __init__(
        self,
        *,
        provider: SearchProvider,
        extract_service: ExtractorService | None,
        cache: SearchCache | None,
    ) -> None:
        self._provider = provider
        self._extract_service = extract_service
        self._cache = cache

    async def search(
        self,
        request: SearchRequest,
        *,
        mode: Literal["speed", "balanced"],
        extract_top_n: int = 3,
        max_extract_chars: int = 6_000,
    ) -> tuple[dict[str, Any], bool]:
        if mode not in {"speed", "balanced"}:
            raise ValueError("mode must be 'speed' or 'balanced'")
        if extract_top_n < 0:
            raise ValueError("extract_top_n must be >= 0")
        if max_extract_chars < 1:
            raise ValueError("max_extract_chars must be >= 1")

        cache_key = _build_cache_key(
            request,
            mode=mode,
            extract_top_n=extract_top_n,
            max_extract_chars=max_extract_chars,
        )
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached, True

        base_results = await self._provider.search(request)
        items = [self._serialize_result(result) for result in base_results]

        if mode == "balanced" and extract_top_n > 0:
            if self._extract_service is None:
                raise ValueError("extract service is required for balanced mode")
            await self._enrich_with_extract(items, extract_top_n, max_extract_chars)

        payload: dict[str, Any] = {
            "query": request.query,
            "mode": mode,
            "limit": request.limit,
            "page": request.page,
            "results": items,
        }
        if self._cache is not None:
            await self._cache.set(cache_key, payload)
        return payload, False

    async def _enrich_with_extract(
        self,
        items: list[dict[str, Any]],
        extract_top_n: int,
        max_extract_chars: int,
    ) -> None:
        assert self._extract_service is not None

        for index, item in enumerate(items):
            item["extract"] = None
            item["extract_error"] = None
            if index >= extract_top_n:
                continue
            try:
                extracted, extracted_cached = await self._extract_service.extract(
                    ExtractRequest(url=item["url"], max_chars=max_extract_chars)
                )
            except Exception as exc:
                item["extract_error"] = str(exc)
                continue

            item["extract"] = {
                "title": extracted.title,
                "markdown": extracted.markdown,
                "passages": list(extracted.passages),
                "content_hash": extracted.content_hash,
                "cached": extracted_cached,
            }

    @staticmethod
    def _serialize_result(result: SearchResult) -> dict[str, Any]:
        return {
            "url": result.url,
            "title": result.title,
            "snippet": result.snippet,
            "source": result.source,
            "score": result.score,
        }


def _build_cache_key(
    request: SearchRequest,
    *,
    mode: str,
    extract_top_n: int,
    max_extract_chars: int,
) -> str:
    payload = {
        "query": request.query,
        "limit": request.limit,
        "page": request.page,
        "categories": list(request.categories),
        "engines": list(request.engines),
        "mode": mode,
        "extract_top_n": extract_top_n,
        "max_extract_chars": max_extract_chars,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)
