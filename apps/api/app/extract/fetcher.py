from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from .security import validate_public_url

DEFAULT_USER_AGENT = "OpenAgentSearch/0.1 (+https://github.com/PPPP98/OpenAgentSearch)"


@dataclass(slots=True, frozen=True)
class FetchResult:
    final_url: str
    content: str
    content_type: str
    status_code: int


class HttpFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        max_redirects: int = 5,
        user_agent: str = DEFAULT_USER_AGENT,
        client: Any = None,
    ) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required to use HttpFetcher")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_redirects = max_redirects
        self._user_agent = user_agent
        self._client = client

    async def fetch_html(self, url: str) -> FetchResult:
        normalized_url = validate_public_url(url)
        if self._client is not None:
            return await self._fetch_with_client(self._client, normalized_url)

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
            return await self._fetch_with_client(client, normalized_url)

    async def _fetch_with_client(self, client: Any, url: str) -> FetchResult:
        current_url = url
        for _ in range(self._max_redirects + 1):
            response = await client.get(
                current_url,
                headers={"User-Agent": self._user_agent},
                follow_redirects=False,
            )
            if 300 <= response.status_code < 400:
                next_url = response.headers.get("location")
                if not next_url:
                    raise ValueError("redirect response missing location header")
                current_url = validate_public_url(urljoin(current_url, next_url))
                continue

            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if not _is_supported_content_type(content_type):
                raise ValueError(f"unsupported content type: {content_type}")

            return FetchResult(
                final_url=current_url,
                content=response.text,
                content_type=content_type,
                status_code=response.status_code,
            )

        raise ValueError("too many redirects")


def _is_supported_content_type(content_type: str) -> bool:
    if not content_type:
        return True
    return (
        "text/html" in content_type
        or "application/xhtml+xml" in content_type
        or "text/plain" in content_type
    )
