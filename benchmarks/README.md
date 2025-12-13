# Station Calyx Benchmark Stack v1.0

This folder captures configs and schemas for benchmarking Station Calyx with reproducible, governance-aware metrics.

## Structure
- `configs/` — benchmark definitions (outcome density, gpqa lite, swe-lite, run schema)
- `runs/` — raw JSONL logs of benchmark runs
- `reports/` — human-readable summaries
- `datasets/` — local slices of external benchmarks (e.g., gpqa-10, swe-lite-20)

## IDs
- `CB-2025-Q1-OD-001` — Outcome Density run
- `CB-2025-Q1-GPQA-010` — gpqa-10 slice run
- `CB-2025-Q1-SWE-020` — swe-lite-20 run

Configs created:
- `configs/outcome_density_v1.json`
- `configs/gpqa_lite_v1.json`
- `configs/swe_lite_v1.json`
- `configs/run_schema_v1.json`
