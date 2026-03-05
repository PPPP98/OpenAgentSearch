# OpenAgentSearch Plan (v2)

## Goal
Improve local search quality and reduce noise in extracted original content.

## Baseline (2026-03-05)
- Search Jaccard average: `0.236` (5-query batch)
- Extract similarity:
  - `token_jaccard`: `0.898`
  - `sequence_ratio`: `0.395`
- Main issue: search overlap variance between repeated runs

## Working Rule
- [x] When one checkbox is completed, commit immediately.
- [x] Tests for each milestone are written after implementation is finished.
- [x] Read this plan and manually check items before closing each milestone.

## Milestones

### M0: Baseline Freeze
- [x] Freeze fixed query batch input
- [x] Run compare script and store baseline artifact
- [x] Save outputs under `artifacts/search-compare/`
- [x] After implementation, add/update baseline artifact format tests
- [x] Run related tests and record pass/fail

Acceptance:
- [x] Baseline metrics are documented
- [x] Baseline run is reproducible with same input/config

### M1: Search Controls End-to-End
- [x] Add `language`, `time_range`, `safesearch` to `/v1/search`
- [x] Pass controls to provider
- [x] Include new controls in cache key
- [x] After implementation, add/update schema/type/cache-key tests
- [x] Run related tests and record pass/fail

Acceptance:
- [x] Control params are validated correctly
- [x] Provider request changes deterministically with controls

### M2: Deterministic Reranker
- [x] Implement reranking weights (title/snippet, domain, path, diversity)
- [x] Externalize weights to config
- [x] Apply reranker before final result output
- [x] After implementation, add/update deterministic ordering/tie tests
- [x] Run related tests and record pass/fail

Acceptance:
- [x] Ranking order is deterministic
- [x] Top results show relevance improvement in benchmark samples

### M3: Extract Noise Reduction
- [x] Keep extractor order: `trafilatura -> readability`
- [x] Improve fallback cleanup for boilerplate/noise tags and patterns
- [x] Keep content-preserving fallback behavior
- [x] After implementation, add/update extract regression tests
- [x] Run related tests and record pass/fail

Acceptance:
- [x] Noise decreases without major content loss
- [x] Validation samples keep main body quality

### M4: Benchmark Automation and Artifacts
- [x] Extend one-off comparison to batch mode
- [x] Save per-query and summary outputs
- [x] Keep result format consistent for repeated runs
- [x] After implementation, add/update artifact schema tests
- [x] Run related tests and record pass/fail

Acceptance:
- [x] Two consecutive runs produce comparable aggregate metrics
- [x] Artifacts are reviewable under `artifacts/search-compare/`

### M5: Quality Gate and Merge
- [x] Run full test suite: `uv run python -m unittest discover -s tests -v`
- [x] Verify KPI targets and write final report
- [x] Re-run benchmark and confirm no regression
- [x] Close milestone checklist and prepare merge

Acceptance:
- [x] Search Jaccard average `>= 0.22`
- [x] Extract `token_jaccard >= 0.64`
- [x] Noise ratio improvement `>= 20%` (vs Tavily noise ratio)
- [x] All required tests pass

## Final Snapshot (2026-03-05)
- Baseline: `artifacts/search-compare/baseline.json`
- Final: `artifacts/search-compare/latest.json`
- Final summary:
  - `search_jaccard_avg`: `0.322`
  - `extract_token_jaccard_avg`: `0.898`
  - `noise_ratio_improvement_vs_tavily_pct`: `75.0`

## Out of Scope
- Adding new external providers
- ML/LLM learned reranker
- Full crawler/index architecture redesign

## Branch Strategy
- Planning branch: `feat/search-quality-upgrade-plan`
- Implementation branch: `feat/search-quality-upgrade-v2`
- Merge to `master` only after M5 acceptance is satisfied
