## Calyx Performance Ledger (spec)

- Purpose: aggregate OD, GPQA-lite, SWE-lite per quarter.
- Inputs: benchmarks/runs/*.jsonl
- Fields per entry: run_id, benchmark_id, date, model_stack, hardware, aggregates (OD, accuracy, pass_rate, explanation_score), hallucination_rate, governance metadata (trace_available, hidden_channels_detected, violations, reflection_depth, agii_score), notes.
- Storage: JSONL per quarter under benchmarks/reports/ledger_Q#.jsonl
- Visualization (future): simple tables/plots for OD over time, external accuracy, governance metrics.
