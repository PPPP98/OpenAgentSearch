from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.benchmark.compare import (
    SCHEMA_VERSION,
    load_query_batch,
    validate_artifact_schema,
    write_artifact,
    write_fixed_query_batch,
)


class BenchmarkArtifactTests(unittest.TestCase):
    def test_fixed_query_batch_exists_and_has_queries(self) -> None:
        query_path = ROOT / "artifacts" / "search-compare" / "query_batch.json"
        self.assertTrue(query_path.is_file())
        queries = load_query_batch(query_path)
        self.assertGreaterEqual(len(queries), 5)

    def test_write_fixed_query_batch_creates_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "query_batch.json"
            write_fixed_query_batch(path)
            self.assertTrue(path.is_file())
            queries = load_query_batch(path)
            self.assertGreaterEqual(len(queries), 1)

    def test_artifact_schema_validation(self) -> None:
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": "2026-03-05T00:00:00+00:00",
            "run_label": "baseline",
            "config": {"query_count": 1},
            "queries": ["example query"],
            "per_query": [
                {
                    "query": "example query",
                    "search": {
                        "local_urls": ["https://example.com/a"],
                        "tavily_urls": ["https://example.com/a"],
                        "intersection_count": 1,
                        "union_count": 1,
                        "jaccard": 1.0,
                    },
                    "extract": {
                        "selected_url": "https://example.com/a",
                        "selection_reason": "intersection_top_local",
                        "local_chars": 120,
                        "tavily_chars": 110,
                        "token_jaccard": 0.8,
                        "sequence_ratio": 0.5,
                        "local_noise_ratio": 0.1,
                        "tavily_noise_ratio": 0.2,
                        "noise_ratio_delta": 0.1,
                    },
                }
            ],
            "summary": {
                "query_count": 1,
                "search_jaccard_avg": 1.0,
                "extract_token_jaccard_avg": 0.8,
                "extract_sequence_ratio_avg": 0.5,
                "local_noise_ratio_avg": 0.1,
                "tavily_noise_ratio_avg": 0.2,
                "noise_ratio_improvement_vs_tavily_pct": 50.0,
                "noise_ratio_improvement_vs_baseline_pct": None,
            },
        }
        errors = validate_artifact_schema(artifact)
        self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "artifact.json"
            write_artifact(artifact_path, artifact)
            self.assertTrue(artifact_path.is_file())

    def test_artifact_schema_rejects_missing_fields(self) -> None:
        errors = validate_artifact_schema({"schema_version": SCHEMA_VERSION})
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
