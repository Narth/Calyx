# Calyx Canonical System Map

Status: canonical map
Date: 2026-04-23
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Authority source: `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md`

This map is the operator-facing authority boundary for the reduced Station Calyx system. A surface is not canonical merely because it exists in code, docs, launch scripts, receipts, or memory.

## Canonical Core

Canonical core means implemented, integrated, exercised, observable, operator-relevant, and part of the current normal runtime/control path.

| system | path(s) | role | evidence | notes |
|---|---|---|---|---|
| Sunrise startup path | `Scripts/sunrise_calyx.ps1`, `Scripts/start_calyx_core_services.ps1` | Normal startup/control path | Classification registry and current sunrise doctrine | Preserved as current startup authority. |
| Sunset shutdown path | `Scripts/sunset_calyx.ps1` | Normal shutdown/control path | Classification registry and station doctrine | Preserved as shutdown counterpart. |
| CBO Core governed chat | `cbo_hub/cbo_core/app.py` | Governed `/chat` mediation | Classification registry and receipt evidence | Primary governed interaction path. |
| Dev Harness | `cbo_hub/dev_harness/app.py` | Local repository support for CBO Core | Core service map | Core because CBO Core depends on it. |
| Avatar Web | `cbo_hub/avatar_web/app.py` | Local browser client to governed chat | Core service map | Core local operator surface, localhost-bound. |
| Discord Gateway | `calyx/cbo/discord_gateway.py` | Governed Discord transport | Classification registry and topology evidence | Current Discord path; distinct from legacy intake. |
| External emitter gate | `calyx/kernel/external_emitter_gate.py` | External-send authority guard | Sunrise preflight evidence | Core governance boundary. |
| Station health loop | `Scripts/station_health_loop.ps1`, `runtime/station_health.json` | Runtime health truth producer | Runtime health artifact and sunrise integration | Core health evidence. |
| Runtime topology observer | `Scripts/runtime_topology_snapshot.py`, `calyx/governance/runtime_topology.py`, `runtime/runtime_topology_snapshot.json` | Runtime identity/topology observation | Runtime topology artifact and receipts | Observes runtime truth; not sole liveness authority. |
| Service failure watch | `Scripts/service_failure_contract.ps1`, `runtime/service_failure_status.json` | Failure-watch surface | Classification registry | Core-adjacent but simplification remains required. |

## Canonical Support

Canonical support means implemented, integrated, exercised, observable, and useful, but not the primary authority surface.

| system | path(s) | role | authority boundary |
|---|---|---|---|
| CLI Avatar | `cbo_hub/cli_avatar/main.py` | Optional local client to CBO Core `/chat` | No independent operator/control authority. |
| Telemetry Gateway | `cbo_hub/telemetry_gateway/app.py` | Authenticated/audited remote-support ingress | Not the normal operator path and not core reasoning authority. |
| Local MCP server | `calyx/mcp_server/server.py`, `Scripts/start_calyx_mcp_stdio.ps1`, `docs/canonical/CALYX_LOCAL_MCP_SERVER.md` | Read-only local stdio MCP support for approved workstation folders, including `D:\Calyx_Data` | Canonical support only; not runtime continuity authority, not a control plane, and not retroactive context ingestion authority. |
| Decision ledger and source registry | `docs/canonical/CALYX_DECISION_LEDGER.md`, `docs/canonical/CALYX_SOURCE_AUTHORITY_REGISTRY.json`, `runtime/active_objective.json` | Operator decision, source authority, and current-objective clarity substrate | Canonical support only; resolves ambiguity but does not expand runtime authority. |
| `STATE.md` | `STATE.md`, `Scripts/update_state_checks.ps1` | Generated operational digest | Advisory support; not sole authoritative truth. |
| `MEMORY.md` | `MEMORY.md` | Curated operator reference and partial continuity component | Not runtime continuity authority and not sole continuity authority. |

## Completion-Required Core-Adjacent Surfaces

