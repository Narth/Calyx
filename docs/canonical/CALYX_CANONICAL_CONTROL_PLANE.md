# Calyx Canonical Control Plane

Status: proposed canonical control plane for reduction
Work order: `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
Generated: 2026-04-23

## Decision

The proposed single canonical control plane is:

- Startup: `Scripts/sunrise_calyx.ps1` -> `Scripts/start_calyx_core_services.ps1`
- Shutdown: `Scripts/sunset_calyx.ps1`
- Runtime truth: `runtime/station_health.json`, `runtime/service_failure_status.json`, `runtime/service_failure_detector_state.json`, `runtime/runtime_topology_snapshot.json`, and governance/security/audit receipts under `runtime/receipts/`
- Operator trust: current health, failure watch, topology observation, and explicit receipts

## Evidence

- Sunrise starts the core HTTP services, health loop, service failure watch, navigator/triage loop, energy churn/CP9 loop, CP6/CP7 loop, Bridge Overseer, CLI Avatar, and Discord Gateway.
- Current `runtime/station_health.json` was fresh and reported `health: pass`.
- Current `runtime/runtime_topology_snapshot.json` reported stale topology and duplicate/ambiguous loop families, proving topology observation is real while also proving control-plane enforcement is incomplete.

## Canonical Control Surfaces

Preserve:

- `Scripts/sunrise_calyx.ps1`
- `Scripts/start_calyx_core_services.ps1`
- `Scripts/sunset_calyx.ps1`
- `runtime/station_health.json`
- `runtime/service_failure_status.json`
- `runtime/service_failure_detector_state.json`
- `runtime/runtime_topology_snapshot.json`
- `runtime/receipts/security/*`
- `runtime/receipts/audit/runtime_topology_snapshot__*.json`

## Advisory Or Quarantined Control Surfaces

Quarantine or demote:

- `outgoing/cbo.lock`
- `outgoing/scheduler.lock`
- `outgoing/svf.lock`
- missing `outgoing/bridge.lock`
- missing `outgoing/watcher.lock`
- `metrics/bridge_pulse.csv` as authority surface
- `Scripts/start_station_calyx.ps1`
- OpenClaw launch/setup scripts
- manual service start instructions that bypass sunrise

## Completion Required

Runtime topology and reconciliation must be aligned if singleton/multiplicity doctrine remains canonical. Current evidence shows topology can detect duplicate/ambiguous services, but duplicate families still exist after prior reconciliation.

## Recommendation

Keep sunrise/sunset as the only canonical control-plane ceremony. Treat all other launchers and historical locks as noncanonical until follow-on demotion work updates docs and operator references.

## Authority Resolution Addendum

`WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1` clarifies:

- CLI Avatar is `canonical support`, not control-plane authority.
- Telemetry Gateway is `canonical support`, not the normal operator path.
- `STATE.md` is `canonical support`, an advisory generated operational digest.
- Bridge Overseer is `quarantined noncanonical` and should not be included in current control-plane authority claims.
- Workspace planning is `quarantined noncanonical`.
