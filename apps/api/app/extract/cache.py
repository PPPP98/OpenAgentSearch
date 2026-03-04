from dataclasses import asdict
import hashlib
import json

from ..core.types import ExtractResult

try:
    from redis import asyncio as redis_asyncio
except ImportError:  # pragma: no cover
    redis_asyncio = None


class RedisExtractCache:
    def __init__(self, redis_url: str | None, *, ttl_seconds: int = 600) -> None:
        self._redis_url = (redis_url or "").strip()
        self._ttl_seconds = ttl_seconds
        self._client = None

    async def get(self, normalized_url: str) -> ExtractResult | None:
        client = await self._get_client()
        if client is None:
            return None

        key = self._build_key(normalized_url)
        try:
            payload = await client.get(key)
        except Exception:
            return None
        if not payload:
            return None

        try:
            raw = json.loads(payload)
        except json.JSONDecodeError:
            return None
        passages = tuple(raw.get("passages", []))
        return ExtractResult(
            url=str(raw.get("url") or normalized_url),
            markdown=str(raw.get("markdown") or ""),
            passages=passages,
            title=raw.get("title"),
            content_hash=raw.get("content_hash"),
        )

    async def set(self, result: ExtractResult) -> None:
        client = await self._get_client()
        if client is None:
            return

        key = self._build_key(result.url)
        payload = json.dumps(asdict(result), ensure_ascii=False)
        try:
            await client.setex(key, self._ttl_seconds, payload)
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
    def _build_key(url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return f"oas:extract:v1:{digest}"