| system | path(s) | gap | recommended action |
|---|---|---|---|
| Heartbeat surface | `runtime/station_heartbeat.json` | Overlaps health/topology and can become stale | simplify |
| Runtime reconciliation | `calyx/governance/reconciliation.py`, `runtime/receipts/audit/runtime_reconciliation__*.json` | Incomplete enforcement for singleton doctrine | complete only if singleton doctrine remains binding |
| Navigator/Triage loop | `Scripts/navigator_triage_loop.ps1`, `outgoing/navigator.lock`, `outgoing/triage.lock` | Real but authority/operator value boundary is overgrown | simplify |
| CP6/CP7 loop | `Scripts/cp6_cp7_loop.ps1`, `tools/cp6_sociologist.py`, `tools/cp7_chronicler.py` | Real but not clearly minimal core | simplify |
| Energy Churn/CP9 loop | `Scripts/energy_churn_cp9_loop.ps1`, `tools/cp9_auto_tuner.py` | Real but tuning authority needs narrowing | simplify |
| Daily memory files | `memory/YYYY-MM-DD.md` | Doctrine requires them, but current exercise is inconsistent | complete or demote doctrine |

## Quarantined Noncanonical

| system | path(s) | reason |
|---|---|---|
| Bridge Overseer | `calyx/cbo/bridge_overseer.py`, `calyx/cbo/README.md`, `metrics/bridge_pulse.csv` | Existing runtime/history does not support canonical orchestration authority. |
| Workspace planning surface | `cbo_hub/avatar_web/workspace_v0.py`, `runtime/workspace_v0/*` | Dormant/historical planning surface, not normal operator path. |
| Legacy Discord intake | `calyx/cbo/discord_intake.py`, `Scripts/start_station_calyx.ps1` | Historical alternate path; current path is Discord Gateway. |
| Mail/intent/work-envelope spine | `calyx/mail/*`, `calyx/cbo/intent_pipeline/*`, `calyx/execution/hub_runner.py` | Historical/staged execution path, not current `/chat` operator flow. |
| Swarm leases/trace/sandbox | `calyx/kernel/swarm_*`, `tests/test_swarm_*` | Staging/test infrastructure with disabled execution/enforcement. |
| OpenClaw surfaces | `openclaw/`, `Scripts/setup_openclaw_calyx.ps1`, `skills/calyx-cbo-bridge/`, `docs/OPENCLAW_CALYX_INTEGRATION.md` | Capability-bearing noncanonical external integration surface. |
| MCP/cloud workflow surfaces | `docs/CLOUD_SYNC_WORKFLOW.md`, `docs/skills_integration.md`, missing `tools/skills_cli.py`, missing `config/skills.yaml` | Future-value fragments distinct from the approved local read-only MCP server. |
| Kalshi/weather/market layers | `docs/planning/WO_KALSHI_*`, `docs/planning/WO_WEATHER_*` | Outside reduced core. |

## Deprecated, Historical, Or Removable

| system | path(s) | status |
|---|---|---|
| Hub task handlers | `calyx/execution/task_handlers/*` | removable; mostly stub execution claims. |
| Hot/warm memory scaffold | `memory/hot/*`, `memory/warm/*`, `docs/MEMORY_ARCHITECTURE_v1.0.md` | removable from current claims. |
| Legacy outgoing control plane | `outgoing/cbo.lock`, `outgoing/scheduler.lock`, `outgoing/svf.lock`, missing `outgoing/bridge.lock` | removable from current authority claims. |
| CP8/CP10 agent claims | `docs/AGENT_REPOSITORY.md`, `COMPENDIUM.md`, missing `tools/cp8_quartermaster.py`, missing `tools/cp10_whisperer.py` | removable or historical until implemented and exercised. |
| Container/deploy placeholder | `cbo_hub/compose.yaml` | removable from reproducible deploy claims. |

## Unknown

| surface | reason |
|---|---|
| Exact current operator use frequency by surface | Requires operator/runtime observation outside documentation pass. |
| Whether CP loops should become core or remain support | They are active, but reduced operator value is not yet proven. |
| Whether daily memory doctrine should be completed or demoted | Current docs require daily memory, but current exercise evidence is inconsistent. |
