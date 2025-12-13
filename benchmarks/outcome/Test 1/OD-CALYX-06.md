## calyx bench run-outcome-density (CLI help)

```
Usage: calyx bench run-outcome-density [--run-id ID] [--hours H] [--tasks FILE]

Flags:
  --run-id ID         Benchmark run id (default: auto CB-<date>-OD-XXX)
  --tasks FILE        Task config (default: benchmarks/configs/outcome_density_v1.json)
  --hours H           Optional timebox for the run
  --model NAME        Model stack identifier
  --notes TEXT        Freeform run notes

Behavior:
  - Initializes run jsonl with meta + task entries.
  - Appends per-task results (duration, peaks, insight scores, flags).
  - Computes outcome density aggregates (optional).

Outputs:
  - benchmarks/runs/<run_id>.jsonl (append-only)
  - optional summary in benchmarks/reports/
```
