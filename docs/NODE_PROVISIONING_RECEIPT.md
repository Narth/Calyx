# Node Provisioning + Federated Telemetry Receipt (calyx_laptop_01)

## Summary of Changes

### A) Node ID
- **Created:** `runtime/node_id.txt` with content `calyx_laptop_01`

### B) Telemetry Outbox (Append-Only Chunks)
- **Created:** `telemetry/outbox/calyx_laptop_01/` directory
- **Created:** `telemetry/outbox_mirror.py` — mirror module for federated telemetry
- **Modified:** `benchmarks/harness/execution_log.py` — calls `mirror_event` after each `append_event`
- Chunk format: `telemetry/outbox/<node_id>/<YYYYMMDD>_<HHMMSS>__<component>__<shortid>.jsonl`
- Each JSONL line includes: `node_id`, `ts_utc`, `event_id`, `source` (source = bench_harness for harness events)

### C) Node-Scoped Benchmark Outputs
- **Created:** `benchmarks/harness/node_utils.py` — `get_node_id()`, `get_results_dir()`
- **Modified:** `benchmarks/harness/runner.py` — uses `get_results_dir()` for lane receipts; adds `node_id` to envelope
- **Modified:** `benchmarks/harness/autonomous_suite_runner_llm.py` — adds `node_id` to envelope metadata
- New receipt path: `runtime/benchmarks/results/<suite>/<node_id>/` when `node_id` exists
- Prior results in `runtime/benchmarks/results/<suite>/` are **not moved**

### D) Export Mechanism
- **Created:** `tools/telemetry_export.ps1` — packages unexported chunks to timestamped export folder

### E) Smoke Test
- **Created:** `tools/telemetry_smoke_test.ps1` — emits test event, verifies outbox, runs export

---

## File Tree (New/Modified)

```
runtime/
  node_id.txt                                    [NEW]

telemetry/
  outbox/
    calyx_laptop_01/
      .gitkeep                                   [NEW]
  outbox_mirror.py                               [NEW]

benchmarks/harness/
  node_utils.py                                  [NEW]
  execution_log.py                               [MODIFIED]
  runner.py                                      [MODIFIED]
  autonomous_suite_runner_llm.py                 [MODIFIED]

tools/
  telemetry_export.ps1                           [NEW]
  telemetry_smoke_test.ps1                       [NEW]

docs/
  NODE_PROVISIONING_RECEIPT.md                   [NEW]
```

---

## Commands to Export Telemetry for Transfer

**From repo root:**
```powershell
.\tools\telemetry_export.ps1
```

**With explicit repo root:**
```powershell
.\tools\telemetry_export.ps1 -RepoRoot c:\Calyx
```

**Output:** `exports/telemetry_exports/calyx_laptop_01/<YYYYMMDD_HHMMSS>/`
- Contains: chunk JSONL files + `manifest.json` (chunk filenames + sha256)
- Marker updated: `telemetry/outbox/calyx_laptop_01/.exported_index.json`

---

## Smoke Test

```powershell
.\tools\telemetry_smoke_test.ps1 -RepoRoot c:\Calyx
```

1. Emits one test telemetry event (labeled `_smoke_test`)
2. Verifies it lands in `telemetry/outbox/calyx_laptop_01/` with `node_id`, `ts_utc`, `event_id`, `source`
3. Runs `telemetry_export.ps1`
4. Shows export folder, manifest, and SHA256 list

---

## Ladder Run Compatibility

The partial Phase 4B ladder run (tinyllama, qwen2.5:3b completed; qwen2.5:7b timed out) uses:
- `runtime/benchmarks/autonomous/` — unchanged
- `runtime/benchmarks/execution_logs/` — unchanged
- `runtime/benchmarks/reports/` — unchanged

**No prior ladder artifacts were moved.** New benchmark runs (e.g. lane runner with receipts) will write to `runtime/benchmarks/results/<suite>/calyx_laptop_01/`. Autonomous runs continue to use `autonomous/` and `execution_logs/`; only the envelope gains a `node_id` field when present.

To resume or re-run the ladder: increase `MONITOR_TIMEOUT` in `phase4b_miniladder.py` (e.g. to 2700 for 45 min per model) and run again. Existing envelopes in `autonomous/` remain valid.
