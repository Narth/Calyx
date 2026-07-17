# RunOps — Benchmark Run Orchestration

RunOps provides a general orchestrator for benchmark run lifecycle: **scan → monitor → verify → report**.

## Usage

### Via presets

```bash
py -m benchmarks.harness.runops --runtime-dir runtime --preset phase4b
```

### Custom run (no preset)

```bash
py -m benchmarks.harness.runops --runtime-dir runtime \
  --run-id autonomous_exec_v0_1_llm \
  --seed 1337 \
  --models tinyllama:latest,qwen2.5-coder:7b \
  --min-valid 2
```

### Phase 4B preset (thin wrapper)

```bash
py -m benchmarks.harness.phase4b_orchestrator --runtime-dir runtime
```

Equivalent to `runops --preset phase4b` plus Phase 4B-specific recommendation output.

## Lifecycle

1. **Scan** — Find runs in `runtime/benchmarks/autonomous/` matching `run_id`, optional `seed` and `models` filters.
2. **Monitor** — For incomplete or active runs (`.run.json.tmp` exists), poll every 15 seconds until completion or 10-minute timeout.
3. **Verify** — Invoke `autonomous_verifier` on each completed run.
4. **Report** — Generate report from valid runs only (exit_status=normal, cases complete, verifier PASS).

## Presets

| Preset   | run_id                             | seed | models                           | min_valid |
|----------|------------------------------------|------|----------------------------------|-----------|
| phase4b  | autonomous_exec_v0_1_llm_phase4b   | 1337 | tinyllama:latest, qwen2.5-coder:7b | 2         |

## Report generators

- **compaction_signal_report** — Capability-based report for plan compaction metrics. Use `write_compaction_signal_report()`.
- **phase4b_minimal_report** — Backward-compatible wrapper; delegates to compaction_signal_report with Phase 4B defaults.

## CLI reference

| Argument      | Description                                |
|---------------|--------------------------------------------|
| `--runtime-dir` | Root (default: runtime)                   |
| `--preset`      | Preset name (phase4b, …)                 |
| `--run-id`      | Run ID pattern (with/without preset)     |
| `--seed`        | Filter by seed                            |
| `--models`      | Comma-separated model_ids to filter       |
| `--min-valid`   | Minimum valid runs for report (default: 1)|

## No behavior changes

RunOps does not modify benchmark execution. It only orchestrates detection, monitoring, verification, and reporting of existing run artifacts.
