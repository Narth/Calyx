---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1

## Section I - Purpose And Scope

### Purpose

Define the swarm control plane for Station Calyx.

This work order extends the existing canonical Calyx Work Envelope model into a swarm-capable execution substrate where:

- CBO remains the only authority that mints execution authority
- work is decomposed into bounded worker assignments
- every worker receives a lease with explicit scope and expiry
- no worker may act outside the lease it was issued

### Scope

This work order governs:

- swarm-capable `work_envelope` extensions
- `worker_lease` definition and lifecycle
- ownership and write-scope rules
- bounded worker budgets
- lease-state receipts and operator visibility

This work order does not:

- define sandbox implementation details
- define trace storage and replay structures in full
- authorize runtime mutation by itself
- authorize overlapping write access by default

## Section II - Relationship To The Canonical Spine

This work order extends, and does not replace, the canonical Calyx spine:

`Mail -> Intent Artifact -> Work Envelope -> Contract Gate -> Execution -> Receipts`

The canonical `WorkEnvelope` remains the only envelope type that may trigger execution.

Swarm execution therefore follows this rule:

- CBO mints one canonical `work_envelope`
- the envelope may include swarm-specific fields under governed `scope` and `constraints`
- workers never execute raw user intent
- workers never mint authority
- workers only act under a valid `worker_lease` derived from the root `work_envelope`

This keeps swarm execution subordinate to the existing spine rather than creating a second authority path.

## Section III - Shared Definitions

The following terms are shared across:

- `WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1`
- `WO_SANDBOXED_WORKER_RUNTIME_V1`
- `WO_SWARM_TRACE_GRAPH_AND_RECEIPT_BUNDLE_V1`

### `swarm_run_id`

The canonical identifier for one governed swarm run.

### `work_envelope_id`

The `envelope_id` of the canonical Calyx `WorkEnvelope` that authorizes the swarm run.

### `worker_id`

A stable per-run worker identity such as `worker-01`, `worker-02`, or `worker-verify-01`.

### `lease_id`

The canonical identifier for one worker lease. A lease belongs to exactly one `worker_id` within one `swarm_run_id`.

### `ownership_scope`

The declared read and write surface assigned to a worker.

### `allowed_tool_classes`

The bounded categories of tools a worker may use, such as:

- `read_files`
- `write_files`
- `run_shell`
- `run_tests`
- `inspect_process`
- `vcs_metadata`
- `network_access`

### `network_scope`

The declared network posture for the work, default deny unless explicitly allowlisted.

### `reconciliation`

The governed close-out step that verifies lease closure, artifact integrity, merge disposition, and unresolved anomalies.

## Section IV - Core Schemas

### A. `work_envelope` Swarm Extension

This work order extends the canonical `WorkEnvelope` by reserving:

- `scope.swarm`
- `constraints.swarm`

Required swarm fields:

```text
scope.swarm = {
  swarm_run_id,
  task_intent,
  file_scope,
  tool_scope,
  network_scope,
  success_criteria,
  worker_plan
}

constraints.swarm = {
  ownership_policy,
  overlapping_write_scope_declared,
  requires_receipt_bundle,
  requires_trace_graph,
  reconciliation_required
}
```

Required field meanings:

- `task_intent`: bounded execution goal for the swarm run
- `file_scope`: repo paths in scope for read and write
- `tool_scope`: allowed tool classes for the run
- `network_scope`: declared network posture, default deny
- `success_criteria`: explicit acceptance conditions
- `worker_plan`: declared expected worker set and responsibilities
- `ownership_policy`: default `exclusive_write_scope`

### B. `worker_lease`

Canonical planning schema:

```text
worker_lease = {
  schema,
  schema_version,
  swarm_run_id,
  work_envelope_id,
  lease_id,
  worker_id,
  lease_state,
  issued_at_utc,
  expires_at_utc,
  max_runtime_sec,
  token_budget,
  compute_budget,
  ownership_scope,
  allowed_tool_classes,
  network_scope,
  success_criteria,
  approval_context,
  revocation_reason,
  notes
}
```

