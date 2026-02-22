# Station Calyx — CBO Hub STATE (authoritative)
Status: maintenance

Last verified: 2026-02-21
Hub OS: Windows
Repo root: C:\Calyx_Terminal
Python venv: .venv_cbohub311 (Python 3.11)

## Status (BloomOS: read this first)
Status: maintenance
heartbeat_ts:
override: on
lock:
checks: dev_harness=?, cbo_core=?, cli=?
Rationale: Station assessment and CBO Stack review (2026-02-21).

## Services
- Dev Harness: http://127.0.0.1:7777 (running)
- CBO Core: http://127.0.0.1:7778 (running)
- CLI Avatar: operational

## Model Routing
- architect: Anthropic Sonnet (API wired)
- workhorse: OpenAI (API wired)
- second_opinion: Kimi (wired)
- local: Ollama (LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL_ID; receipt-backed, cost=0)

## Tooling (CBO-controlled)
### Allowed (Read-only)
- repo_list (via Dev Harness /repo/list) — max_entries <= 500
- repo_search (via Dev Harness /repo/search) — max_hits <= 200
- Tool loop: executes up to 3 tool_requests per response
- Execution conditions:
  - model_role in architect | workhorse | second_opinion | local
  - allow_tools == true
  - tool_requests JSON parses + passes allowlist

### Forbidden (until Calyx Sign)
- Any file write (other than receipts)
- Any docker write/exec automation
- Any network actions beyond configured model APIs and the local Dev Harness calls
- Any silent spend (must be receipt-backed)

## Receipts
- Receipts preserved: YES
- Receipt fields include executed_tools: YES
- second_opinion_receipt (provider, base_url, model_id, http_status, error_snippet) when model_role second_opinion
- local_receipt (provider, base_url, model_id, http_status, error_snippet) when model_role local

## Runbook
- Phase 6 + Kimi + 3-call: **patches_out/PHASE6_RUNTIME_RUNBOOK.md**

---
BloomOS: use Status + heartbeat_ts + checks only; act on unhealthy or stale. Rest is context.