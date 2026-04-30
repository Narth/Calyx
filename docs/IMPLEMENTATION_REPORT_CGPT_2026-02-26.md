# Station Calyx Implementation Report — CGPT Review

**Date:** 2026-02-26
**Prepared by:** CBO (Calyx Bridge Overseer)
**Audience:** CGPT
**Status:** Post-sunrise validation complete

---

## 1. Executive Summary

Station Calyx is operational. All four Calyx Core services are running and validated. This report summarizes the current implementation state, recent deliverables (notably the Station Event Ledger), and readiness for external review.

---

## 2. Sunrise Status (2026-02-26 00:05 UTC)

| Service            | Port | Status | Endpoint                    |
|--------------------|------|--------|-----------------------------|
| Dev Harness        | 7777 | ok     | http://127.0.0.1:7777       |
| CBO Core (CBO)     | 7778 | ok     | http://127.0.0.1:7778       |
| Avatar Web         | 7780 | ok     | http://127.0.0.1:7780       |
| Telemetry Gateway  | 7781 | ok     | http://0.0.0.0:7781         |

**Checks:** `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`
**Heartbeat:** 2026-02-26T00:05:26Z
**Health:** warn | **Entropy tier:** pass

---

## 3. Recent Implementation: Station Event Ledger (WO_STATION_EVENT_LEDGER_V1)

### 3.1 Purpose

The Station Event Ledger provides a **human-legible, append-only, correlation-aware event spine** for Station Calyx. Prior to this work, the Station behaved like a black box; the ledger makes decisions, failures, denials, and irreversible actions observable.

**Philosophy:** Station Calyx must fail visibly, act traceably, decide audibly, escalate explicitly, and deny deterministically.

### 3.2 Architecture

| Component | Location | Role |
|-----------|----------|------|
| **Event Ledger** | `calyx/kernel/event_ledger.py` | `emit()` API — atomic append, flush, never throws |
| **Ledger Path** | `runtime/ledger/station_events__YYYYMMDD.jsonl` | Per-day JSONL file |
| **View Tool** | `Scripts/ledger_tail.py` | Human-legible tail; `-n 50`, `--json` |
| **Health Check** | `calyx/kernel/ledger_health_check.py` | Validates writability, staleness; emits `ledger.stall` |

### 3.3 Schema (Strict + Minimal)

Each event includes: `ts`, `level`, `component`, `event`, `msg`, `corr_id` (uuid4 if missing), `run_id`, `data`, `artifact_refs`, `policy`, `decision`. No large nested payloads; data truncated for telemetry.

### 3.4 Integration Points

| Area | Events | Location |
|------|--------|----------|
| **Station boot** | `station.boot`, `station.boot.error` | CBO Core lifespan |
| **Heartbeat** | `heartbeat.tick` | `Scripts/update_state_checks.ps1` → `emit_heartbeat_tick.py` |
| **Discord** | `cbo.discord.inbound`, `cbo.discord.outbound` | `discord_intake.py`, `discord_response.py` |
| **Mail/Router** | `mail.ingest.accept`, `mail.ingest.reject`, `router.deliver.success`, `router.deliver.replay`, `router.deliver.atomic_write` | `calyx/mail/router.py` |
| **Tool execution** | `toolcall.requested`, `toolcall.allowed`, `toolcall.denied`, `toolcall.error` | `home_node_executor.py`, `toolsurface.py` |
| **Global exception** | `exception` (short stack in `data`) | CBO Core exception handler |

### 3.5 Governance Invariants

- Ledger failure cannot crash Station — fallback to stderr
- Non-blocking writes only
- Destructive ops: `destructive.preflight`, `destructive.commit`, `destructive.rollback` (caller-emitted)

### 3.6 Usage

```bash
# Human-legible (default)
python Scripts/ledger_tail.py -n 50

# Raw JSON
python Scripts/ledger_tail.py -n 50 --json
```

---

## 4. Station Calyx Stack Overview

### 4.1 Services

| Service | Module | Port | Role |
|---------|--------|------|------|
| Dev Harness | `cbo_hub.dev_harness.app` | 7777 | `repo_list`, `repo_search` for CBO |
| CBO Core | `cbo_hub.cbo_core.app` | 7778 | CBO (Calyx Bridge Overseer), `/chat`, `/execute`, `/state` |
| Avatar Web | `cbo_hub.avatar_web.app` | 7780 | Chat + Whiteboard UI |
| Telemetry Gateway | `cbo_hub.telemetry_gateway.app` | 7781 | Remote connection (ngrok tunnel) |

### 4.2 Model Routing

- **architect:** Anthropic Sonnet
- **workhorse:** OpenAI
- **second_opinion:** Kimi K2.5
- **local:** Ollama (receipt-backed, cost=0)

### 4.3 Tooling (CBO-controlled)

- **Allowed:** `repo_list`, `repo_search` via Dev Harness
- **Forbidden:** `eval`, `exec`, `subprocess`, `discord_send`, `send_email`, `http_request`
- **Sponsorship:** Calyx Sign `cbo_sponsorship_research_test_improve` — Architect sponsors CBO for research, test, improve Station Calyx

---

## 5. Key Scripts

| Script | Purpose |
|--------|---------|
| `Scripts/start_calyx_core_services.ps1 [-StopFirst]` | Sunrise all four services |
| `Scripts/check_calyx_core_services.ps1` | TCP probe; outputs `checks` line |
| `Scripts/update_state_checks.ps1` | Updates STATE.md (checks, heartbeat_ts, health) |
| `Scripts/ledger_tail.py [-n N] [--json]` | View Station Event Ledger |
| `Scripts/station_health_loop.ps1` | 1s health loop → `runtime/station_health.json` |
| `Scripts/patch_readiness.ps1` | Entropy-aware pre-check before patches |

---

## 6. Canonical References

- **Services:** `cbo_hub/docs/CALYX_CORE_SERVICES.md`
- **State:** `STATE.md` (authoritative)
- **Sponsorship:** `docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md`
- **Health audit:** `docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md`
- **Build safety:** `docs/planning/BUILD_SAFETY_CHECK.md`

---

## 7. Recommendations for CGPT Review

1. **Validate ledger output** — Run `python Scripts/ledger_tail.py -n 25` and confirm events are human-legible after CBO Core activity.
2. **Verify service health** — `GET http://127.0.0.1:7778/state` returns STATE.md content.
3. **Check sponsorship** — `GET http://127.0.0.1:7778/sponsorship` returns `valid: true` when signed.
4. **Station health loop** — If `runtime/station_health.stop` exists, remove it and start `station_health_loop.ps1` for full health telemetry.

---

## 8. Open Items

- **Station health loop** — Currently stopped (stop file present from prior restart). Restart if continuous health telemetry is desired.
- **Ledger follow mode** — `ledger_tail.py` is one-shot; no built-in `-f` follow. Use a loop or external `tail -f` on the JSONL file for live streaming.

---

*Report generated by CBO. Station Calyx is operational and ready for CGPT review.*
