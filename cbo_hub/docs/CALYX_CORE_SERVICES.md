# Calyx Core/Support services list

Canonical service map for CBO Hub stability and metrics. This document distinguishes canonical core from canonical support. Use it for startup order, health checks, and STATE.md `checks`, but do not treat every listed service as core authority.

Authority clarification, 2026-04-23:
- Canonical core CBO Hub services: Dev Harness, CBO Core, Avatar Web.
- Canonical support CBO Hub services: Telemetry Gateway, CLI Avatar.
- `STATE.md` is a generated operational digest, not sole authoritative runtime truth.

**Repo root:** `C:\Calyx_Terminal`
**Python:** `.venv_cbohub311` (3.11) — use venv for all uvicorn runs.

---

## Services (start order)

| Service            | Port | Module                           | Health check              | Startup command |
|--------------------|------|----------------------------------|---------------------------|-----------------|
| Dev Harness        | 7777 | `cbo_hub.dev_harness.app:app`    | TCP 127.0.0.1:7777        | `uvicorn cbo_hub.dev_harness.app:app --host 127.0.0.1 --port 7777` |
| CBO Core (CBO)     | 7778 | `cbo_hub.cbo_core.app:app`       | TCP 127.0.0.1:7778        | `uvicorn cbo_hub.cbo_core.app:app --host 127.0.0.1 --port 7778` |
| Avatar Web         | 7780 | `cbo_hub.avatar_web.app:app`     | TCP 127.0.0.1:7780        | `uvicorn cbo_hub.avatar_web.app:app --host 127.0.0.1 --port 7780` (Chat + Whiteboard) |
| Telemetry Gateway  | 7781 | `cbo_hub.telemetry_gateway.app:app` | TCP 0.0.0.0:7781      | `uvicorn cbo_hub.telemetry_gateway.app:app --host 0.0.0.0 --port 7781` |

- **Dev Harness** must be up before CBO Core (CBO calls it for repo_list / repo_search).
- **CBO Core (CBO):** CBO Core is the governed `/chat` service. It is not the quarantined Bridge Overseer control plane. CBO Core must be up before Avatar Web, CLI Avatar, and Telemetry Gateway because they proxy/call `/chat`.
- **Avatar Web** and **CLI Avatar** are clients only; no other service depends on them. **Avatar Web is localhost-only** (127.0.0.1); do not expose it publicly until stack policy allows (see `docs/STATION_STACK_POLICY.md`).
- **Telemetry Gateway** is canonical support and the remote connection point: auth (TELEMETRY_SECRET), identity isolation (X-Telemetry-Client-ID), audit log in `cbo_hub/logs/telemetry_gateway_audit.jsonl`. Bind 0.0.0.0 for tunnel (e.g. ngrok). It is not the normal operator path and not core reasoning authority.

Health is currently **TCP connect** to the port. Future: add GET `/health` or `/ready` per service for finer metrics and STATE.md `checks`.

---

## STATE.md alignment

- **checks:** `dev_harness=?`, `cbo_core=?`, `avatar_web=?`, `telemetry_gateway=?` — `cli` denotes “avatar usable” (CLI or web); can be derived from CBO Core being up.
- **Services section** in STATE.md should match this list; update when adding or changing a service.
- **Authority boundary:** `STATE.md` summarizes service checks. Fresh runtime JSON, receipts, topology, and live probes remain stronger evidence for runtime truth.
- **Metrics:** Receipts (`cbo_hub/receipts/cbo_core.jsonl`) provide per-request metrics; aggregate stability (e.g. uptime, last health success) can be written by a small probe script that runs periodically and updates STATE.md or a `runtime/` metrics file (when allowed).

---

## Scripts

- **Start all four (with venv):** `Scripts\start_calyx_core_services.ps1` — optional `-StopFirst` to free ports before start.
- **Start only gateway:** `Scripts\start_telemetry_gateway.ps1` — optional `-StopFirst`.
- **Probe health:** `Scripts\check_calyx_core_services.ps1` — TCP probe with 3s timeout per port; outputs `dev_harness=ok,...` or `=fail`; exit code 0 only when all ok.
- **Update STATE.md from probe:** `Scripts\update_state_checks.ps1` — runs the probe, then writes `checks:` and `heartbeat_ts:` into STATE.md. Wired into HEARTBEAT.md so each heartbeat refreshes state.
- **Station health loop (CPU/RAM):** `Scripts\station_health_loop.ps1` — 1s loop, writes `runtime/station_health.json`. Started by sunrise; stop via `runtime/station_health.stop`. See HEARTBEAT.md, docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md.
- **Runbook:** `patches_out/PHASE6_RUNTIME_RUNBOOK.md`, `cbo_hub/docs/USAGE_AND_HEALTH.md`.

---

*Canonical support document for Calyx CBO Hub service definitions. Update this file when adding or changing a service, and preserve the core/support distinction.*
