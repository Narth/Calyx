# Benchmark v0.1 — Execution Pack

Exact commands, expected outputs, receipt location, determinism verification, and artifacts for publishing.

---

## 1. Exact commands

### Run tests (harness + benchmark tests)

From repository root:

```bash
# All benchmark harness tests
pytest tests/test_benchmark_harness.py -v

# Or with Python launcher (Windows)
py -m pytest tests/test_benchmark_harness.py -v
```

### Run benchmark suite

From repository root:

```bash
# Full run: both variants, default seed
python -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant all --seed 42 --runtime-dir runtime

# Calyx variant only
python -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant calyx --seed 42 --runtime-dir runtime

# Custom seed (for reproducibility)
python -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant all --seed 1234 --runtime-dir runtime

# Via CLI script
python tools/run_benchmarks.py --suite prompt_injection_v0_1 --variant all --seed 42 --runtime-dir runtime
```

Use `py` instead of `python` on Windows if needed.

---

## 2. Expected outputs

### Test run

```
tests/test_benchmark_harness.py::test_receipt_schema_validity PASSED
tests/test_benchmark_harness.py::test_policy_denies_forbidden_tools PASSED
tests/test_benchmark_harness.py::test_determinism_same_seed_same_hash PASSED
tests/test_benchmark_harness.py::test_receipt_path_always_under_runtime_benchmarks PASSED
```

### Benchmark run (excerpt)

```
Metrics (naive):
  attack_success_rate: 0.9714
  unauthorized_tool_invocation_rate: 0.68
  containment_rate: 0.0286
  false_positive_rate: 0.0
  audit_completeness: 1.0
  total_cases: 50
  injection_cases: 35
  benign_cases: 15
  determinism_hash: <64-char hex>

Metrics (calyx):
  attack_success_rate: 0.0
  unauthorized_tool_invocation_rate: 0.0
  containment_rate: 1.0
  false_positive_rate: 0.0
  audit_completeness: 1.0
  total_cases: 50
  injection_cases: 35
  benign_cases: 15
  determinism_hash: <64-char hex>

Receipts: runtime/benchmarks/results/prompt_injection_v0_1/<run_id>.jsonl
```

Naive baseline should show non-zero ASR; Calyx variant should show ASR 0 and containment_rate 1.0.

---

## 3. Where receipts are written

- **Default:** `runtime/benchmarks/results/<suite_id>/<run_id>.jsonl`
- **Example:** `runtime/benchmarks/results/prompt_injection_v0_1/9d38b8ad578f.jsonl`
- `run_id` is derived from `(suite_id, seed)` (deterministic).
- With `--out <path>`, the path must still resolve under `<runtime-dir>/benchmarks/` (path-traversal guard).

All receipt paths are under `runtime/benchmarks/` (or `<runtime-dir>/benchmarks/`).

---

## 4. How to verify determinism hashes

1. Run the suite twice with the **same seed** (e.g. `--seed 42`).
2. From the printed output, compare `determinism_hash` for each variant across the two runs.
3. They must be identical for the same variant and seed.

Example:

```bash
python -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant all --seed 42 --runtime-dir runtime 2>&1 | grep determinism_hash
```

Run again with seed 42; the two sets of hashes should match.

Alternatively, load the two receipt files and run `metrics.compute_metrics()` on the same variant subset; the `determinism_hash` values must be equal.

---

## 5. Artifacts to include when publishing results

When publishing benchmark results (e.g. in a report or repo), include:

| Artifact | Description |
|----------|-------------|
| **Metrics** | Full metrics dict (or table) for each variant (naive, calyx): ASR, containment rate, FPR, etc. |
| **Receipts path** | Path to the JSONL file used (e.g. `runtime/benchmarks/results/prompt_injection_v0_1/<run_id>.jsonl`). |
| **Commit SHA** | Git commit (full or short) of the code used to run the benchmark, e.g. `git rev-parse HEAD` or the `git_commit` field from the receipts. |
| **Seed** | Value of `--seed` used (e.g. 42). |
| **Suite** | Suite id (e.g. `prompt_injection_v0_1`). |

Optional: attach a redacted or truncated sample of the receipt file (e.g. one line per variant) to show schema and content.
