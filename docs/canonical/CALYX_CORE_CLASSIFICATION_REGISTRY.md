# Calyx Core Classification Registry

Status: reduction registry
Work order: `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Generated: 2026-04-23

This registry classifies major Station Calyx systems against current evidence. `core` means proposed canonical core for the reduced system, not merely code presence. `canonical support` means implemented, integrated, exercised, and operator-relevant, but not the primary runtime/control authority.

## Classification Table

| name | path(s) | claimed purpose | observed purpose | implemented | integrated | exercised | classification | reasoning | recommended action |
|---|---|---|---|---|---|---|---|---|---|
| Sunrise startup path | `Scripts/sunrise_calyx.ps1`, `Scripts/start_calyx_core_services.ps1` | Start Station Calyx core services and loops | Current canonical startup wrapper and service launcher | yes | yes | yes | `core` | Starts the real core service set and emits sunrise/runtime evidence. | preserve |
| Sunset shutdown path | `Scripts/sunset_calyx.ps1` | Stop Station Calyx services | Current shutdown path referenced by doctrine | yes | yes | likely | `core` | Required counterpart to sunrise; no superior current shutdown path found. | preserve |
| Patch/sunrise wrappers | `Scripts/station_patch_sunrise.ps1`, `Scripts/calyx_sunset_sunrise.ps1` | Governed patch and restart wrappers | Convenience wrappers around sunrise/sunset | yes | partial | unknown | `quarantined` | Useful but not the single canonical control plane. | quarantine |
| Core HTTP services | `cbo_hub/dev_harness/app.py`, `cbo_hub/cbo_core/app.py`, `cbo_hub/avatar_web/app.py` | Local service substrate | Live local service family under sunrise | yes | yes | yes | `core` | Current heartbeat and topology show these as live service identities. Telemetry Gateway is separated below as canonical support, not core. | preserve |
| CBO Core governed chat | `cbo_hub/cbo_core/app.py` `/chat` | Governed operator interaction | Current chat/control path for Discord and browser surfaces | yes | yes | yes | `core` | Receipts show active governed chat usage and routing proofs. | preserve |
| Discord Gateway | `calyx/cbo/discord_gateway.py` | Governed Discord relay | Active canonical Discord transport | yes | yes | yes | `core` | Started by current sunrise path and visible in topology. | preserve |
| Legacy Discord intake | `calyx/cbo/discord_intake.py`, `Scripts/start_station_calyx.ps1` | Mail-spine Discord intake | Historical alternate Discord path | yes | no | historical | `quarantined` | Mutually exclusive with Discord Gateway and not current normal operation. | quarantine |
| External emitter gate | `calyx/kernel/external_emitter_gate.py`, `Scripts/start_calyx_core_services.ps1` | Prevent noncanonical external senders | Sunrise preflight guard | yes | yes | yes | `core` | Enforces reduced authority posture against OpenClaw-like emitters. | preserve |
| Station health loop | `Scripts/station_health_loop.ps1`, `runtime/station_health.json` | CPU/RAM/GPU and health truth | Fresh local health state | yes | yes | yes | `core` | Current artifact is fresh and operator-relevant. | preserve |
| Heartbeat surface | `runtime/station_heartbeat.json`, sunrise health checks | Runtime heartbeat summary | TTL-scoped status snapshot | yes | yes | yes | `completion-required` | Useful but can become stale and overlaps health/topology authority. | simplify |
| Service failure watch | `Scripts/service_failure_contract.ps1`, `runtime/service_failure_status.json`, `runtime/service_failure_detector_state.json` | Detect service failure | Active failure-watch surface | yes | yes | yes | `completion-required` | Current topology reports duplicate/ambiguous service failure watch instances. | simplify |
| Runtime topology observer | `Scripts/runtime_topology_snapshot.py`, `calyx/governance/runtime_topology.py`, `runtime/runtime_topology_snapshot.json` | Observe runtime identity/multiplicity | Active read-only topology observer | yes | yes | yes | `core` | Emits current evidence, but is not liveness authority. | preserve |
| Runtime reconciliation | `calyx/governance/reconciliation.py`, `runtime/receipts/audit/runtime_reconciliation__*.json` | Collapse duplicate runtime families | One-off reconciliation artifact | yes | partial | historical | `completion-required` | It is needed only if singleton doctrine remains core; current duplicates show enforcement is incomplete. | complete |
| Navigator/Triage loop | `Scripts/navigator_triage_loop.ps1`, `outgoing/navigator.lock`, `outgoing/triage.lock` | Cadence and triage signals | Active background loop | yes | yes | yes | `completion-required` | Fresh locks exist, but current topology reports duplicate/ambiguous instances. | simplify |
| CP6/CP7 loop | `Scripts/cp6_cp7_loop.ps1`, `tools/cp6_sociologist.py`, `tools/cp7_chronicler.py`, `outgoing/cp6.lock`, `outgoing/cp7.lock` | Harmony and drift signals | Active background loop | yes | yes | yes | `completion-required` | Real and exercised, but not clearly essential to minimal core and currently duplicated. | simplify |
| Energy churn/CP9 loop | `Scripts/energy_churn_cp9_loop.ps1`, `tools/cp9_auto_tuner.py`, `outgoing/cp9.lock` | Energy trend and tuning | Active background loop | yes | yes | yes | `completion-required` | Real and exercised, but operator value needs narrowing and duplicates exist. | simplify |
| Bridge Overseer | `calyx/cbo/bridge_overseer.py`, `metrics/bridge_pulse.csv` | Coordinate objectives/tasks | Running pulse loop with zero objectives/tasks | yes | yes | yes | `quarantined` | Active process, but current output shows no meaningful task control role. | quarantine |
| CLI Avatar | `cbo_hub/cli_avatar/main.py` | Local CLI avatar | Optional local client to CBO Core `/chat` | yes | yes | yes | `canonical support` | Implemented and launched by sunrise, but has no independent authority beyond forwarding to `/chat`. | preserve |
| Telemetry Gateway | `cbo_hub/telemetry_gateway/app.py` | Remote command ingress | Authenticated/audited remote-support ingress to CBO Core | yes | yes | yes | `canonical support` | Implemented, started by sunrise, and audit-exercised; not the normal operator path or core reasoning authority. | preserve |
| Mail/intent/work-envelope spine | `calyx/mail/*`, `calyx/cbo/intent_pipeline/*`, `calyx/execution/hub_runner.py`, `runtime/cbo/intents/` | Canonical intent-to-execution path | Historical/staged execution path | yes | partial | historical | `quarantined` | Last meaningful artifacts are old; current operator path uses `/chat`. | quarantine |
| Hub task handlers | `calyx/execution/task_handlers/*` | Execute approved work envelopes | Mostly stub handlers | partial | partial | historical | `removable` | Handlers report execution without doing substantive work. | remove |
| Swarm leases/trace/sandbox | `calyx/kernel/swarm_*`, `tests/test_swarm_*` | Multi-worker governed execution substrate | Schema/test/staging infrastructure | partial | no | tests only | `quarantined` | Receipts explicitly say execution and enforcement are disabled. | quarantine |
| Workspace planning surface | `cbo_hub/avatar_web/workspace_v0.py`, `runtime/workspace_v0/*` | Operator planning/whiteboard mediation | Real but dormant workspace tool | yes | partial | historical | `quarantined` | Heavily exercised on 2026-04-14, not current canonical path. | quarantine |
| Hot/warm memory scaffolding | `memory/hot/*`, `memory/warm/*`, `docs/MEMORY_ARCHITECTURE_v1.0.md` | Automated hot/warm continuity | Jan 2026 seed files and stale directories | partial | no | no | `removable` | One-time scaffold not maintained or integrated. | remove |
| Daily memory files | `memory/YYYY-MM-DD.md` | Daily continuity | Required by doctrine but missing for current day and yesterday | partial | manual | no | `completion-required` | If daily memory remains canonical, current operation violates its own startup rule. | complete |
| Curated memory | `MEMORY.md` | Main-session continuity | Real human-readable operator reference and partial continuity surface | yes | yes | yes | `canonical support` | Required by session doctrine and currently present, but authority resolution says it is not runtime continuity authority and not sole continuity authority. | preserve |
| `STATE.md` operational state | `STATE.md`, `Scripts/update_state_checks.ps1` | Current station state | Generated operational digest over health, service checks, and topology | yes | yes | yes | `canonical support` | Useful and exercised, but advisory; live probes, fresh runtime JSON, and receipts are stronger authority. | preserve |
| Legacy outgoing control plane | `outgoing/cbo.lock`, `outgoing/scheduler.lock`, `outgoing/svf.lock`, missing `outgoing/bridge.lock` | Agent/control-plane authority | Stale or absent lock files | partial | no | stale | `removable` | Stale artifacts should not imply current authority. | remove |
| CP8/CP10 and broad CP ecology | `docs/AGENT_REPOSITORY.md`, `COMPENDIUM.md`, missing `tools/cp8_quartermaster.py`, missing `tools/cp10_whisperer.py` | Agent ecology | Documented but not present | no | no | no | `removable` | Missing entrypoints and no runtime evidence. | remove |
| OpenClaw surfaces | `openclaw/`, `Scripts/setup_openclaw_calyx.ps1`, `skills/calyx-cbo-bridge/`, `docs/OPENCLAW_CALYX_INTEGRATION.md` | External assistant/gateway integration | Historical/prohibited capability surface | partial | no | prohibited | `quarantined` | Capability-bearing and noncanonical; must not be mistaken for current station authority. | quarantine |
| MCP/cloud workflow surfaces | `docs/CLOUD_SYNC_WORKFLOW.md`, `docs/skills_integration.md`, missing `tools/skills_cli.py`, missing `config/skills.yaml` | MCP/skill workflows | Documented fragments, no active local MCP server evidence | partial | no | no | `quarantined` | Future-value only; not current runtime. | quarantine |
| Container/deploy surface | `cbo_hub/compose.yaml` | Containerized service topology | Placeholder service only | partial | no | no | `removable` | Not a reproducible station deploy path. | remove |
| Kalshi/weather/market research layers | `docs/planning/WO_KALSHI_*`, `docs/planning/WO_WEATHER_*`, related tests | Market/research capabilities | Planning and tests outside core | partial | no | no | `quarantined` | Explicitly outside reduction scope. | quarantine |

## Proposed Core

Preserve as the reduced canonical core:

- `Scripts/sunrise_calyx.ps1`
- `Scripts/start_calyx_core_services.ps1`
- `Scripts/sunset_calyx.ps1`
- `cbo_hub/dev_harness/app.py`
- `cbo_hub/cbo_core/app.py`
- `cbo_hub/avatar_web/app.py`
- `calyx/cbo/discord_gateway.py`
- `calyx/kernel/external_emitter_gate.py`
- `Scripts/station_health_loop.ps1`
- `Scripts/runtime_topology_snapshot.py`
- `runtime/station_health.json`
- `runtime/service_failure_status.json`
- `runtime/runtime_topology_snapshot.json`

## Canonical Support

Preserve as support surfaces, not core authority:

- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/cli_avatar/main.py`
- `STATE.md`
- `MEMORY.md`

## Completion Required

These are already close enough to active core that incompleteness harms coherence:

- Runtime reconciliation, if singleton doctrine remains binding.
- Heartbeat/failure-watch authority boundaries.
- Navigator/Triage, CP6/CP7, and CP9 loop multiplicity and operator value.
- Daily memory continuity if daily memory remains canonical.

## Quarantine Required

Exclude from current canonical claims:

- OpenClaw and OpenClaw bridge surfaces.
- Legacy `discord_intake` as a normal operator path.
- Mail/intent/work-envelope execution spine until revalidated or retired.
- Swarm/sandbox worker runtime.
- Workspace planning surface.
- MCP/skills/cloud sync workflow surfaces.
- Kalshi/weather/market research layers.
- Bridge Overseer until it has current operator value.

## Removable From Current Claims

Remove from active docs or demote to historical:

- Missing CP8/CP10/Agent1/traffic navigator entrypoints.
- Legacy stale `outgoing` control-plane locks.
- Placeholder container/deploy claims.
- Stub hub task-handler execution claims.
- Hot/warm memory scaffold claims.

## Resolved By Authority Resolution

`WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1` resolved the prior unknowns:

- `CLI Avatar`: `canonical support`, optional `/chat` client only.
- `Telemetry Gateway`: `canonical support`, remote-support ingress only.
- `STATE.md`: `canonical support`, advisory generated operational digest.
- Bridge Overseer: `quarantined noncanonical`.
- Workspace planning: `quarantined noncanonical`.
- `MEMORY.md`: `canonical support`, curated operator reference and partial continuity component, not runtime continuity authority.
