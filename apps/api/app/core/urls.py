from dataclasses import replace
from typing import Iterable
import posixpath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .types import SearchResult

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
}
TRACKING_QUERY_PREFIXES = ("utm_",)


def normalize_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("url must not be empty")

    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("url scheme must be http or https")
    if not parts.hostname:
        raise ValueError("url must include hostname")
    if parts.username or parts.password:
        raise ValueError("url must not include credentials")

    hostname = parts.hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = _normalize_path(parts.path)
    query = _normalize_query(parts.query)

    return urlunsplit((scheme, netloc, path, query, ""))


def dedupe_urls(urls: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        normalized = normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def dedupe_search_results(results: Iterable[SearchResult]) -> list[SearchResult]:
    deduped: list[SearchResult] = []
    seen: set[str] = set()
    for result in results:
        try:
            canonical_url = normalize_url(result.url)
        except ValueError:
            canonical_url = result.url
        if canonical_url in seen:
            continue
        seen.add(canonical_url)
        deduped.append(replace(result, url=canonical_url))
    return deduped


def _normalize_path(path: str) -> str:
    if not path:
        return "/"

    normalized = posixpath.normpath(path)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if path.endswith("/") and normalized != "/":
        normalized = f"{normalized}/"
    return normalized


def _normalize_query(query: str) -> str:
    if not query:
        return ""

    params = parse_qsl(query, keep_blank_values=True)
    filtered = []
    for key, value in params:
        normalized_key = key.lower()
        if normalized_key in TRACKING_QUERY_KEYS:
            continue
        if any(normalized_key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        filtered.append((key, value))

    filtered.sort(key=lambda item: (item[0], item[1]))
    return urlencode(filtered, doseq=True)
