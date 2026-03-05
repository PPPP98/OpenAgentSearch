from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .compare import (
    BenchmarkConfig,
    load_env_file,
    load_query_batch,
    run_compare_sync,
    validate_artifact_schema,
    write_artifact,
    write_fixed_query_batch,
)

DEFAULT_OUT_DIR = Path("artifacts/search-compare")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare OpenAgentSearch results with Tavily and save artifacts.")
    parser.add_argument("--mode", choices=("baseline", "run"), default="run")
    parser.add_argument("--run-label", default="")
    parser.add_argument("--queries", type=Path, default=DEFAULT_OUT_DIR / "query_batch.json")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--baseline-path", type=Path, default=DEFAULT_OUT_DIR / "baseline.json")
    parser.add_argument("--local-api-base-url", default=os.getenv("OAS_API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--tavily-api-key", default=os.getenv("TAVILY_API_KEY", ""))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--language", default="all")
    parser.add_argument("--time-range", default="")
    parser.add_argument("--safesearch", type=int, default=1)
    parser.add_argument("--max-extract-chars", type=int, default=6000)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    repo_root_env = Path(__file__).resolve().parents[4] / ".env"
    load_env_file(repo_root_env)
    load_env_file(Path(".env"))
    args = parse_args()

    if not args.tavily_api_key.strip():
        args.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
    if not args.tavily_api_key.strip():
        raise SystemExit("TAVILY_API_KEY is required (env or --tavily-api-key)")

    if not args.queries.exists():
        write_fixed_query_batch(args.queries)
    queries = load_query_batch(args.queries)

    baseline_summary = _load_baseline_summary(args.baseline_path)
    run_label = args.run_label.strip() or args.mode
    config = BenchmarkConfig(
        local_api_base_url=args.local_api_base_url,
        tavily_api_key=args.tavily_api_key,
        query_limit=args.limit,
        language=args.language,
        time_range=args.time_range,
        safesearch=args.safesearch,
        max_extract_chars=args.max_extract_chars,
        timeout_seconds=args.timeout_seconds,
    )

    artifact = run_compare_sync(
        queries,
        config=config,
        run_label=run_label,
        baseline_summary=baseline_summary,
    )

    errors = validate_artifact_schema(artifact)
    if errors:
        raise SystemExit(f"artifact schema validation failed: {errors}")

    out_dir: Path = args.out_dir
    runs_dir = out_dir / "runs"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = runs_dir / f"{stamp}_{run_label}.json"
    latest_path = out_dir / "latest.json"

    write_artifact(run_path, artifact)
    write_artifact(latest_path, artifact)
    if args.mode == "baseline":
        write_artifact(args.baseline_path, artifact)

    summary = artifact["summary"]
    print(f"Saved run artifact: {run_path}")
    if args.mode == "baseline":
        print(f"Updated baseline: {args.baseline_path}")
    print(f"Updated latest: {latest_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _load_baseline_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None
    return summary


if __name__ == "__main__":
    main()
