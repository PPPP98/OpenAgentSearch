from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


class OpenAgentSearchApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 20.0,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._auth_header_name = auth_header_name
        self._auth_header_value = auth_header_value

    async def search(
        self,
        payload: dict[str, Any],
        *,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/v1/search",
            payload,
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )

    async def extract(
        self,
        payload: dict[str, Any],
        *,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/v1/extract",
            payload,
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        auth_header_name: str | None,
        auth_header_value: str | None,
    ) -> dict[str, Any]:
        if httpx is None:
            raise RuntimeError("httpx is required to call OpenAgentSearch API")

        headers = self._build_headers(
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, dict):
            raise ValueError("API response must be JSON object")
        return result

    def _build_headers(
        self,
        *,
        auth_header_name: str | None,
        auth_header_value: str | None,
    ) -> dict[str, str]:
        name = auth_header_name or self._auth_header_name
        value = auth_header_value or self._auth_header_value
        if (name and not value) or (value and not name):
            raise ValueError("auth header requires both name and value")
        if not name:
            return {}
        return {name: value}
