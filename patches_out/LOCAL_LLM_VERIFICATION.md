# Local LLM / benchmark harness — verification (CBO Core)

**Date:** 2026-02-21  
**Update:** Local LLM is **wired** as of same day. CBO Core now routes `model_role=local` to Ollama via `_call_local()`.

---

## 0. Local LLM wiring (current)

- **model_role:** `local`
- **Implementation:** `_call_local()` in `cbo_hub/cbo_core/app.py` → Ollama `POST {LOCAL_LLM_BASE_URL}/api/generate` (same shape as benchmark harness).
- **Config (env):** `LOCAL_LLM_BASE_URL` (default `http://127.0.0.1:11434`), `LOCAL_LLM_MODEL_ID` (required; no fallback).
- **Receipt:** `local_receipt` with `provider: "local"`, `base_url`, `model_id`, `http_status`, `error_snippet`, `called`. Invocation tracked even when cost=0.
- **Tool loop:** Local is eligible (repo_list, repo_search, same caps). STATE.md injected into prompt when role is local.
- **Smoke test:** Set `LOCAL_LLM_MODEL_ID` (e.g. `llama3.2`), start Ollama, then `POST /chat` with `model_role=local`, `user_text="Say hello."` → expect 200 and reply from local model; receipt has `local_receipt.http_status: 200`.
- **Verified:** Local run with **tinyllama** via Ollama; `Post-CalyxChat @{ user_text = "Say hello."; model_role = "local"; allow_tools = $false }` returned 200 and full model output (fourth voice online).

**60-second confirmation (CGPT checklist):** (1) repo_search under cbo_hub/cbo_core/ finds `_call_local`. (2) app.py model_role switch has architect→anthropic, workhorse→openai, second_opinion→kimi, **local**→_call_local. (3) Black-box: `/chat` with model_role=local returns local model output (or readable env error), not “unknown role” — wired.

---

## 1. Repo search results (Dev Harness POST /repo/search) [pre-wiring snapshot]

| Query | Where it appears |
|-------|-------------------|
| **ollama** | `benchmarks/harness/llm_backends/local_runtime.py`, `benchmarks/harness/llm_adapter.py`, `benchmarks/llm_config.example.json`, `Scripts/setup_openclaw_calyx.ps1`, patches, tests. **Not in cbo_hub.** |
| **local_runtime** | `benchmarks/harness/llm_backends/local_runtime.py`, `benchmarks/harness/llm_adapter.py`, BENCHMARK_VALIDATION_REPORT, HISTORY, patches. **Not in cbo_hub.** |
| **_call_local / telemetry_llm** | No matches in repo. |
| **localhost:11434** | In benchmarks (local_runtime, patches) and Scripts; not in cbo_hub. |

---

## 2. CBO Core routing (cbo_hub/cbo_core/app.py)

**Model call functions present:**

* `_call_anthropic` → architect  
* `_call_openai` → workhorse  
* `_call_kimi` → second_opinion  

**Now present:** `_call_local` (Ollama /api/generate). Env: `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL_ID`.

**model_role values:** `none | architect | workhorse | second | second_opinion | local`.

---

## 3. Direct test: POST /chat with model_role=local

**Payload:** `{"user_text": "Say hello.", "model_role": "local", "allow_tools": false}`

**Before wiring:** Reply contained `[cbo] Unknown model_role 'local'`.

**After wiring:** With `LOCAL_LLM_MODEL_ID` set and Ollama running, reply contains local model output; receipt has `local_receipt` with `called: true`, `http_status: 200`. Without env or Ollama down: readable error in reply and `local_receipt.error_snippet`.

---

## 4. Two-layer distinction (CGPT summary)

| Layer | Status |
|-------|--------|
| **Telemetry collection** (CPU, battery, receipts, logs, artifacts) | Assumed **local** / deterministic; not part of this check. |
| **Telemetry reasoning** (LLM summarization, anomaly detection, synthesis) | CBO Core: **remote** (Anthropic, OpenAI, Kimi) **or local** (Ollama via `model_role=local`). |

Benchmark harness (`benchmarks/harness/`, `local_runtime.py`) remains a separate subsystem for benchmark runs; CBO Core uses the same Ollama API shape (`/api/generate`) for the `local` role so the local system keeps the hub running when network is constrained.

---

**Reference:** CGPT directive verification; Phase 6 summary; STATE.md.
