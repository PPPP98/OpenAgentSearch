from typing import Literal

from pydantic import BaseModel, Field


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
