---
status: active
owner: station
last_reviewed_utc: "2026-04-17"
doctrine_scope: governed
---

# WO_OPENCLAW_REINTEGRATION_PATH_V1

## Section I - Purpose And Scope

### Purpose

Define the governed path by which OpenClaw could be reintroduced as a bounded execution substrate inside Station Calyx.

This work order exists so OpenClaw, if it returns, does so only as:

- subordinate to Calyx authority
- bounded by worker leases
- contained by sandbox manifests
- observable through trace and receipts

### Scope

This work order governs:

- phased reintegration planning for OpenClaw
- identity mapping into swarm primitives
- lease, sandbox, and trace prerequisites
- execution gating requirements
- failure conditions that block progression

This work order does not:

- authorize activation
- authorize execution
- change runtime behavior
- reclassify OpenClaw as currently allowed

## Section II - Current State And Target State

### Current State

OpenClaw is currently:

- present
- capable
- historically integrated
- blocked from execution under current Station governance

Operationally, OpenClaw remains outside the active Calyx control plane because it is not yet bound to:

- `worker_lease`
- `sandbox_manifest`
- `trace_graph`
- receipt-backed execution gating

### Target State

OpenClaw may only return as:

`external_allowed_non_authoritative_execution_substrate`

Meaning:

- usable as an execution substrate
- never a source of authority
- never a parallel governance spine
- always subordinate to Calyx-minted leases and envelopes

## Section III - Relationship To Existing Work Orders

This work order is subordinate to:

- `WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1`
- `WO_SANDBOXED_WORKER_RUNTIME_V1`
- `WO_SWARM_TRACE_GRAPH_AND_RECEIPT_BUNDLE_V1`

OpenClaw reintegration may not invent a parallel control plane.

Required inheritance:

- root authority comes from the canonical `work_envelope`
- OpenClaw execution identity maps to `worker_id`
- OpenClaw authorization maps to `lease_id`
- OpenClaw containment maps to `sandbox_id`
- OpenClaw observability maps to `trace_node`

Shared lifecycle:

`proposal -> work_envelope -> worker_lease -> sandbox_prepare -> trace_init -> execute -> reconcile`

## Section IV - Reintegration Model And Shared Definitions

### `openclaw_runtime_identity`

The explicit identity record for one OpenClaw runtime instance observed on the machine.

### `openclaw_worker_binding`

The record binding an OpenClaw runtime instance to:

- `swarm_run_id`
- `worker_id`
- `lease_id`
- `sandbox_id`

### `openclaw_execution_gate`

The enforcement decision point that allows or denies an OpenClaw execution attempt based on governance prerequisites.

### `openclaw_capability_profile`

The declared tool, file, and network surface OpenClaw may use when operating under a lease.

Hard rule:

OpenClaw must never operate as free ambient capability. It must always be bound to explicit Calyx identifiers.

## Section V - Reintegration Phases

### Phase A - Identity And Containment Mapping

Goal:

Map OpenClaw processes and artifacts into Calyx execution vocabulary without allowing execution.

Required outputs:

- OpenClaw process identity model
- mapping from observed OpenClaw process family to `worker_id`
- binding stub from OpenClaw runtime to `lease_id`
- binding stub from OpenClaw runtime to future `sandbox_id`

Required conditions:

- every OpenClaw runtime family is explicitly discoverable
- every candidate OpenClaw execution surface is attributable
- no runtime remains anonymous

Execution status:

- no execution allowed

### Phase B - Sandbox Binding

Goal:

Require OpenClaw execution to inhabit the same containment model as any other worker.

Required outputs:

- OpenClaw-specific `sandbox_manifest` compatibility rules
- sandbox root derivation rules for OpenClaw workspaces
- pre-execution snapshot expectations
- post-execution diff expectations
- quarantine behavior for OpenClaw outputs

Required conditions:

- OpenClaw file access does not exceed `ownership_scope`
- OpenClaw tool access does not exceed `allowed_tool_classes`
- OpenClaw network posture does not exceed `network_scope`

Execution status:

- no execution allowed

### Phase C - Trace Binding

Goal:

Require every OpenClaw action to appear in the swarm trace graph.

Required outputs:

- OpenClaw trace-node mapping rules
- artifact reference policy for OpenClaw-produced outputs
- lease transition linkage for OpenClaw workers
- degraded-state handling when OpenClaw trace emission is incomplete

Required conditions:

