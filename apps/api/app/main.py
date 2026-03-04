import os
import logging
from math import ceil
from time import perf_counter
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .core.domain_policy import DomainPolicyStore
from .core.observability import InMemoryMetrics, log_event
from .core.types import ExtractRequest, SearchRequest
from .extract import (
    DomainPolicyBlocked,
    DomainRateLimitExceeded,
    DomainTokenBucketLimiter,
    ExtractService,
    RedisExtractCache,
    SSRFValidationError,
)
from .providers import SearxngProvider
from .search import RedisSearchCache, SearchService

app = FastAPI(title="OpenAgentSearch API", version="0.1.0")
logger = logging.getLogger("openagentsearch.api")
metrics = InMemoryMetrics()


def _read_bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _read_float_env(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _read_int_env(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


rate_limit_enabled = _read_bool_env("EXTRACT_RATE_LIMIT_ENABLED", default=True) and not _read_bool_env(
    "OAS_DISABLE_RATE_LIMIT",
    default=False,
)
rate_limit_tokens_per_sec = max(
    0.001,
    _read_float_env("EXTRACT_RATE_LIMIT_TOKENS_PER_SEC", default=1.0),
)
rate_limit_burst = max(
    1,
    _read_int_env("EXTRACT_RATE_LIMIT_BURST", default=3),
)
extract_domain_limiter = (
    DomainTokenBucketLimiter(
        tokens_per_second=rate_limit_tokens_per_sec,
        burst=rate_limit_burst,
    )
    if rate_limit_enabled
    else None
)
domain_policy_store = DomainPolicyStore.from_file(os.getenv("DOMAIN_POLICY_FILE"))

searxng_provider = SearxngProvider(
    base_url=os.getenv("SEARXNG_BASE_URL", "http://searxng:8080"),
    timeout_seconds=float(os.getenv("SEARXNG_TIMEOUT_SECONDS", "12")),
)
extract_service = ExtractService(
    cache=RedisExtractCache(
        redis_url=os.getenv("REDIS_URL"),
        ttl_seconds=int(os.getenv("EXTRACT_CACHE_TTL_SECONDS", "600")),
    ),
    domain_limiter=extract_domain_limiter,
    domain_policy_store=domain_policy_store,
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


def _new_request_id() -> str:
    return uuid4().hex[:12]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/internal/metrics")
def internal_metrics() -> dict:
    return metrics.snapshot()


@app.post("/v1/extract", response_model=ExtractResponseBody)
async def extract(payload: ExtractRequestBody) -> ExtractResponseBody:
    request_id = _new_request_id()
    started = perf_counter()
    status_code = 200
    outcome = "success"
    metrics.inc("api.extract.requests_total")
    log_event(logger, "extract.start", request_id=request_id, url=payload.url, max_chars=payload.max_chars)
    try:
        result, cached = await extract_service.extract(
            ExtractRequest(url=payload.url, max_chars=payload.max_chars)
        )
        metrics.inc("api.extract.success_total")
        metrics.inc("api.extract.cache_hits_total" if cached else "api.extract.cache_misses_total")
    except SSRFValidationError as exc:
        status_code = 400
        outcome = "error"
        metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DomainRateLimitExceeded as exc:
        status_code = 429
        outcome = "error"
        metrics.inc("api.extract.errors_total")
        metrics.inc("api.extract.rate_limited_total")
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(max(1, ceil(exc.retry_after_seconds)))},
        ) from exc
    except DomainPolicyBlocked as exc:
        status_code = 403
        outcome = "error"
        metrics.inc("api.extract.errors_total")
        metrics.inc("api.extract.policy_blocked_total")
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 400
        outcome = "error"
        metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        status_code = 502
        outcome = "error"
        metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=502, detail=f"extract failed: {exc}") from exc
    finally:
        latency_ms = (perf_counter() - started) * 1000.0
        metrics.observe_ms("api.extract.latency_ms", latency_ms)
        log_event(
            logger,
            "extract.finish",
            request_id=request_id,
            status_code=status_code,
            outcome=outcome,
            latency_ms=round(latency_ms, 3),
        )

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
    request_id = _new_request_id()
    started = perf_counter()
    status_code = 200
    outcome = "success"
    metrics.inc("api.search.requests_total")
    log_event(
        logger,
        "search.start",
        request_id=request_id,
        query=payload.query,
        mode=payload.mode,
        limit=payload.limit,
        page=payload.page,
        extract_top_n=payload.extract_top_n,
    )
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
        metrics.inc("api.search.success_total")
        metrics.inc("api.search.cache_hits_total" if cached else "api.search.cache_misses_total")
    except ValueError as exc:
        status_code = 400
        outcome = "error"
        metrics.inc("api.search.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        status_code = 502
        outcome = "error"
        metrics.inc("api.search.errors_total")
        raise HTTPException(status_code=502, detail=f"search failed: {exc}") from exc
    finally:
        latency_ms = (perf_counter() - started) * 1000.0
        metrics.observe_ms("api.search.latency_ms", latency_ms)
        log_event(
            logger,
            "search.finish",
            request_id=request_id,
            status_code=status_code,
            outcome=outcome,
            latency_ms=round(latency_ms, 3),
        )

    return SearchResponseBody(
        query=str(result_payload.get("query", request.query)),
        mode=str(result_payload.get("mode", payload.mode)),
        limit=int(result_payload.get("limit", request.limit)),
        page=int(result_payload.get("page", request.page)),
        results=[SearchResultBody(**item) for item in result_payload.get("results", [])],
        cached=cached,
    )