Required semantics:

- `token_budget` and `compute_budget` may be conceptual in v1 if not yet enforceable
- `ownership_scope` must include:
  - `read_paths`
  - `write_paths`
  - `deny_paths`
- `allowed_tool_classes` must be explicit, not inherited silently
- `network_scope` must mirror or narrow the root `work_envelope`

### C. Ownership Model

Default rule:

- read scope may overlap
- write scope may not overlap

Overlapping write scope is permitted only when all of the following are true:

- overlap is explicitly declared in the root `work_envelope`
- affected paths are named
- merge order is defined
- reconciliation ownership is assigned

## Section V - Required Behavior

The control plane must enforce the following rules:

1. Only CBO may mint the root `work_envelope`.
2. No worker may become active without a `worker_lease`.
3. No worker may write outside `ownership_scope.write_paths`.
4. No worker may use tool classes outside `allowed_tool_classes`.
5. No worker may use network access unless `network_scope` allows it.
6. No worker may silently expand authority by spawning unleased peer workers.
7. Every lease must inherit from, and never exceed, the root `work_envelope`.

Hard rule:

No worker may act outside its lease.

## Section VI - Lease Lifecycle And State Transitions

Allowed lease states:

- `proposed`
- `approved`
- `active`
- `expired`
- `revoked`
- `completed`

Allowed transitions:

```text
proposed -> approved
approved -> active
approved -> revoked
approved -> expired
active -> completed
active -> revoked
active -> expired
```

Disallowed transitions include:

- `completed -> active`
- `revoked -> active`
- `expired -> active`

Shared lifecycle for coordinated swarm execution:

```text
proposal -> intent clarification -> work_envelope minted -> worker_leases proposed
-> worker_leases approved -> worker sandboxes prepared -> worker_leases active
-> execution and trace capture -> worker_leases completed/revoked/expired
-> reconciliation -> merge decision -> receipt bundle sealed
```

## Section VII - Receipts, Artifacts, And Operator Visibility

Recommended lease artifact families:

- `swarm.lease.proposed`
- `swarm.lease.approved`
- `swarm.lease.activated`
- `swarm.lease.expired`
- `swarm.lease.revoked`
- `swarm.lease.completed`

Minimum receipt fields:

- `schema`
- `receipt_type`
- `timestamp_utc`
- `swarm_run_id`
- `work_envelope_id`
- `lease_id`
- `worker_id`
- `lease_state`
- `ownership_scope`
- `allowed_tool_classes`
- `network_scope`
- `reason`

Operator-facing requirements:

- current workers by `worker_id`
- lease state for each worker
- write ownership map
- expired and revoked leases
- unresolved scope conflicts

## Section VIII - Constraints And Non-Goals

Hard constraints:

- no lease inheritance by implication
- no unbounded worker runtime
- no write overlap by default
- no network access by default
- no worker authority outside the root `work_envelope`

Non-goals:

- real-time token metering in v1
- autonomous lease renewal
- implicit cross-worker shared state
- automatic merge of overlapping write outputs

## Section IX - Staging And Validation

Planning and staging should proceed in this order:

### Phase 0

Schema and terminology definition only.

### Phase 1

Static lease issuance and validation.

### Phase 2

Ownership conflict detection before activation.

### Phase 3

Receipt-backed lifecycle transitions.

### Phase 4

Integration with sandbox and trace systems.

Required validation cases:

- worker lease exceeds envelope scope -> deny
- overlapping write paths without declaration -> deny
- expired lease activation attempt -> deny
- revoked lease execution attempt -> deny
- network request outside `network_scope` -> deny

## Section X - Success Criteria And Intent Confirmation

This work order is successful when:

- every worker is bounded by a lease
- every lease is bounded by the root `work_envelope`
- ownership is explicit before execution begins
- overlapping write authority cannot appear silently
- lease lifecycle can be receipted and audited

Intent confirmation:

This work order does not construct unbounded autonomy.

It constructs delegated, revocable capability with explicit scope and expiry.