- OpenClaw actions are attributable to `worker_id` and `lease_id`
- trace initialization occurs before any action
- missing trace is a block, not a warning

Execution status:

- no execution allowed

### Phase D - Execution Gate

Goal:

Define the conditions under which OpenClaw could be allowed to begin work.

OpenClaw execution must be denied unless all are true:

- root `work_envelope` exists
- `worker_lease` is in `active`
- `sandbox_manifest` is in `prepared`
- pre-execution snapshot exists
- `trace_graph` root exists
- OpenClaw worker node exists
- receipt bundle path is initialized

Execution status:

- no general execution allowed
- gate logic only

### Phase E - Controlled Activation

Goal:

Allow narrow, receipted, operator-visible OpenClaw execution after all prior phases are complete and validated.

Initial posture:

- one worker only
- one lease only
- one sandbox only
- bounded tool classes only
- bounded write scope only
- default deny network

Required conditions:

- full trace emission
- full receipt emission
- operator-visible state
- reconciliation before merge acceptance

Execution status:

- limited execution permitted only after separate approval work

## Section VI - Hard Requirements

OpenClaw must never:

- execute outside lease authority
- write outside sandbox scope
- act without trace emission
- bypass receipt generation
- widen authority through its own config or channel model
- originate a second governance path

Additional hard requirements:

1. OpenClaw must be lease-subordinate.
2. OpenClaw must be sandbox-contained.
3. OpenClaw must be trace-visible before action.
4. OpenClaw outputs must be reconcilable.
5. OpenClaw failure must fail closed.

## Section VII - Failure Conditions

Reintegration must stop if any of the following occur:

- OpenClaw process identity cannot be mapped to `worker_id`
- OpenClaw can execute before lease activation
- OpenClaw can write outside declared paths
- OpenClaw action occurs without a trace node
- OpenClaw output appears without artifact refs
- OpenClaw can call external systems outside `network_scope`
- OpenClaw can operate while receipt initialization is absent
- OpenClaw configuration can silently reintroduce channel authority or ambient execution

Phase-specific block conditions:

- Phase A block: unresolved runtime identity or unmatched process family
- Phase B block: sandbox inheritance cannot be enforced
- Phase C block: trace graph cannot represent OpenClaw actions structurally
- Phase D block: execution gate can be bypassed
- Phase E block: controlled run cannot be fully receipted and reconciled

## Section VIII - Enforcement Prerequisites

OpenClaw may not be reclassified into an allowed execution substrate until the following are proven:

### Control Plane Prerequisites

- stable `worker_lease` issuance
- enforced lease lifecycle
- ownership conflict rejection

### Containment Prerequisites

- sandbox manifests enforce lease boundaries
- snapshot and diff capture are available
- quarantine path exists for suspicious outputs

### Trace Prerequisites

- trace root exists before worker start
- OpenClaw worker nodes are created deterministically
- receipt bundle can include OpenClaw artifacts without schema fork

### Governance Prerequisites

- OpenClaw remains non-authoritative
- OpenClaw cannot own Discord or another channel as a silent control path
- OpenClaw docs and config cannot override current Station authority

## Section IX - Staging And Validation

Recommended implementation order:

### Stage 0

Planning and terminology only.

### Stage 1

Phase A identity binding artifacts and validation.

### Stage 2

Phase B sandbox compatibility model and validation.

### Stage 3

Phase C trace compatibility and bundle integration.

### Stage 4

Phase D execution gate checks with deny-only behavior.

### Stage 5

Phase E controlled activation under separate explicit approval.

Required validation cases:

- OpenClaw runtime detected without worker binding -> deny
- OpenClaw worker with no active lease -> deny
- OpenClaw lease active but no prepared sandbox -> deny
- OpenClaw prepared sandbox but no trace root -> deny
- OpenClaw action without artifact refs -> deny
- OpenClaw output outside ownership scope -> quarantine and deny merge

## Section X - Success Criteria And Intent Confirmation

This work order is successful when:

- the path for reintegration is explicit and staged
- OpenClaw cannot return as ambient capability
- OpenClaw can only return by satisfying lease, sandbox, trace, and gate prerequisites
- failure conditions are clear enough to block unsafe partial reintegration

Intent confirmation:

This work order does not restore OpenClaw.

It defines how OpenClaw could earn re-entry only as a bounded, auditable, non-authoritative execution substrate under Station Calyx governance.
