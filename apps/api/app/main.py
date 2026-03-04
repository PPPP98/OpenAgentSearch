import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .core.types import ExtractRequest
from .extract import ExtractService, RedisExtractCache, SSRFValidationError

app = FastAPI(title="OpenAgentSearch API", version="0.1.0")
extract_service = ExtractService(
    cache=RedisExtractCache(
        redis_url=os.getenv("REDIS_URL"),
        ttl_seconds=int(os.getenv("EXTRACT_CACHE_TTL_SECONDS", "600")),
    )
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
