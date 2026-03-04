from math import ceil
from time import perf_counter

from fastapi import APIRouter, HTTPException

from ..core.observability import log_event
from ..core.types import ExtractRequest, SearchRequest
from ..extract import DomainPolicyBlocked, DomainRateLimitExceeded, SSRFValidationError
from ..runtime import new_request_id, runtime
from ..schemas import (
    ExtractRequestBody,
    ExtractResponseBody,
    SearchRequestBody,
    SearchResponseBody,
    SearchResultBody,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/internal/metrics")
def internal_metrics() -> dict:
    return runtime.metrics.snapshot()


@router.post("/v1/extract", response_model=ExtractResponseBody)
async def extract(payload: ExtractRequestBody) -> ExtractResponseBody:
    request_id = new_request_id()
    started = perf_counter()
    status_code = 200
    outcome = "success"
    runtime.metrics.inc("api.extract.requests_total")
    log_event(runtime.logger, "extract.start", request_id=request_id, url=payload.url, max_chars=payload.max_chars)
    try:
        result, cached = await runtime.extract_service.extract(
            ExtractRequest(url=payload.url, max_chars=payload.max_chars)
        )
        runtime.metrics.inc("api.extract.success_total")
        runtime.metrics.inc("api.extract.cache_hits_total" if cached else "api.extract.cache_misses_total")
    except SSRFValidationError as exc:
        status_code = 400
        outcome = "error"
        runtime.metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DomainRateLimitExceeded as exc:
        status_code = 429
        outcome = "error"
        runtime.metrics.inc("api.extract.errors_total")
        runtime.metrics.inc("api.extract.rate_limited_total")
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(max(1, ceil(exc.retry_after_seconds)))},
        ) from exc
    except DomainPolicyBlocked as exc:
        status_code = 403
        outcome = "error"
        runtime.metrics.inc("api.extract.errors_total")
        runtime.metrics.inc("api.extract.policy_blocked_total")
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 400
        outcome = "error"
        runtime.metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        status_code = 502
        outcome = "error"
        runtime.metrics.inc("api.extract.errors_total")
        raise HTTPException(status_code=502, detail=f"extract failed: {exc}") from exc
    finally:
        latency_ms = (perf_counter() - started) * 1000.0
        runtime.metrics.observe_ms("api.extract.latency_ms", latency_ms)
        log_event(
            runtime.logger,
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


@router.post("/v1/search", response_model=SearchResponseBody)
async def search(payload: SearchRequestBody) -> SearchResponseBody:
    request_id = new_request_id()
    started = perf_counter()
    status_code = 200
    outcome = "success"
    runtime.metrics.inc("api.search.requests_total")
    log_event(
        runtime.logger,
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
        result_payload, cached = await runtime.search_service.search(
            request,
            mode=payload.mode,
            extract_top_n=payload.extract_top_n,
            max_extract_chars=payload.max_extract_chars,
        )
        runtime.metrics.inc("api.search.success_total")
        runtime.metrics.inc("api.search.cache_hits_total" if cached else "api.search.cache_misses_total")
    except ValueError as exc:
        status_code = 400
        outcome = "error"
        runtime.metrics.inc("api.search.errors_total")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        status_code = 502
        outcome = "error"
        runtime.metrics.inc("api.search.errors_total")
        raise HTTPException(status_code=502, detail=f"search failed: {exc}") from exc
    finally:
        latency_ms = (perf_counter() - started) * 1000.0
        runtime.metrics.observe_ms("api.search.latency_ms", latency_ms)
        log_event(
            runtime.logger,
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
