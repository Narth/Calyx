# Station Calyx — CBO Hub STATE (authoritative)
Status: maintenance

Last verified: 2026-02-24
Hub OS: Windows
Repo root: C:\Calyx_Terminal
Python venv: .venv_cbohub311 (Python 3.11)

## Status (BloomOS: read this first)
Status: maintenance
heartbeat_ts: 2026-02-24T02:03:25Z
override: on
lock:
checks: dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok
Assessment includes: CBO (cbo_core), Dev Harness, Avatar Web, Telemetry Gateway. CBO is the Calyx Bridge Overseer; all test and assessment metrics include CBO.
Rationale: Station assessment and CBO Stack review (2026-02-21).\n\n**Architect Directive:** Maintenance status is intentionally maintained to ensure workflow consistency during optimization phase. Core services (dev_harness, cbo_core, avatar_web, telemetry_gateway) are operational but intentionally restricted to "ok" state for structured improvement tracking.
Populate checks: run Scripts\update_state_checks.ps1 (calls check_calyx_core_services.ps1 and writes checks + heartbeat_ts here). Heartbeat runs this.

## Services (Calyx Core — canonical list: cbo_hub/docs/CALYX_CORE_SERVICES.md)
- Dev Harness: http://127.0.0.1:7777
- CBO Core: http://127.0.0.1:7778
- CLI Avatar: terminal (python -m cbo_hub.cli_avatar.main)
- Avatar Web: http://127.0.0.1:7780 (localhost only; no public browser API until stack hardened — docs/STATION_STACK_POLICY.md)
- Telemetry Gateway: http://0.0.0.0:7781 (remote connection; expose via ngrok)
Start all: Scripts\start_calyx_core_services.ps1 [-StopFirst]

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

### Calyx Sign sponsorship (in place — 2026-02-24)
- **Signed:** `cbo_sponsorship_research_test_improve.approval.json.sig` verified. Architect sponsors CBO to stamp operations within scope (research, test, improve Station Calyx). When a decision requires Architect input, CBO asks in the current channel and waits. See **docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md**.

### Forbidden (outside sponsored scope)
- Any file write (other than receipts and stamped operations within scope)
- Any docker write/exec automation
- Any network actions beyond configured model APIs and the local Dev Harness calls
- Any silent spend (must be receipt-backed)

## Receipts
- Receipts preserved: YES
- Receipt fields include executed_tools: YES
- second_opinion_receipt (provider, base_url, model_id, http_status, error_snippet) when model_role second_opinion
- local_receipt (provider, base_url, model_id, http_status, error_snippet) when model_role local

## Planning (whiteboard)
- Avatar Web sub-agents, task tracking, viewable avatars: **docs/planning/AVATAR_WEB_SUBAGENTS_WHITEBOARD.md** (hardware-gated; local first = visible crew).
- Rooms, decks, channel pockets (future): **docs/planning/WHITEBOARD_ROOMS_DECKS.md** — literal rooms/ship decks and channel-pocket containers so subagents/subtasks complete in their own spaces without overbearing architect load or system collapse.
- Build safety (hardware, safety, utility, efficiency): **Scripts\build_safety_check.ps1** + **docs/planning/BUILD_SAFETY_CHECK.md** — run before crucial builds to avoid overreach and crash loops.

## Runbook
- Phase 6 + Kimi + 3-call: **patches_out/PHASE6_RUNTIME_RUNBOOK.md**

---
BloomOS: use Status + heartbeat_ts + checks only; act on unhealthy or stale. Rest is context.