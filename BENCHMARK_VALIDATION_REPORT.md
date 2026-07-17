# Benchmark Structure + Uniform Execution Guarantees Validation Report
## prompt_injection_v0_2 Lane 2 — qwen2.5-coder:7b

**Date:** 2026-02-13  
**Mode:** Observation-only (no code changes)  
**Git Commit:** `bedcc0442e5efe52d0a1b60e04e031fdcbeecf4d`

---

## STEP 1 — Suite Integrity + Case Enumeration

### Suite Definition

- **Git commit hash:** `bedcc0442e5efe52d0a1b60e04e031fdcbeecf4d`
- **Suite SHA256:** `59d4f9312d9334c4880acda1e5691a986eac3bbc5de2a0ce28f1b1ada4d9b177`
- **Suite file:** `benchmarks/suites/prompt_injection_v0_2/cases.jsonl`
- **Total cases:** 60
- **Attack cases:** 45
- **Benign cases:** 15

### Case IDs in Execution Order (Deterministic)

Cases are loaded in file order (line-by-line read):

1. schema_poison_01
2. schema_poison_02
3. schema_poison_03
4. schema_poison_04
5. schema_poison_05
6. policy_forge_01
7. policy_forge_02
8. policy_forge_03
9. policy_forge_04
10. policy_forge_05
11. hierarchy_inv_01
12. hierarchy_inv_02
13. hierarchy_inv_03
14. hierarchy_inv_04
15. hierarchy_inv_05
16. format_coerce_01
17. format_coerce_02
18. format_coerce_03
19. format_coerce_04
20. format_coerce_05
21. covert_01
22. covert_02
23. covert_03
24. covert_04
25. covert_05
26. multistep_01
27. multistep_02
28. multistep_03
29. multistep_04
30. multistep_05
31. tool_shape_01
32. tool_shape_02
33. tool_shape_03
34. tool_shape_04
35. tool_shape_05
36. role_legacy_01
37. role_legacy_02
38. role_legacy_03
39. role_legacy_04
40. role_legacy_05
41. coerce_legacy_01
42. coerce_legacy_02
43. coerce_legacy_03
44. coerce_legacy_04
45. coerce_legacy_05
46. benign_tempt_01
47. benign_tempt_02
48. benign_tempt_03
49. benign_tempt_04
50. benign_tempt_05
51. benign_standard_01
52. benign_standard_02
53. benign_standard_03
54. benign_standard_04
55. benign_standard_05
56. benign_standard_06
57. benign_standard_07
58. benign_standard_08
59. benign_standard_09
60. benign_standard_10

### Case Order Determination

**Evidence:** `benchmarks/harness/runner.py:154-163`

```python
def load_cases(suite_path: Path) -> list[dict]:
    """Load cases from suite cases.jsonl."""
    cases = []
    with open(suite_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases
```

**Findings:**
- Case order is **deterministic** (file order, line-by-line read)
- **No shuffle** — no random ordering
- **No sort** — no sorting by case_id or category
- **No seed dependency** — seed does NOT affect case order
- Order is **filesystem file order** (sequential line read)

---

## STEP 2 — Run Completeness Audit

### Receipt Analysis

| Run | Receipt Path | Total Lines | Unique Case IDs | Expected Cases | Missing Cases | Last Case ID | Pattern |
|-----|--------------|-------------|-----------------|----------------|---------------|-------------|---------|
| Seed 1337 | `37f6472e96a0__20260213T152454.jsonl` | 60 | 60 | 60 | 0 | `benign_standard_10` | Complete |
| Seed 314159 | `100f91784108__20260213T153851.jsonl` | 60 | 60 | 60 | 0 | `benign_standard_10` | Complete |
| Seed 271828 | `7ee73f2636a0__20260213T154441.jsonl` | 60 | 60 | 60 | 0 | `benign_standard_10` | Complete |

**All three runs completed successfully with all 60 cases.**

### Stop Reason Analysis

**Evidence searched:**
- Harness stdout/stderr logs: **NOT FOUND** (no persistent log files)
- Executor logs: **NOT FOUND** (no correlation ID logs)
- Process exit codes: **NOT RECOVERABLE** (no process tracking artifacts)

**Stop reason determination:** **NOT RECOVERABLE** from current artifacts.

**Note:** All receipts end with `benign_standard_10` (case 60), indicating normal completion.

---

## STEP 3 — Timeout / Early-Termination Checks

### Effective Timeout Configuration

**Runtime Configuration:**
- **File:** `runtime/llm_config.json`
- **Timeout value:** `120` seconds

**Evidence:** `benchmarks/harness/llm_backends/local_runtime.py:20-24`

```python
def __init__(self, config: dict) -> None:
    self.config = config
    self.model_id = config.get("model_id") or "llama2"
    self.command = config.get("command") or ["ollama", "run", self.model_id]
    self.timeout = int(config.get("timeout", 60))
```

**Timeout Scope:** **PER-CASE** (not per-run)

**Evidence:** `benchmarks/harness/llm_backends/local_runtime.py:26-49`

```python
def generate(self, prompt: str, *, seed: int | None = None) -> LLMResponse:
    cmd = list(self.command)
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout,  # Per-case timeout
            cwd=Path(__file__).resolve().parents[3],
        )
```

**Findings:**
- Each `adapter.generate()` call has **independent timeout**
- Timeout applies to `subprocess.run()` per case
- **No global time budget** — harness continues until all cases processed
- Harness does **NOT override timeout** per lane/suite

### Stop Conditions in Harness

**Evidence:** `benchmarks/harness/runner.py:166-209` (`_run_suite`)

**Stop conditions checked:**

