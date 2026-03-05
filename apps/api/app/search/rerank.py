from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from urllib.parse import parse_qs, urlsplit

from ..core.types import SearchRequest, SearchResult

WORD_RE = re.compile(r"[A-Za-z0-9]+")

DEFAULT_DOMAIN_PRIORS: dict[str, float] = {
    "wikipedia.org": 0.7,
    "arxiv.org": 0.6,
    "docs.python.org": 0.55,
    "developer.mozilla.org": 0.55,
    "github.com": 0.45,
    "kubernetes.io": 0.55,
    "ietf.org": 0.5,
    "openai.com": 0.5,
}


@dataclass(slots=True, frozen=True)
class RerankConfig:
    title_weight: float = 1.5
    snippet_weight: float = 0.8
    domain_weight: float = 0.5
    path_weight: float = 0.35
    diversity_weight: float = 0.35
    source_score_weight: float = 0.05
    domain_priors: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_DOMAIN_PRIORS))


class DeterministicReranker:
    def __init__(self, config: RerankConfig | None = None) -> None:
        self._config = config or RerankConfig()
        self._domain_priors = {key.lower(): float(value) for key, value in self._config.domain_priors.items()}

    def rerank(self, request: SearchRequest, results: list[SearchResult]) -> list[SearchResult]:
        if len(results) <= 1:
            return list(results)

        query_tokens = _tokenize(request.query)
        scored = [
            _ScoredResult(
                result=result,
                base_score=self._base_score(result, query_tokens),
            )
            for result in results
        ]

        ordered = self._diversity_aware_order(scored)
        return [item.result for item in ordered]

    def _base_score(self, result: SearchResult, query_tokens: set[str]) -> float:
        title_score = _overlap_ratio(query_tokens, _tokenize(result.title))
        snippet_score = _overlap_ratio(query_tokens, _tokenize(result.snippet))
        domain_score = self._domain_prior_score(result.url)
        path_score = _path_quality(result.url)
        source_score = _normalized_source_score(result.score)

        return (
            self._config.title_weight * title_score
            + self._config.snippet_weight * snippet_score
            + self._config.domain_weight * domain_score
            + self._config.path_weight * path_score
            + self._config.source_score_weight * source_score
        )

    def _domain_prior_score(self, url: str) -> float:
        host = _extract_host(url)
        if not host:
            return 0.0
        if host in self._domain_priors:
            return self._domain_priors[host]
        for domain, score in self._domain_priors.items():
            if host.endswith(f".{domain}"):
                return score
        return 0.0

    def _diversity_aware_order(self, scored: list["_ScoredResult"]) -> list["_ScoredResult"]:
        remaining = list(scored)
        picked: list[_ScoredResult] = []
        domain_counts: dict[str, int] = {}

        while remaining:
            best = min(
                remaining,
                key=lambda item: (
                    -self._adjusted_score(item, domain_counts),
                    item.result.url,
                ),
            )
            remaining.remove(best)
            picked.append(best)

            domain = _extract_host(best.result.url)
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        return picked

    def _adjusted_score(self, item: "_ScoredResult", domain_counts: dict[str, int]) -> float:
        domain = _extract_host(item.result.url)
        penalty = self._config.diversity_weight * domain_counts.get(domain, 0)
        return item.base_score - penalty


@dataclass(slots=True, frozen=True)
class _ScoredResult:
    result: SearchResult
    base_score: float


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in WORD_RE.finditer(text)}


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left))


def _extract_host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _path_quality(url: str) -> float:
    try:
        parts = urlsplit(url)
    except ValueError:
        return 0.0

    path = parts.path or "/"
    segments = [segment for segment in path.split("/") if segment]
    depth = len(segments)
    score = 1.0
    if depth >= 5:
        score -= 0.45
    elif depth >= 3:
        score -= 0.25
    elif depth >= 1:
        score -= 0.1

    query_params = parse_qs(parts.query, keep_blank_values=True)
    if len(query_params) >= 4:
        score -= 0.15
    if any(key.lower().startswith("utm_") for key in query_params):
        score -= 0.2
    return max(0.0, min(1.0, score))


def _normalized_source_score(score: float | None) -> float:
    if score is None:
        return 0.0
    return 1 / (1 + math.exp(-float(score)))
