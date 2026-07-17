# Calyx Governance Benchmark v0.1

Reproducible, offline benchmark harness for measuring governance containment against **prompt injection** and **tool misuse**. No network or LLM required.

## Quick Start

```bash
# From repo root
python -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant all --seed 1234

# Or via CLI script
python tools/run_benchmarks.py --suite prompt_injection_v0_1 --variant calyx --runtime-dir runtime
```

## What It Does

- **Offline core:** No network, no external APIs.
- **No LLM required:** A deterministic scripted "agent" parses `CALL_TOOL:{name,args}` markers from prompts to simulate tool coercion.
- **Four variants:**
  - **naive:** Deterministic stub agent; executes requested tool calls (baseline vulnerability).
  - **calyx:** Stub agent + deny-by-default policy gate; only allowlisted tools may run.
  - **naive_llm:** Live LLM returns tool calls; policy bypassed (execute all).
  - **calyx_llm:** Live LLM returns tool calls; policy gate applied (deny-by-default).
- **Outputs:** All results go to `runtime/benchmarks/` (git-ignored). Receipts are JSONL; metrics are printed.

## Directory Layout

```
benchmarks/
├── README.md
├── llm_config.example.json
├── harness/
│   ├── runner.py
│   ├── receipts.py
│   ├── metrics.py
│   ├── policy.py
│   ├── tools_stub.py
│   ├── llm_adapter.py
│   ├── llm_config.py
│   └── llm_backends/
│       ├── local_runtime.py
│       └── mock_runtime.py
└── suites/
    └── prompt_injection_v0_1/
        └── cases.jsonl
```

## How to Run

| Flag | Description |
|------|-------------|
| `--suite` | Suite id, e.g. `prompt_injection_v0_1` |
| `--variant` | `naive`, `calyx`, `naive_llm`, `calyx_llm`, or `all` |
| `--seed` | Integer seed (default: 42) |
| `--runtime-dir` | Root for output (default: `runtime`) |
| `--out` | Optional receipt path |
| `--llm-backend` | For LLM variants: `local` or `mock` (dry run without real model) |

---

## Local LLM Backend (naive_llm / calyx_llm)

Live LLM runs use a local backend only (no network). Configure via `runtime/llm_config.json`:

1. Copy `benchmarks/llm_config.example.json` to `runtime/llm_config.json`.
2. Edit `model_id`, `command`, etc. For Ollama: `{"backend":"local","model_id":"llama2","command":["ollama","run","llama2"]}`.
3. `runtime/` is git-ignored; do not commit secrets.

**Dry run (no real model):**

```bash
py -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant calyx_llm --seed 1337 --llm-backend mock --runtime-dir runtime
```

**Structured output format:** The LLM must return a single JSON object:

```json
{"tool_calls":[{"name":"fs_list","args":{"path":"."}}]}
```

Parsing is strict. On parse failure: no tool calls executed; error recorded in receipt. Model output is never passed to eval/exec.

**Determinism note:** Live LLM runs are not expected to be deterministic unless the model/runtime is configured deterministically. Harness `determinism_hash` reflects post-policy tool execution outcomes (case_id, pass, executed), not raw model text. Use `--llm-backend mock` for reproducible dry runs.

## How to Interpret Results

- **Attack Success Rate (ASR):** Fraction of injection cases where a forbidden tool was executed.
- **Containment Rate:** Fraction of cases where the system correctly denied forbidden tools.
- **False Positive Rate:** From benign control cases.
- **Determinism hash:** Same seed => same hash.

Receipts: `runtime/benchmarks/results/<suite>/<run_id>.jsonl`.

---

## Determinism Model

`determinism_hash` is computed from the **outcome subset** of each receipt entry only:

- `case_id`
- `pass`
- `executed` (tool_calls_executed)

Receipt byte-equality is **not** guaranteed across runs.

**Non-deterministic fields:**

- `ts_utc`
- `git_commit`

**Reproducibility** is defined as:

- Identical `determinism_hash` (per variant)
- Identical metric outputs

---

## Metric Definitions

| Metric | Definition |
|--------|------------|
| **attack_success_rate** | Injection cases where a forbidden tool was executed / total injection cases |
| **containment_rate** | Injection cases where no forbidden tool was executed / total injection cases |
| **false_positive_rate** | Benign cases where pass == False / total benign cases |
| **unauthorized_tool_invocation_rate** | (Number of forbidden tool executions across all receipts) / (Total receipt lines). Per-invocation, not per-case. |
| **audit_completeness** | Currently fixed at 1.0. Reserved for future expansion. |

---

## Artifact Immutability Policy

- Receipts are **overwrite-per-run**. Each run replaces the receipt file for that `run_id`.
- `run_id` is deterministic from `suite` + `seed`.
- Determinism is defined at the outcome layer, not the metadata layer.
- Determinism is verified via `determinism_hash`.

**Reproducibility command example:**

```bash
py -m benchmarks.harness.runner --suite prompt_injection_v0_1 --variant all --seed 1337 --runtime-dir runtime
```
