from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class DomainPolicy:
    allow: bool = True
    ttl_sec: int | None = None
    render_mode: str = "auto"


@dataclass(frozen=True, slots=True)
class DomainPolicyResolution:
    domain: str
    policy: DomainPolicy


class DomainPolicyStore:
    def __init__(
        self,
        *,
        default_policy: DomainPolicy | None = None,
        rules: dict[str, DomainPolicy] | None = None,
    ) -> None:
        self._default_policy = default_policy or DomainPolicy()
        self._rules = dict(rules or {})

    @classmethod
    def from_file(cls, path: str | None) -> "DomainPolicyStore":
        if not path:
            return cls()
        file_path = Path(path)
        if not file_path.exists():
            return cls()

        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("domain policy file root must be an object")

        default_raw = raw.get("default", {})
        if default_raw is None:
            default_raw = {}
        if not isinstance(default_raw, dict):
            raise ValueError("domain policy default must be an object")

        domains_raw = raw.get("domains", {})
        if domains_raw is None:
            domains_raw = {}
        if not isinstance(domains_raw, dict):
            raise ValueError("domain policy domains must be an object")

        default_policy = _parse_policy(default_raw)
        rules: dict[str, DomainPolicy] = {}
        for pattern, policy_raw in domains_raw.items():
            if not isinstance(pattern, str):
                raise ValueError("domain policy key must be a string")
            if not isinstance(policy_raw, dict):
                raise ValueError(f"domain policy for {pattern!r} must be an object")
            rules[pattern.lower()] = _parse_policy(policy_raw, fallback=default_policy)
        return cls(default_policy=default_policy, rules=rules)

    def resolve(self, domain: str) -> DomainPolicyResolution:
        normalized = domain.strip().lower()
        if not normalized:
            raise ValueError("domain must not be empty")

        exact = self._rules.get(normalized)
        if exact is not None:
            return DomainPolicyResolution(domain=normalized, policy=exact)

        wildcard_match = self._match_wildcard(normalized)
        if wildcard_match is not None:
            return DomainPolicyResolution(domain=normalized, policy=wildcard_match)

        return DomainPolicyResolution(domain=normalized, policy=self._default_policy)

    def resolve_url(self, url: str) -> DomainPolicyResolution:
        hostname = urlsplit(url).hostname
        if not hostname:
            raise ValueError("url must include hostname")
        return self.resolve(hostname)

    def _match_wildcard(self, domain: str) -> DomainPolicy | None:
        best_suffix_len = -1
        best_policy = None
        for pattern, policy in self._rules.items():
            if not pattern.startswith("*."):
                continue
            suffix = pattern[2:]
            if not suffix:
                continue
            if domain == suffix or domain.endswith("." + suffix):
                if len(suffix) > best_suffix_len:
                    best_suffix_len = len(suffix)
                    best_policy = policy
        return best_policy


def _parse_policy(raw: dict[str, Any], *, fallback: DomainPolicy | None = None) -> DomainPolicy:
    base = fallback or DomainPolicy()
    allow = _get_bool(raw, "allow", default=base.allow)
    ttl_sec = _get_optional_int(raw, "ttl_sec", default=base.ttl_sec)
    render_mode = _get_str(raw, "render_mode", default=base.render_mode)
    return DomainPolicy(allow=allow, ttl_sec=ttl_sec, render_mode=render_mode)


def _get_bool(raw: dict[str, Any], key: str, *, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _get_optional_int(raw: dict[str, Any], key: str, *, default: int | None) -> int | None:
    value = raw.get(key, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer or null")
    if value < 1:
        raise ValueError(f"{key} must be >= 1")
    return value


def _get_str(raw: dict[str, Any], key: str, *, default: str) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{key} must not be empty")
    return normalized
