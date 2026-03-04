from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class _TimingStats:
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


class InMemoryMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._timings: dict[str, _TimingStats] = {}

    def inc(self, name: str, value: int = 1) -> None:
        if value < 0:
            raise ValueError("counter increment value must be >= 0")
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def observe_ms(self, name: str, value_ms: float) -> None:
        value = max(0.0, float(value_ms))
        with self._lock:
            stats = self._timings.get(name)
            if stats is None:
                self._timings[name] = _TimingStats(
                    count=1,
                    total_ms=value,
                    min_ms=value,
                    max_ms=value,
                )
                return
            stats.count += 1
            stats.total_ms += value
            stats.min_ms = min(stats.min_ms, value)
            stats.max_ms = max(stats.max_ms, value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            timings = {
                key: {
                    "count": stats.count,
                    "total_ms": round(stats.total_ms, 3),
                    "avg_ms": round((stats.total_ms / stats.count), 3) if stats.count else 0.0,
                    "min_ms": round(stats.min_ms, 3),
                    "max_ms": round(stats.max_ms, 3),
                }
                for key, stats in self._timings.items()
            }
        return {
            "counters": counters,
            "timings": timings,
        }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timings.clear()


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
