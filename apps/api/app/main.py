import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .core.types import ExtractRequest, SearchRequest
from .extract import ExtractService, RedisExtractCache, SSRFValidationError
from .providers import SearxngProvider
from .search import RedisSearchCache, SearchService

app = FastAPI(title="OpenAgentSearch API", version="0.1.0")
searxng_provider = SearxngProvider(
    base_url=os.getenv("SEARXNG_BASE_URL", "http://searxng:8080"),
    timeout_seconds=float(os.getenv("SEARXNG_TIMEOUT_SECONDS", "12")),
)
extract_service = ExtractService(
    cache=RedisExtractCache(
        redis_url=os.getenv("REDIS_URL"),
        ttl_seconds=int(os.getenv("EXTRACT_CACHE_TTL_SECONDS", "600")),
    )
)
search_service = SearchService(
    provider=searxng_provider,
    extract_service=extract_service,
    cache=RedisSearchCache(
        redis_url=os.getenv("REDIS_URL"),
        ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "120")),
    ),
)


class ExtractRequestBody(BaseModel):
    url: str
    max_chars: int = Field(default=20_000, ge=1, le=200_000)


class ExtractResponseBody(BaseModel):
    url: str
    markdown: str
    passages: list[str]
    title: str | None = None
    content_hash: str | None = None
    cached: bool


class SearchRequestBody(BaseModel):
    query: str
    mode: Literal["speed", "balanced"] = "speed"
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1)
    categories: list[str] = Field(default_factory=list)
    engines: list[str] = Field(default_factory=list)
    extract_top_n: int = Field(default=3, ge=0, le=20)
    max_extract_chars: int = Field(default=6_000, ge=1, le=200_000)


class SearchExtractBody(BaseModel):
    title: str | None = None
    markdown: str
    passages: list[str]
    content_hash: str | None = None
    cached: bool


class SearchResultBody(BaseModel):
    url: str
    title: str
    snippet: str
    source: str | None = None
    score: float | None = None
    extract: SearchExtractBody | None = None
    extract_error: str | None = None


class SearchResponseBody(BaseModel):
    query: str
    mode: Literal["speed", "balanced"]
    limit: int
    page: int
    results: list[SearchResultBody]
    cached: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/extract", response_model=ExtractResponseBody)
async def extract(payload: ExtractRequestBody) -> ExtractResponseBody:
    try:
        result, cached = await extract_service.extract(
            ExtractRequest(url=payload.url, max_chars=payload.max_chars)
        )
    except SSRFValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"extract failed: {exc}") from exc

    return ExtractResponseBody(
        url=result.url,
        markdown=result.markdown,
        passages=list(result.passages),
        title=result.title,
        content_hash=result.content_hash,
        cached=cached,
    )


@app.post("/v1/search", response_model=SearchResponseBody)
async def search(payload: SearchRequestBody) -> SearchResponseBody:
    try:
        request = SearchRequest(
            query=payload.query,
            limit=payload.limit,
            page=payload.page,
            categories=tuple(payload.categories),
            engines=tuple(payload.engines),
        )
        result_payload, cached = await search_service.search(
            request,
            mode=payload.mode,
            extract_top_n=payload.extract_top_n,
            max_extract_chars=payload.max_extract_chars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"search failed: {exc}") from exc

    return SearchResponseBody(
        query=str(result_payload.get("query", request.query)),
        mode=str(result_payload.get("mode", payload.mode)),
        limit=int(result_payload.get("limit", request.limit)),
        page=int(result_payload.get("page", request.page)),
        results=[SearchResultBody(**item) for item in result_payload.get("results", [])],
        cached=cached,
    )
