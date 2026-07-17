---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# WO_SWARM_TRACE_GRAPH_AND_RECEIPT_BUNDLE_V1

## Section I - Purpose And Scope

### Purpose

Define the observability model for governed swarm execution.

This work order exists so a swarm run can be:

- traced structurally
- audited after the fact
- replayed at the sequence level
- reconciled against lease and sandbox boundaries

### Scope

This work order governs:

- swarm trace graph structure
- trace-node requirements
- receipt bundle contents
- replay guarantees
- anomaly recording
- merge decision capture

This work order does not:

- mint leases
- create sandbox boundaries
- replace the existing Calyx receipt philosophy
- authorize execution by itself

## Section II - Relationship To Leases And Sandboxes

This work order is subordinate to:

- `WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1`
- `WO_SANDBOXED_WORKER_RUNTIME_V1`

The trace graph must reflect:

- `work_envelope` authority
- `worker_lease` lifecycle transitions
- sandbox preparation and sealing
- worker actions
- tests
- reconciliation
- merge disposition

The receipt bundle must unify the outputs of all three systems rather than fragment them into unrelated artifact families.

## Section III - Shared Definitions

### `trace_node_id`

The canonical identifier for one trace node.

### `trace_graph`

The directed acyclic execution graph for one `swarm_run_id`.

### `receipt_bundle_id`

The canonical identifier for one swarm receipt bundle.

### `merge_decision`

The governed decision describing whether worker outputs are accepted, rejected, deferred, or quarantined.

### `anomaly_record`

A bounded record describing lease, sandbox, trace, or validation irregularity.

### `replay_manifest`

The minimal artifact set required to reconstruct the structural execution sequence of a swarm run.

## Section IV - Core Trace And Bundle Schemas

### A. `swarm_trace_node`

Canonical planning schema:

```text
swarm_trace_node = {
  schema,
  schema_version,
  swarm_run_id,
  work_envelope_id,
  lease_id,
  worker_id,
  sandbox_id,
  node_id,
  parent_id,
  action_type,
  timestamp_utc,
  inputs,
  outputs,
  result_status,
  artifact_refs,
  notes
}
```

Required node fields per this work order:

- `node_id`
- `parent_id`
- `action_type`
- `timestamp_utc`
- `inputs`
- `outputs`
- `result_status`

Bounded input/output rule:

- trace nodes may contain summarized or hashed payloads
- trace nodes should not silently omit the existence of material inputs or outputs
- large payloads should be stored as separate artifacts and referenced by path

### B. Trace Graph Structure

Required hierarchy:

- root node: orchestrator or planner
- child nodes: workers
- grandchild nodes: tool calls, tests, actions, and lifecycle events

Recommended `action_type` values:

- `plan`
- `lease_transition`
- `sandbox_prepare`
- `tool_call`
- `command`
- `test_run`
- `artifact_write`
- `reconciliation`
- `merge_decision`

### C. `swarm_receipt_bundle`

Canonical planning schema:

```text
swarm_receipt_bundle = {
  schema,
  schema_version,
  receipt_bundle_id,
  swarm_run_id,
  work_envelope_id,
  issued_at_utc,
  work_envelope_ref,
  worker_leases,
  sandbox_manifests,
  trace_graph_ref,
  test_results,
  merge_decision,
  anomalies,
  reconciliation_summary,
  replay_manifest,
  bundle_status
}
```

## Section V - Required Behavior

The trace and bundle system must ensure:

1. every swarm run has exactly one root trace graph
2. every worker action is attributable to `worker_id` and `lease_id`
3. lease lifecycle transitions appear in the trace graph
4. sandbox preparation and sealing appear in the trace graph
5. tests and merge decisions are bundled with the run
6. anomalies are preserved rather than normalized away

Hard rule:

No swarm run is considered structurally complete without a receipt bundle.

## Section VI - Lifecycle And Trace Transition Requirements

The trace graph must cover the full governed lifecycle:

```text
proposal
-> work_envelope minted
-> worker_leases proposed
-> worker_leases approved
-> sandboxes prepared
-> worker activation
-> worker actions and tests
-> lease completion/revocation/expiry
-> reconciliation
-> merge decision
-> receipt bundle sealed
```

Required trace properties:

- monotonic structural order
- parent-child linkage
- explicit result status for each node
- lease-state visibility at the node level where applicable

Required `result_status` values:

- `pending`
- `running`
- `passed`
- `failed`
- `blocked`
- `revoked`
- `expired`
- `quarantined`

## Section VII - Replay Guarantees And Operator Visibility

Minimum replay guarantees:

1. reconstruct root authority artifact
2. reconstruct worker set and lease timing
3. reconstruct sandbox identity per worker
4. reconstruct command/test/action order
5. reconstruct changed artifact references
6. reconstruct merge disposition and anomaly set

Replay does not require full raw stdout retention for every step in v1.

Replay does require enough evidence to answer:

- what was authorized
- who acted
- in what order
- within what sandbox
- under what lease
- with what result

Operator-visible bundle contents must include:

- root task summary
- worker list and final states
- test outcome summary
- merge decision
- anomalies and unresolved debt

## Section VIII - Alignment With Existing Calyx Receipts And Constraints

This work order must align with the existing Calyx receipt philosophy:

- canonical JSON
- deterministic or stable key ordering where practical
- schema-named receipt families
- plain-path artifact references
- no silent omission of failure or anomaly

This work order must not fork the existing receipt model into an unrelated telemetry silo.

Hard constraints:

- `worker_id` must match the control-plane lease records
- `lease_id` must be referenced in trace nodes
- `sandbox_id` must match sandbox manifests
- receipt bundle paths must remain attributable to `swarm_run_id`

## Section IX - Staging And Validation

Planning and staging should proceed in this order:

### Phase 0

Trace and bundle schema definition only.

### Phase 1

Single-worker trace graph.

### Phase 2

Multi-worker graph with lease transitions.

### Phase 3

Sandbox and test artifact references.

### Phase 4

Bundle sealing and replay validation.

Required validation cases:

- missing lease reference in worker node -> invalid
- missing root planner node -> invalid
- merge decision without test evidence -> degraded bundle
- anomaly omitted from bundle -> invalid
- replay manifest missing sandbox or diff refs -> degraded replay guarantee

## Section X - Success Criteria And Intent Confirmation

This work order is successful when:

- the structural sequence of a swarm run can be reconstructed
- lease and sandbox boundaries are visible inside the trace
- bundle contents are sufficient for governed review
- anomalies remain visible through reconciliation
- merge decisions are attributable rather than narrative

Intent confirmation:

This work order does not exist to decorate the swarm with extra logs.

It exists to make swarm execution structurally knowable, reviewable, and replayable.
