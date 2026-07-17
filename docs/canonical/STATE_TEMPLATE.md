---
status: active
owner: station
last_reviewed_utc: "2026-04-30"
doctrine_scope: governed
---

# STATE.md Template

## Purpose

`STATE.md` is the live Station digest. It is generated support evidence for current operator orientation, heartbeat display, and quick audit inspection. It is not sole runtime authority.

This template defines the tracked baseline shape. The live root `STATE.md` may change frequently and should be treated as a generated runtime digest.

## Authority Boundary

- `STATE.md` summarizes live probes, runtime JSON, topology, signal digest, clarity status, and service checks.
- Fresh runtime JSON, receipts, topology snapshots, and live probes remain stronger runtime evidence.
- A frozen copy of `STATE.md` may be archived into `docs/operations/` only by explicit operator intent.
- `STATE.md` must not contain secrets, raw tokens, private Discord IDs, or machine credentials.

## Required Fields

```text
heartbeat_ts: <ISO-8601 UTC timestamp>
health: <pass|warn|fail|unknown>
health_ts: <ISO-8601 UTC timestamp or empty>
entropy_tier: <pass|high|unacceptable|unknown>
navigator_interval: <hot|cool|pause|unknown>
triage_status: <pass|warn|fail|unknown>
cpu_target: <safe_travels|under|over|unknown>
runtime_truth_state: <fresh|stale|unknown>
runtime_truth_expires_ts: <ISO-8601 UTC timestamp>
runtime_truth_label: <DERIVED_FRESH|STALE_STATE|...>
runtime_truth_canonical: advisory digest from live_probes[ (<reason>)]
state_authority_status: canonical support
state_authority_note: STATE.md is advisory generated support; not sole authoritative truth
active_objective_status: <active|paused|missing|unknown>
active_objective_summary: <bounded operator-readable summary>
confusion_policy: <classification policy summary>
source_authority_registry: <valid(...)|invalid(...)|missing>
checks: dev_harness=<ok|fail>,cbo_core=<ok|fail>,avatar_web=<ok|fail>,telemetry_gateway=<ok|fail>
failure_flags_active: <integer>
failure_change_lane: <clear|service_failure_active|unknown>
failure_risk_lane: <clear|single_service_restart_candidate|full_sunrise_candidate|unknown>
failure_flag_services: <comma-separated service list or empty>
runtime_topology_ts: <ISO-8601 UTC timestamp>
runtime_topology_truth_state: <fresh|stale|unknown>
runtime_topology_risk: <LOW|ELEVATED|CRITICAL|unknown>
runtime_topology_active_services: <comma-separated service(count) list or none>
runtime_topology_authority_summary: <authority(count) list or none>
runtime_topology_duplicates: <comma-separated duplicate services or none>
runtime_topology_authority_ambiguous: <comma-separated ambiguous services or none>
runtime_topology_flagged_services: <comma-separated flagged services or none>
signal_level: <none|advisory|warning|critical|unknown>
signal_top: <signal id or none>
signal_count: <integer>
signal_requires_operator_confirmation: <true|false>
signal_operator_brief: <bounded advisory summary>
```

## Audit Modes

### Real-Time Audit

Use the current root `STATE.md` with:

```powershell
.\Scripts\update_state_checks.ps1
```

Then inspect:

- `STATE.md`
- `runtime/station_heartbeat.json`
- `runtime/runtime_topology_snapshot.json`
- `runtime/signals/current_signal_digest.json`
- `runtime/service_runtime_snapshot.json`

### Frozen-Time Audit

Copy the current digest and supporting artifacts into an explicitly named evidence bundle under `docs/operations/` or another operator-approved archive location. The bundle must include the timestamp, reason, and source artifact paths.

## Baseline Rule

Track this template. Treat root `STATE.md` as live generated state unless the operator explicitly freezes a snapshot for audit evidence.
