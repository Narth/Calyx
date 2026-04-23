---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# WO_SANDBOXED_WORKER_RUNTIME_V1

## Section I - Purpose And Scope

### Purpose

Define the containment model for swarm workers operating under `worker_lease` authority.

This work order exists so worker execution can be:

- isolated
- bounded
- reversible
- attributable

without requiring shared mutable runtime by default.

### Scope

This work order governs:

- worker isolation mode
- bounded command execution posture
- snapshot and diff expectations
- rollback definition
- network containment
- orphan, stale-lock, and quarantine handling

This work order does not:

- mint leases
- redefine lease semantics
- define final trace bundle structure in full
- authorize process termination by itself

## Section II - Relationship To The Swarm Control Plane

This work order is subordinate to:

- `WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1`

All sandbox behavior must enforce lease constraints rather than inventing new authority.

Required inheritance:

- sandbox scope must not exceed `ownership_scope`
- allowed commands must not exceed `allowed_tool_classes`
- network posture must not exceed `network_scope`
- sandbox lifetime must not exceed lease lifetime

Shared lifecycle:

`proposal -> work_envelope -> worker_lease -> sandbox_prepare -> execute -> trace -> reconcile`

## Section III - Shared Definitions

### `sandbox_id`

The canonical identifier for one worker sandbox.

### `sandbox_manifest`

The declarative record describing one worker sandbox and its effective boundaries.

### `snapshot_record`

The pre-execution or post-execution record used to reconstruct state and support rollback.

### `quarantine_record`

The record describing partial, suspicious, or non-mergeable worker output.

### `orphan_worker`

A worker process or workspace surface that remains present without a valid active lease or expected heartbeat.

### `stale_lock`

A worker lock or sandbox claim that persists beyond declared lease timing or reconciliation timing.

## Section IV - Core Runtime And Snapshot Schemas

### A. `sandbox_manifest`

Canonical planning schema:

```text
sandbox_manifest = {
  schema,
  schema_version,
  swarm_run_id,
  work_envelope_id,
  lease_id,
  worker_id,
  sandbox_id,
  isolation_mode,
  sandbox_root,
  read_paths,
  write_paths,
  deny_paths,
  allowed_tool_classes,
  network_scope,
  pre_execution_snapshot_id,
  post_execution_diff_id,
  sandbox_state,
  notes
}
```

Allowed `isolation_mode` values in v1 planning:

- `git_worktree`
- `branch_overlay`
- `directory_overlay`
- `read_only_probe`

### B. `snapshot_record`

```text
snapshot_record = {
  schema,
  schema_version,
  snapshot_id,
  swarm_run_id,
  lease_id,
  worker_id,
  snapshot_stage,
  snapshot_method,
  captured_at_utc,
  scope_hash,
  artifact_paths,
  rollback_method,
  notes
}
```

Allowed `snapshot_stage` values:

- `pre_execution`
- `post_execution`

### C. `post_execution_diff`

```text
post_execution_diff = {
  diff_id,
  swarm_run_id,
  lease_id,
  worker_id,
  changed_paths,
  added_paths,
  deleted_paths,
  ownership_violations,
  generated_artifacts,
  diff_summary
}
```

## Section V - Required Behavior

The sandboxed runtime must enforce:

1. one sandbox per worker lease
2. no shared mutable state unless explicitly declared
3. command execution only within allowed tool classes
4. default deny network posture
5. pre-execution snapshot before write-enabled work
6. post-execution diff before reconciliation
7. quarantine for partial or suspicious outputs

No worker may:

- write outside the lease's `write_paths`
- read denied paths
- bypass sandbox preparation
- carry mutable outputs directly into another worker sandbox without declaration

## Section VI - Execution Lifecycle And State Transitions

Allowed sandbox states:

- `prepared`
- `active`
- `sealed`
- `quarantined`
- `released`

Allowed transitions:

```text
prepared -> active
active -> sealed
active -> quarantined
sealed -> released
quarantined -> released
```

Shared runtime lifecycle:

1. lease approved
2. sandbox prepared
3. pre-execution snapshot captured
4. worker activated
5. commands executed within lease limits
6. post-execution diff captured
7. sandbox sealed or quarantined
8. reconciliation decides release, rollback, or hold

## Section VII - Command, Network, And Failure Posture

### Command Execution Rules

Command execution must be:

- bounded
- attributable
- deny-by-default

Minimum command controls:

- explicit allowed tool classes
- explicit working root
- execution timeout
- captured exit status
- trace linkage to `lease_id`

### Network Posture

Default:

- `network_scope.mode = deny`

Allowlist mode requires:

- host or domain allowlist
- purpose statement
- protocol and port bounds if applicable
- inheritance from root `work_envelope`

### Failure Handling

Required failure classes:

- `ownership_violation`
- `sandbox_escape_attempt`
- `network_scope_violation`
- `orphan_worker_detected`
- `stale_lock_detected`
- `snapshot_missing`
- `rollback_unavailable`

Partial outputs must be quarantined rather than merged by default.

## Section VIII - Receipts, Quarantine, And Recovery

Recommended receipt families:

- `swarm.sandbox.prepared`
- `swarm.sandbox.activated`
- `swarm.snapshot.pre_execution`
- `swarm.snapshot.post_execution`
- `swarm.diff.captured`
- `swarm.output.quarantined`
- `swarm.orphan.detected`
- `swarm.stale_lock.detected`
- `swarm.rollback.available`

Minimum rollback definition in v1:

- the system can identify the pre-execution snapshot
- the system can identify the changed paths
- the system can define the method by which prior state would be restored

This work order does not require fully automatic rollback in v1, but rollback capability must be explicit rather than assumed.

## Section IX - Staging And Validation

Planning and staging should proceed in this order:

### Phase 0

Sandbox schema definition and lifecycle only.

### Phase 1

Read-only probe sandbox.

### Phase 2

Write-bounded sandbox with snapshot and diff capture.

### Phase 3

Quarantine, orphan detection, and stale-lock handling.

### Phase 4

Receipt-backed integration with leases and trace graph.

Required validation cases:

- worker attempts write outside scope -> sandbox violation
- worker attempts undeclared network access -> deny
- snapshot missing before write run -> block activation
- orphan worker outlives lease -> flag
- stale lock after lease expiry -> flag
- quarantined output remains excluded from merge path by default

## Section X - Success Criteria And Intent Confirmation

This work order is successful when:

- each worker runs in an isolated execution surface
- lease boundaries are enforced by sandbox boundaries
- pre and post state are observable
- rollback capability is defined per run
- partial output does not silently contaminate canonical state

Intent confirmation:

This work order is not about making workers freer.

It is about making worker execution containable, inspectable, and recoverable.
