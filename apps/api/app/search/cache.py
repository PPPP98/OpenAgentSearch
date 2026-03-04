import hashlib
import json
from typing import Any

try:
    from redis import asyncio as redis_asyncio
except ImportError:  # pragma: no cover
    redis_asyncio = None


class RedisSearchCache:
    def __init__(self, redis_url: str | None, *, ttl_seconds: int = 120) -> None:
        self._redis_url = (redis_url or "").strip()
        self._ttl_seconds = ttl_seconds
        self._client = None

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        client = await self._get_client()
        if client is None:
            return None

        key = self._build_key(cache_key)
        try:
            payload = await client.get(key)
        except Exception:
            return None
        if not payload:
            return None

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    async def set(self, cache_key: str, payload: dict[str, Any]) -> None:
        client = await self._get_client()
        if client is None:
            return

        key = self._build_key(cache_key)
        serialized = json.dumps(payload, ensure_ascii=False)
        try:
            await client.setex(key, self._ttl_seconds, serialized)
        except Exception:
            return

    async def _get_client(self):
        if not self._redis_url or redis_asyncio is None:
            return None
        if self._client is not None:
            return self._client
        self._client = redis_asyncio.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        return self._client

    @staticmethod
    def _build_key(cache_key: str) -> str:
        digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return f"oas:search:v1:{digest}"
