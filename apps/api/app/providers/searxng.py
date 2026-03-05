from typing import Any

import httpx

from ..core.types import SearchRequest, SearchResult
from ..core.urls import dedupe_search_results


class SearxngProvider:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client = client

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        if self._client is not None:
            return await self._search_with_client(self._client, request)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._search_with_client(client, request)

    async def _search_with_client(
        self,
        client: httpx.AsyncClient,
        request: SearchRequest,
    ) -> list[SearchResult]:
        response = await client.get(
            f"{self._base_url}/search",
            params=self._build_params(request),
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()

        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("invalid SearXNG payload: 'results' must be list")

        parsed_results: list[SearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            parsed_results.append(
                SearchResult(
                    url=url,
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("content") or ""),
                    source=_to_optional_string(item.get("engine")),
                    score=_to_optional_float(item.get("score")),
                )
            )

        deduped = dedupe_search_results(parsed_results)
        return deduped

    @staticmethod
    def _build_params(request: SearchRequest) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "q": request.query,
            "format": "json",
            "pageno": request.page,
            "language": request.language,
            "safesearch": request.safesearch,
        }
        if request.time_range:
            params["time_range"] = request.time_range
        if request.categories:
            params["categories"] = ",".join(request.categories)
        if request.engines:
            params["engines"] = ",".join(request.engines)
        return params


def _to_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
