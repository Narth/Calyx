---
status: active
owner: station
last_reviewed_utc: "2026-04-18"
doctrine_scope: governed
---

# STATION_INTERRUPTION_AND_RECOVERY_MODEL

## Purpose

This model defines how Station Calyx records clean shutdown, detects unclean interruption, identifies host boot, and reports post-boot recovery.

The goal is simple: no lifecycle transition should require later reconstruction from partial evidence when a receipt can be emitted at the time it happens.

## Lifecycle Artifacts

### 1. Clean shutdown

Latest artifact:

- `runtime/station_shutdown_marker.json`

Receipts:

- `runtime/receipts/audit/station_shutdown_marker__*.json`

Required fields:

- `shutdown_ts_utc`
- `reason`
- `active_services`
- `active_leases`
- `in_flight_operations`

### 2. Host boot detection

Latest artifact:

- `runtime/host_boot_detected.json`

Receipts:

- `runtime/receipts/audit/host_boot_detected__*.json`

Required fields:

- `os_boot_ts_utc`
- `last_station_artifact_ts_utc`
- `delta_from_last_station_artifact_sec`
- `classification`

Classification values:

- `normal_restart`
- `post_interruption_restart`

### 3. Unclean interruption assessment

Latest artifact:

- `runtime/station_unclean_interruption.json`

Receipts:

- `runtime/receipts/audit/station_unclean_interruption__*.json`

Required fields:

- `interruption_detected`
- `inferred_interruption_window`
- `affected_surfaces`
- `missing_clean_shutdown_marker`
- `stale_truth_surfaces_at_boot`

### 4. Recovery status

Latest artifact:

- `runtime/station_recovery_status.json`

Receipts:

- `runtime/receipts/audit/station_recovery_status__*.json`

Required fields:

- `restored_services`
- `missing_or_failed_services`
- `port_bindings`
- `truth_surfaces`
- `topology_snapshot_available`
- `recovery_classification`

## Script Integration

### `Scripts/sunset_calyx.ps1`

Before termination begins, sunset emits a shutdown marker with:

- active service set
- active non-terminal worker leases
- detectable in-flight swarm runs
- declared shutdown reason

Reason values currently supported:

- `manual`
- `patch`
- `restart`

### `Scripts/sunrise_calyx.ps1`

Before service start:

- emit `host_boot_detected`
- emit `station_unclean_interruption`

After startup attempt returns:

- emit `station_recovery_status`

### `Scripts/update_state_checks.ps1`

Update-state now consumes the latest host-boot artifact when present and carries:

- `host_boot_ts`
- `host_boot_classification`

into `runtime/station_heartbeat.json` and `runtime/service_runtime_snapshot.json`.

## Evidence Rules

- Shutdown marker is the canonical clean-stop signal.
- Missing shutdown marker after later host boot is treated as interruption evidence.
- Host boot detection is OS-derived, not inferred solely from Station artifacts.
- Recovery status is observational only. It does not heal, restart, or enforce.

## Boundaries

This model does not:

- auto-restart services
- auto-heal failed loops
- enforce containment
- alter worker execution

It records lifecycle truth. It does not control it.

## Forward Compatibility

These artifacts are compatible with later:

- lease / swarm receipt bundles
- non-execution trace graph lifecycle nodes
- richer incident reconstruction and recovery dashboards
