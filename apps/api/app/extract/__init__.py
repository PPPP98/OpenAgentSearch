__all__ = [
    "DomainPolicyBlocked",
    "DomainRateLimitExceeded",
    "DomainTokenBucketLimiter",
    "ExtractService",
    "FetchResult",
    "HttpFetcher",
    "RedisExtractCache",
    "SSRFValidationError",
    "validate_public_url",
]


def __getattr__(name: str):
    if name == "DomainPolicyBlocked":
        from .policy import DomainPolicyBlocked

        return DomainPolicyBlocked
    if name == "DomainRateLimitExceeded":
        from .rate_limit import DomainRateLimitExceeded

        return DomainRateLimitExceeded
    if name == "DomainTokenBucketLimiter":
        from .rate_limit import DomainTokenBucketLimiter

        return DomainTokenBucketLimiter
    if name == "ExtractService":
        from .service import ExtractService

        return ExtractService
    if name == "FetchResult":
        from .fetcher import FetchResult

        return FetchResult
    if name == "HttpFetcher":
        from .fetcher import HttpFetcher

        return HttpFetcher
    if name == "RedisExtractCache":
        from .cache import RedisExtractCache

        return RedisExtractCache
    if name == "SSRFValidationError":
        from .security import SSRFValidationError

        return SSRFValidationError
    if name == "validate_public_url":
        from .security import validate_public_url

        return validate_public_url
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
