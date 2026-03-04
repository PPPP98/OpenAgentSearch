from pathlib import Path
import json
import logging
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.core.observability import InMemoryMetrics, log_event


class InMemoryMetricsTests(unittest.TestCase):
    def test_counter_and_timing_snapshot(self) -> None:
        metrics = InMemoryMetrics()

        metrics.inc("api.extract.requests_total")
        metrics.inc("api.extract.requests_total")
        metrics.observe_ms("api.extract.latency_ms", 10.0)
        metrics.observe_ms("api.extract.latency_ms", 30.0)

        snapshot = metrics.snapshot()
        counters = snapshot.get("counters", {})
        timings = snapshot.get("timings", {})

        self.assertEqual(counters.get("api.extract.requests_total"), 2)
        self.assertIn("api.extract.latency_ms", timings)
        self.assertEqual(timings["api.extract.latency_ms"]["count"], 2)
        self.assertEqual(timings["api.extract.latency_ms"]["avg_ms"], 20.0)
        self.assertEqual(timings["api.extract.latency_ms"]["min_ms"], 10.0)
        self.assertEqual(timings["api.extract.latency_ms"]["max_ms"], 30.0)

    def test_clear_resets_all_metrics(self) -> None:
        metrics = InMemoryMetrics()
        metrics.inc("api.search.requests_total")
        metrics.observe_ms("api.search.latency_ms", 1.0)
        metrics.clear()

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.get("counters"), {})
        self.assertEqual(snapshot.get("timings"), {})


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())


class LogEventTests(unittest.TestCase):
    def test_log_event_writes_json_payload_with_fields(self) -> None:
        logger = logging.getLogger("test.m6.observability")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = _ListHandler()
        logger.handlers = [handler]
        try:
            log_event(logger, "search.finish", request_id="abc123", status_code=200, outcome="success")
        finally:
            logger.handlers = []

        self.assertEqual(len(handler.records), 1)
        payload = json.loads(handler.records[0])
        self.assertEqual(payload["event"], "search.finish")
        self.assertEqual(payload["request_id"], "abc123")
        self.assertEqual(payload["status_code"], 200)
        self.assertEqual(payload["outcome"], "success")


if __name__ == "__main__":
    unittest.main()
