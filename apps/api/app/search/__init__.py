__all__ = [
    "RedisSearchCache",
    "SearchService",
]


def __getattr__(name: str):
    if name == "RedisSearchCache":
        from .cache import RedisSearchCache

        return RedisSearchCache
    if name == "SearchService":
        from .service import SearchService

        return SearchService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
