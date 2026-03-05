from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
from typing import Any

import httpx

from ..core.urls import normalize_url

SCHEMA_VERSION = "search-compare.v1"

DEFAULT_QUERY_BATCH = (
    "openai gpt-5 release notes",
    "python asyncio taskgroup tutorial",
    "kubernetes pod security standards",
    "latest ipcc climate report summary",
    "best mechanical keyboard for programming",
)

NOISE_PATTERNS = (
    re.compile(r"\bcookie\b", re.IGNORECASE),
    re.compile(r"\bprivacy\b", re.IGNORECASE),
    re.compile(r"\bterms\b", re.IGNORECASE),
    re.compile(r"\bsubscribe\b", re.IGNORECASE),
    re.compile(r"\bnewsletter\b", re.IGNORECASE),
    re.compile(r"\bsign[\s-]?in\b", re.IGNORECASE),
    re.compile(r"\blog[\s-]?in\b", re.IGNORECASE),
    re.compile(r"\badvert", re.IGNORECASE),
    re.compile(r"\bsponsored\b", re.IGNORECASE),
    re.compile(r"\ball rights reserved\b", re.IGNORECASE),
    re.compile(r"^\s*[#>*-]{0,2}\s*(share|comments|menu)\b", re.IGNORECASE),
)

WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(slots=True, frozen=True)
class BenchmarkConfig:
    local_api_base_url: str = "http://localhost:8000"
    tavily_api_key: str = ""
    query_limit: int = 8
    language: str = "all"
    time_range: str = ""
    safesearch: int = 1
    max_extract_chars: int = 6_000
    timeout_seconds: float = 30.0


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def write_fixed_query_batch(path: Path, queries: tuple[str, ...] = DEFAULT_QUERY_BATCH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"queries": list(queries)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_query_batch(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    queries = payload.get("queries", [])
    if not isinstance(queries, list):
        raise ValueError("query batch file must contain 'queries' list")

    normalized: list[str] = []
    for query in queries:
        text = str(query).strip()
        if text:
            normalized.append(text)
    if not normalized:
        raise ValueError("query batch is empty")
    return normalized


async def compare_queries(
    queries: list[str],
    *,
    config: BenchmarkConfig,
    run_label: str,
    baseline_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not config.tavily_api_key.strip():
        raise ValueError("TAVILY_API_KEY is required")

    timeout = httpx.Timeout(config.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        per_query: list[dict[str, Any]] = []
        for query in queries:
            compared = await _compare_one_query(query, client=client, config=config)
            per_query.append(compared)

    summary = _build_summary(per_query, baseline_summary=baseline_summary)
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_label": run_label,
        "config": {
            "local_api_base_url": config.local_api_base_url,
            "query_limit": config.query_limit,
            "language": config.language,
            "time_range": config.time_range,
            "safesearch": config.safesearch,
            "max_extract_chars": config.max_extract_chars,
            "timeout_seconds": config.timeout_seconds,
            "query_count": len(queries),
        },
        "queries": queries,
        "per_query": per_query,
        "summary": summary,
    }
    errors = validate_artifact_schema(artifact)
    if errors:
        raise ValueError(f"invalid artifact schema: {errors}")
    return artifact


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def validate_artifact_schema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top = ("schema_version", "generated_at", "run_label", "config", "queries", "per_query", "summary")
    for key in required_top:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if not isinstance(payload.get("queries"), list):
        errors.append("queries must be list")
    if not isinstance(payload.get("per_query"), list):
        errors.append("per_query must be list")

    per_query = payload.get("per_query")
    if isinstance(per_query, list):
        for idx, item in enumerate(per_query):
            if not isinstance(item, dict):
                errors.append(f"per_query[{idx}] must be object")
                continue
            if not isinstance(item.get("query"), str):
                errors.append(f"per_query[{idx}].query must be string")

            search = item.get("search")
            if not isinstance(search, dict):
                errors.append(f"per_query[{idx}].search must be object")
            else:
                for key in ("local_urls", "tavily_urls", "intersection_count", "union_count", "jaccard"):
                    if key not in search:
                        errors.append(f"per_query[{idx}].search missing {key}")

            extract = item.get("extract")
            if not isinstance(extract, dict):
                errors.append(f"per_query[{idx}].extract must be object")
            else:
                for key in (
                    "selected_url",
                    "selection_reason",
                    "local_chars",
                    "tavily_chars",
                    "token_jaccard",
                    "sequence_ratio",
                    "local_noise_ratio",
                    "tavily_noise_ratio",
                    "noise_ratio_delta",
                ):
                    if key not in extract:
                        errors.append(f"per_query[{idx}].extract missing {key}")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be object")
    else:
        required_summary = (
            "query_count",
            "search_jaccard_avg",
            "extract_token_jaccard_avg",
            "extract_sequence_ratio_avg",
            "local_noise_ratio_avg",
            "tavily_noise_ratio_avg",
            "noise_ratio_improvement_vs_tavily_pct",
            "noise_ratio_improvement_vs_baseline_pct",
        )
        for key in required_summary:
            if key not in summary:
                errors.append(f"summary missing {key}")

    return errors


async def _compare_one_query(query: str, *, client: httpx.AsyncClient, config: BenchmarkConfig) -> dict[str, Any]:
    local = await _local_search(query, client=client, config=config)
    tavily = await _tavily_search(query, client=client, config=config)

    local_urls = _extract_result_urls(local, limit=config.query_limit)
    tavily_urls = _extract_result_urls(tavily, limit=config.query_limit)
    search_metrics = _search_metrics(local_urls, tavily_urls)

    selected_url = None
    selection_reason = "no_url"
    local_markdown = ""
    tavily_raw = ""
    for candidate_url, candidate_reason in _select_extract_candidates(local_urls, tavily_urls):
        local_candidate = await _local_extract(candidate_url, client=client, config=config)
        tavily_candidate = await _tavily_extract(candidate_url, client=client, config=config)
        if not selected_url and (local_candidate or tavily_candidate):
            selected_url = candidate_url
            selection_reason = candidate_reason
            local_markdown = local_candidate
            tavily_raw = tavily_candidate
        if local_candidate and tavily_candidate:
            selected_url = candidate_url
            selection_reason = candidate_reason
            local_markdown = local_candidate
            tavily_raw = tavily_candidate
            break

    extract_metrics = _extract_metrics(local_markdown, tavily_raw)
    extract_payload = {
        "selected_url": selected_url,
        "selection_reason": selection_reason,
        "local_chars": len(local_markdown),
        "tavily_chars": len(tavily_raw),
        "token_jaccard": extract_metrics["token_jaccard"],
        "sequence_ratio": extract_metrics["sequence_ratio"],
        "local_noise_ratio": extract_metrics["local_noise_ratio"],
        "tavily_noise_ratio": extract_metrics["tavily_noise_ratio"],
        "noise_ratio_delta": extract_metrics["noise_ratio_delta"],
        "local_preview": local_markdown[:280],
        "tavily_preview": tavily_raw[:280],
    }

    return {
        "query": query,
        "search": {
            "local_urls": local_urls,
            "tavily_urls": tavily_urls,
            "intersection_count": search_metrics["intersection_count"],
            "union_count": search_metrics["union_count"],
            "jaccard": search_metrics["jaccard"],
        },
        "extract": extract_payload,
    }


async def _local_search(query: str, *, client: httpx.AsyncClient, config: BenchmarkConfig) -> dict[str, Any]:
    payload = {
        "query": query,
        "mode": "speed",
        "limit": config.query_limit,
        "page": 1,
        "language": config.language,
        "time_range": config.time_range,
        "safesearch": config.safesearch,
    }
    response = await client.post(f"{config.local_api_base_url.rstrip('/')}/v1/search", json=payload)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("local search response must be object")
    return data


async def _tavily_search(query: str, *, client: httpx.AsyncClient, config: BenchmarkConfig) -> dict[str, Any]:
    payload = {
        "api_key": config.tavily_api_key,
        "query": query,
        "max_results": config.query_limit,
        "search_depth": "advanced",
        "include_raw_content": False,
    }
    response = await client.post("https://api.tavily.com/search", json=payload)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("tavily search response must be object")
    return data


async def _local_extract(url: str, *, client: httpx.AsyncClient, config: BenchmarkConfig) -> str:
    payload = {"url": url, "max_chars": config.max_extract_chars}
    response = await client.post(f"{config.local_api_base_url.rstrip('/')}/v1/extract", json=payload)
    if response.status_code >= 400:
        return ""
    data = response.json()
    if not isinstance(data, dict):
        return ""
    return str(data.get("markdown") or "")


async def _tavily_extract(url: str, *, client: httpx.AsyncClient, config: BenchmarkConfig) -> str:
    payload = {
        "api_key": config.tavily_api_key,
        "urls": [url],
        "extract_depth": "advanced",
        "include_images": False,
    }
    response = await client.post("https://api.tavily.com/extract", json=payload)
    if response.status_code >= 400:
        return ""
    data = response.json()
    if not isinstance(data, dict):
        return ""
    results = data.get("results", [])
    if not isinstance(results, list) or not results:
        return ""
    first = results[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("raw_content") or first.get("content") or "")


def _extract_result_urls(payload: dict[str, Any], *, limit: int) -> list[str]:
    raw_items = payload.get("results", [])
    if not isinstance(raw_items, list):
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_url = str(item.get("url") or "").strip()
        if not raw_url:
            continue
        try:
            normalized = normalize_url(raw_url)
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
        if len(urls) >= limit:
            break
    return urls


def _search_metrics(local_urls: list[str], tavily_urls: list[str]) -> dict[str, float | int]:
    local_set = set(local_urls)
    tavily_set = set(tavily_urls)
    intersection = local_set & tavily_set
    union = local_set | tavily_set
    jaccard = (len(intersection) / len(union)) if union else 0.0
    return {
        "intersection_count": len(intersection),
        "union_count": len(union),
        "jaccard": _round(jaccard),
    }


def _select_extract_candidates(local_urls: list[str], tavily_urls: list[str]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    tavily_set = set(tavily_urls)
    for url in local_urls:
        if url in tavily_set:
            candidates.append((url, "intersection_top_local"))
            seen.add(url)
    if local_urls:
        for url in local_urls:
            if url in seen:
                continue
            candidates.append((url, "local_top_only"))
            seen.add(url)
    for url in tavily_urls:
        if url in seen:
            continue
        candidates.append((url, "tavily_top_only"))
        seen.add(url)
    return candidates[:4]


def _extract_metrics(local_text: str, tavily_text: str) -> dict[str, float | None]:
    token_jaccard = _token_jaccard(local_text, tavily_text)
    sequence_ratio = _sequence_ratio(local_text, tavily_text)
    local_noise = _noise_ratio(local_text)
    tavily_noise = _noise_ratio(tavily_text)

    delta = None
    if local_noise is not None and tavily_noise is not None:
        delta = _round(tavily_noise - local_noise)

    return {
        "token_jaccard": token_jaccard,
        "sequence_ratio": sequence_ratio,
        "local_noise_ratio": local_noise,
        "tavily_noise_ratio": tavily_noise,
        "noise_ratio_delta": delta,
    }


def _token_jaccard(left: str, right: str) -> float | None:
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
    if not left_tokens or not right_tokens:
        return None
    # Use overlap coefficient to reduce asymmetry when one extractor returns much longer text.
    denominator = min(len(left_tokens), len(right_tokens))
    if denominator <= 0:
        return None
    return _round(len(left_tokens & right_tokens) / denominator)


def _sequence_ratio(left: str, right: str) -> float | None:
    a = left.strip()
    b = right.strip()
    if not a or not b:
        return None
    return _round(SequenceMatcher(None, a, b).ratio())


def _noise_ratio(text: str) -> float | None:
    candidate = text.strip()
    if not candidate:
        return None

    lines = [line.strip() for line in re.split(r"[\r\n]+", candidate) if line.strip()]
    if len(lines) < 3:
        lines = [line.strip() for line in re.split(r"(?<=[.!?])\s+", candidate) if line.strip()]
    if not lines:
        return None

    noise_lines = 0
    for line in lines:
        if _is_noise_line(line):
            noise_lines += 1
    return _round(noise_lines / len(lines))


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) <= 48 and stripped.count("|") >= 2:
        return True
    if len(stripped) <= 36 and stripped.count("·") >= 2:
        return True
    for pattern in NOISE_PATTERNS:
        if pattern.search(stripped):
            return True
    return False


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def _build_summary(per_query: list[dict[str, Any]], *, baseline_summary: dict[str, Any] | None) -> dict[str, Any]:
    search_values = [item["search"]["jaccard"] for item in per_query]
    token_values = [item["extract"]["token_jaccard"] for item in per_query]
    sequence_values = [item["extract"]["sequence_ratio"] for item in per_query]
    local_noise_values = [item["extract"]["local_noise_ratio"] for item in per_query]
    tavily_noise_values = [item["extract"]["tavily_noise_ratio"] for item in per_query]

    search_avg = _avg(search_values)
    token_avg = _avg(token_values)
    sequence_avg = _avg(sequence_values)
    local_noise_avg = _avg(local_noise_values)
    tavily_noise_avg = _avg(tavily_noise_values)

    noise_improvement_vs_tavily = None
    if local_noise_avg is not None and tavily_noise_avg is not None and tavily_noise_avg > 0:
        noise_improvement_vs_tavily = _round(((tavily_noise_avg - local_noise_avg) / tavily_noise_avg) * 100.0)

    noise_improvement_vs_baseline = None
    baseline_local_noise = None
    if baseline_summary and isinstance(baseline_summary, dict):
        baseline_local_noise = baseline_summary.get("local_noise_ratio_avg")
    if (
        isinstance(baseline_local_noise, (int, float))
        and local_noise_avg is not None
    ):
        if baseline_local_noise > 0:
            noise_improvement_vs_baseline = _round(
                ((baseline_local_noise - local_noise_avg) / baseline_local_noise) * 100.0
            )
        elif baseline_local_noise == 0 and local_noise_avg == 0:
            noise_improvement_vs_baseline = 100.0

    return {
        "query_count": len(per_query),
        "search_jaccard_avg": search_avg,
        "extract_token_jaccard_avg": token_avg,
        "extract_sequence_ratio_avg": sequence_avg,
        "local_noise_ratio_avg": local_noise_avg,
        "tavily_noise_ratio_avg": tavily_noise_avg,
        "noise_ratio_improvement_vs_tavily_pct": noise_improvement_vs_tavily,
        "noise_ratio_improvement_vs_baseline_pct": noise_improvement_vs_baseline,
    }


def _avg(values: list[float | None]) -> float | None:
    valid = [float(value) for value in values if isinstance(value, (float, int))]
    if not valid:
        return None
    return _round(sum(valid) / len(valid))


def _round(value: float) -> float:
    return round(float(value), 3)


def run_compare_sync(
    queries: list[str],
    *,
    config: BenchmarkConfig,
    run_label: str,
    baseline_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        compare_queries(
            queries,
            config=config,
            run_label=run_label,
            baseline_summary=baseline_summary,
        )
    )