1. **Global time budget:** ❌ **NOT IMPLEMENTED**
   - No check for total elapsed time
   - No maximum runtime limit

2. **Max consecutive failures:** ❌ **NOT IMPLEMENTED**
   - No counter for consecutive parse failures
   - No threshold to abort run

3. **Parse failure threshold:** ❌ **NOT IMPLEMENTED**
   - No percentage-based failure threshold
   - No absolute failure count limit

4. **Exception aborts run:** ⚠️ **PARTIAL**
   - **Evidence:** `benchmarks/harness/llm_backends/local_runtime.py:59-67`
   - Exceptions caught **per-case**, return `LLMResponse` with `parse_errors`
   - Loop continues to next case (no abort)
   - **However:** Unhandled exceptions in harness itself would abort run

**Receipt Writing Behavior:**

**Evidence:** `benchmarks/harness/receipts.py:93-94`

```python
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
```

**Findings:**
- Each case writes **immediately** (append mode)
- One line per case (JSON receipt)
- **No explicit flush** — relies on Python file buffering
- **No atomicity guarantee** — partial writes possible on crash

---

## STEP 4 — Uniformity Contract

| **Guaranteed by Harness** | **Not Guaranteed / Variable** |
|--------------------------|-------------------------------|
| **Case order:** Deterministic (file order, no shuffle) | **Case count:** May vary (timeout/exception can stop early) |
| *Evidence:* `runner.py:154-163` (load_cases reads line-by-line) | *Evidence:* `runner.py:179` (for case in cases - no try/except wrapper around loop) |
| **Seed usage:** Affects LLM generation only (adapter.generate seed param) | **Stop conditions:** Per-case timeout, no global budget |
| *Evidence:* `runner.py:108` (`adapter.generate(prompt, seed=seed)`) | *Evidence:* `local_runtime.py:37` (timeout per subprocess.run) |
| **Receipt writing:** Immediate append (one line per case) | **Receipt atomicity:** NOT guaranteed (append mode, no transaction) |
| *Evidence:* `receipts.py:93-94` (`f.write()` per case) | *Evidence:* `receipts.py:93` (open in 'a' mode, no flush guarantee) |
| **Lane 2 direct execution:** Supported via `--lane 2` flag | **Lane 1 gate:** Optional (`--lane auto` checks, `--lane 2` bypasses) |
| *Evidence:* `runner.py:413` (`--lane` choices include '2') | *Evidence:* `runner.py:617` (Lane 2 runs if suite matches, no gate check) |
| **Case iteration:** Sequential, deterministic order | **Early termination:** Possible via timeout, exception, or external kill |
| *Evidence:* `runner.py:179` (`for case in cases:`) | *Evidence:* No global exception handler around case loop |

---

## OBSERVED FACTS

1. **Suite structure:**
   - 60 cases total (45 attack, 15 benign)
   - Case order is deterministic (file order)
   - All case IDs present and unique

2. **Execution completeness:**
   - Seed 1337: **60/60 cases completed**
   - Seed 314159: **60/60 cases completed**
   - Seed 271828: **60/60 cases completed**
   - All receipts end with `benign_standard_10` (case 60)

3. **Timeout configuration:**
   - 120 seconds per case (from `runtime/llm_config.json`)
   - Applied per-case, not per-run
   - No global time budget

4. **Stop conditions:**
   - No global time budget check
   - No max consecutive failures check
   - No parse failure threshold
   - Exceptions caught per-case, loop continues

5. **Receipt writing:**
   - Immediate append mode (one line per case)
   - No explicit flush
   - No atomicity guarantee

---

## INTERPRETATION

**Uniformity guarantees:**
- Case order is **deterministic** and **seed-independent**
- All cases are **attempted** unless process terminates externally
- Receipts are written **immediately** per case (no batching)

**Non-guarantees:**
- Case count may vary if process terminates early
- Receipt atomicity not guaranteed (partial writes possible)
- No global time budget enforcement
- No failure threshold enforcement

---

## UNKNOWNS

1. **Process termination:**
   - No harness stdout/stderr logs available
   - No process exit code tracking
   - Cannot determine if runs completed normally or were interrupted

2. **Receipt file state:**
   - Cannot verify if all writes were flushed to disk
   - Cannot verify if file was complete at termination

3. **Early termination scenarios:**
   - If process killed externally, which cases would be missing?
   - If timeout occurred, would it be per-case or global?
   - If exception occurred, would it abort entire run?

4. **Lane 2 execution without Lane 1:**
   - `--lane 2` bypasses Lane 1 gate check
   - No logging of bypass decision in receipts
   - Cannot determine from receipts whether Lane 1 was run

---

## EVIDENCE SUMMARY

### Code References

- **Case loading:** `benchmarks/harness/runner.py:154-163`
- **Case iteration:** `benchmarks/harness/runner.py:179`
- **Timeout configuration:** `benchmarks/harness/llm_backends/local_runtime.py:24,37`
- **Exception handling:** `benchmarks/harness/llm_backends/local_runtime.py:59-67`
- **Receipt writing:** `benchmarks/harness/receipts.py:93-94`
- **Lane 2 execution:** `benchmarks/harness/runner.py:617`

### Receipt Files Analyzed

- `runtime/benchmarks/results/prompt_injection_v0_2/37f6472e96a0__20260213T152454.jsonl` (seed 1337)
- `runtime/benchmarks/results/prompt_injection_v0_2/100f91784108__20260213T153851.jsonl` (seed 314159)
- `runtime/benchmarks/results/prompt_injection_v0_2/7ee73f2636a0__20260213T154441.jsonl` (seed 271828)

---

**Report generated:** 2026-02-13  
**No code changes proposed** — observation-only validation
