# Search Quality Upgrade Final Report

## Run Info
- Baseline artifact: `artifacts/search-compare/baseline.json`
- Final artifact: `artifacts/search-compare/latest.json`
- Baseline run_label: `baseline_v2`
- Final run_label: `final_v2_repeat`

## KPI Check
- Search Jaccard avg: baseline `0.236` -> final `0.322` (target `>= 0.22`) PASS
- Extract token_jaccard avg: baseline `0.898` -> final `0.898` (target `>= 0.64`) PASS
- Noise improvement vs Tavily: baseline `75.0` -> final `75.0` (target `>= 20`) PASS

## Notes
- Search overlap variance exists across repeated runs due upstream index/result churn.
- Extract comparison now retries candidate URLs until both local and Tavily raw extraction are available.
- Query batch is frozen in `artifacts/search-compare/query_batch.json`.
