import logging
import os
from dataclasses import dataclass
from uuid import uuid4

from .core.domain_policy import DomainPolicyStore
from .core.observability import InMemoryMetrics
from .extract import DomainTokenBucketLimiter, ExtractService, RedisExtractCache
from .providers import SearxngProvider
from .search import RedisSearchCache, SearchService


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


@dataclass(frozen=True, slots=True)
class AppRuntime:
    logger: logging.Logger
    metrics: InMemoryMetrics
    extract_service: ExtractService
    search_service: SearchService


def build_runtime() -> AppRuntime:
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
    return AppRuntime(
        logger=logging.getLogger("openagentsearch.api"),
        metrics=InMemoryMetrics(),
        extract_service=extract_service,
        search_service=search_service,
    )


runtime = build_runtime()


def new_request_id() -> str:
    return uuid4().hex[:12]
