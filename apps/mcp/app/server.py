import os
from typing import Any

from .client import OpenAgentSearchApiClient

SERVER_NAME = "openagentsearch-mcp"
SERVER_VERSION = "0.1.0"


def create_mcp():
    try:
        from fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("fastmcp is required to run MCP server") from exc

    client = OpenAgentSearchApiClient(
        base_url=os.getenv("OAS_API_BASE_URL", "http://api:8000"),
        timeout_seconds=float(os.getenv("OAS_API_TIMEOUT_SECONDS", "20")),
        auth_header_name=os.getenv("OAS_AUTH_HEADER_NAME"),
        auth_header_value=os.getenv("OAS_AUTH_HEADER_VALUE"),
    )
    mcp = FastMCP(name=SERVER_NAME, version=SERVER_VERSION)

    @mcp.tool(
        name="openagentsearch.search",
        description="Search web results via OpenAgentSearch API. mode=speed returns SERP only, mode=balanced includes extract for top results.",
    )
    async def openagentsearch_search(
        query: str,
        mode: str = "speed",
        limit: int = 10,
        page: int = 1,
        extract_top_n: int = 3,
        max_extract_chars: int = 6000,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
    ) -> dict[str, Any]:
        payload = build_search_payload(
            query=query,
            mode=mode,
            limit=limit,
            page=page,
            extract_top_n=extract_top_n,
            max_extract_chars=max_extract_chars,
        )
        return await client.search(
            payload,
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )

    @mcp.tool(
        name="openagentsearch.extract",
        description="Extract markdown and passages from URL via OpenAgentSearch API.",
    )
    async def openagentsearch_extract(
        url: str,
        max_chars: int = 20_000,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
    ) -> dict[str, Any]:
        payload = build_extract_payload(url=url, max_chars=max_chars)
        return await client.extract(
            payload,
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )

    return mcp


def build_search_payload(
    *,
    query: str,
    mode: str = "speed",
    limit: int = 10,
    page: int = 1,
    extract_top_n: int = 3,
    max_extract_chars: int = 6000,
) -> dict[str, Any]:
    query_value = query.strip()
    if not query_value:
        raise ValueError("query must not be empty")
    mode_value = mode.strip().lower()
    if mode_value not in {"speed", "balanced"}:
        raise ValueError("mode must be 'speed' or 'balanced'")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    if page < 1:
        raise ValueError("page must be >= 1")
    if not 0 <= extract_top_n <= 20:
        raise ValueError("extract_top_n must be between 0 and 20")
    if not 1 <= max_extract_chars <= 200_000:
        raise ValueError("max_extract_chars must be between 1 and 200000")
    return {
        "query": query_value,
        "mode": mode_value,
        "limit": limit,
        "page": page,
        "extract_top_n": extract_top_n,
        "max_extract_chars": max_extract_chars,
    }


def build_extract_payload(*, url: str, max_chars: int = 20_000) -> dict[str, Any]:
    url_value = url.strip()
    if not url_value:
        raise ValueError("url must not be empty")
    if not 1 <= max_chars <= 200_000:
        raise ValueError("max_chars must be between 1 and 200000")
    return {"url": url_value, "max_chars": max_chars}
