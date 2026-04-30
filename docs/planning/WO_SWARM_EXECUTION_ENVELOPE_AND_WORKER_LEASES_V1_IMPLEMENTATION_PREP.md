---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1_IMPLEMENTATION_PREP

## Section I - Purpose And Scope

### Purpose

Prepare `WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1` for staged implementation without enabling worker execution.

This artifact converts the planning schema into concrete implementation targets:

- modules and files to extend
- new modules to add
- integration points inside the existing governance spine
- receipt emission locations
- a staging-first path for Phases 0 through 2

### Scope

This implementation-prep pass governs:

- schema placement
- validation entry points
- static lease issuance design
- ownership conflict detection design
- planning receipts for implementation preparation

This pass does not:

- enable live worker execution
- introduce overlapping write behavior
- activate sandboxing
- mutate runtime services
- require sunrise

## Section II - Active Authority Context

This pass is grounded in the current Active Authority Context:

- `thread_origin_objective = move COMPENDIUM.md`
- `objective_state = satisfied`
- `thread_demotion = enforced`

Current governing authority:

- `swarm infrastructure planning and execution`

Current authority basis:

- current Station state
- latest completed work orders:
  - `WO_RUNTIME_MULTIPLICITY_VISIBILITY_AND_RECONCILIATION_V1`
  - `WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1`
  - `WO_ACTIVE_AUTHORITY_CONTEXT_AND_THREAD_DEMOTION_V1`
- active swarm infrastructure build sequence

This artifact is therefore justified by current swarm-governance work, not by historical thread origin.

## Section III - Existing Spine Anchors

WO1 must extend the current canonical spine rather than fork it.

Existing anchor modules:

- `calyx/kernel/envelope.py`
  - canonical `WorkEnvelope`
- `calyx/cbo/intent_pipeline/plan.py`
  - plan building and Work Envelope minting
- `calyx/kernel/contract.py`
  - deny-by-default Work Envelope validation
- `calyx/execution/hub_runner.py`
  - envelope execution, checkpointing, receipts, manifests
- `calyx/kernel/receipts.py`
  - canonical receipt writer
- `docs/SPINE.md`
  - institutional object-flow authority
- `CALYX_CONTRACT.yaml`
  - task, source, and tool-surface policy

Core implementation rule:

Swarm control must appear as a governed extension of the canonical `WorkEnvelope`, not as a second execution envelope type.

## Section IV - Implementation Targets

### A. Existing Modules To Extend

#### 1. `calyx/kernel/envelope.py`

Implementation target:

- extend canonical serialization support for reserved swarm fields under:
  - `scope.swarm`
  - `constraints.swarm`

Required changes:

- no new top-level envelope authority type
- preserve deterministic hash behavior
- ensure swarm fields survive `to_canonical_dict()` and `from_dict()`

Recommendation:

- keep the current dataclass shape stable
- validate swarm extensions as nested structures rather than exploding the top-level dataclass immediately

#### 2. `calyx/cbo/intent_pipeline/plan.py`

Implementation target:

- allow intent planning to build a swarm-aware plan artifact before minting the root Work Envelope

Required changes:

- optional plan-time assembly of:
  - `swarm_run_id`
  - `worker_plan`
  - `file_scope`
  - `tool_scope`
  - `network_scope`
  - `success_criteria`
- persist swarm-aware planning fields into `plan.json`
- mint canonical Work Envelope with reserved swarm fields nested under `scope` and `constraints`

#### 3. `calyx/kernel/contract.py`

Implementation target:

- validate swarm extensions inside the canonical Work Envelope

Required changes:

- add swarm-schema validation hooks
- ensure worker-plan fields cannot silently exceed root envelope scope
- deny malformed or contradictory swarm ownership declarations
- preserve existing deny-by-default behavior

Recommendation:

- do not add live worker-execution allow rules in Phase 0
- treat malformed swarm fields as validation failures even before any worker runtime exists

#### 4. `calyx/execution/hub_runner.py`

Implementation target:

- introduce staged handling for swarm-enabled envelopes without executing workers

Required changes by phase:

- Phase 0:
  - schema validation only
  - no lease activation
- Phase 1:
  - static lease issuance artifact generation
  - no worker process or sandbox activation
- Phase 2:
  - ownership conflict detection before any future activation point

Hard constraint:

`hub_runner` must not become a hidden worker orchestrator in this phase.

#### 5. `calyx/kernel/receipts.py`

Implementation target:

- reuse canonical receipt writers for swarm governance artifacts

Required changes:

- none required for Phase 0 if payloads obey current receipt requirements
- optional helper wrappers may be added in later phases for swarm receipt families

### B. New Modules To Add

#### 1. `calyx/kernel/swarm_lease.py`

Proposed responsibility:

- canonical `worker_lease` schema helpers
- lifecycle transition validation
- ownership-scope validation
- conflict detection helpers

Reason:

WO1 is a control-plane concern and belongs closer to envelope/contract/receipt logic than to task handlers.

#### 2. `calyx/kernel/swarm_work_envelope.py`

Proposed responsibility:

- validation helpers for `scope.swarm` and `constraints.swarm`
- normalization of swarm extension fields
- compatibility helpers between canonical envelope and swarm extension

Reason:

This keeps swarm-specific shape validation out of the base `WorkEnvelope` implementation while preserving the one-envelope rule.

#### 3. `tests/test_swarm_work_envelope.py`

Proposed responsibility:

- schema and inheritance validation tests

#### 4. `tests/test_worker_lease_validation.py`

Proposed responsibility:

- lease-state, scope, and overlap validation tests

#### 5. `tests/test_swarm_hub_runner_staging.py`

Proposed responsibility:

- verify hub-runner staged behavior:
  - validate only
  - static issuance only
  - conflict detection only

## Section V - Integration Points

### A. Intent Pipeline Integration

Integration point:

- `build_plan()` in `calyx/cbo/intent_pipeline/plan.py`

Required behavior:

- support optional swarm-aware plan construction
- keep non-swarm plans unchanged

### B. Work Envelope Minting Integration

Integration point:

- `mint_work_envelope()` in `calyx/cbo/intent_pipeline/plan.py`

Required behavior:

- mint one root envelope only
- embed swarm plan fields as governed nested extensions

### C. Contract Gate Integration

Integration point:

- `validate_work_envelope()` in `calyx/kernel/contract.py`

Required behavior:

- validate swarm extension shape and inheritance
- deny undeclared overlap or malformed scope

### D. Execution Spine Integration

Integration point:

- `run_work_envelope()` in `calyx/execution/hub_runner.py`

Required behavior:

- accept swarm-enabled envelopes in staged mode
- emit receipts for validation, proposed leases, and conflict detection
- stop short of worker execution

### E. Receipt Integration

Integration point:

- canonical receipt pathing through `calyx/kernel/receipts.py`

Required behavior:

- use existing receipt philosophy
- keep swarm artifacts attributable to:
  - `swarm_run_id`
  - `work_envelope_id`
  - `lease_id`
  - `worker_id`

## Section VI - Artifact And Receipt Locations

### A. Proposed Runtime Artifact Locations

Planning target paths:

- `runtime/cbo/swarm/<swarm_run_id>/work_envelope.json`
- `runtime/cbo/swarm/<swarm_run_id>/worker_leases.json`
- `runtime/cbo/swarm/<swarm_run_id>/ownership_map.json`
- `runtime/cbo/swarm/<swarm_run_id>/conflict_report.json`

These paths are staging artifacts and do not imply live worker runtime.

### B. Proposed Receipt Families

Recommended receipt locations:

- governance-oriented planning and lifecycle receipts:
  - `runtime/receipts/governance/`
- execution-adjacent staging receipts:
  - `runtime/receipts/audit/`

Recommended receipt families:

- `swarm.work_envelope.validated`
- `swarm.worker_lease.proposed`
- `swarm.worker_lease.approved`
- `swarm.worker_lease.issuance_static`
- `swarm.ownership.conflict_detected`
- `swarm.ownership.validation_passed`

### C. Planning Receipt For This Pass

This implementation-prep pass should emit a planning receipt under:

- `runtime/receipts/audit/`

with current AAC summary, WO reference, and identified implementation targets.

## Section VII - Staging-First Implementation Path

### Phase 0 - Schema And Validation Only

Goal:

- add schema helpers
- extend envelope parsing and contract validation
- do not issue or activate worker leases at runtime

Implementation targets:

- `calyx/kernel/swarm_work_envelope.py`
- `calyx/kernel/swarm_lease.py`
- `calyx/kernel/envelope.py`
- `calyx/kernel/contract.py`
- tests for shape and deny conditions

Validation cases:

- malformed `scope.swarm`
- malformed `constraints.swarm`
- worker plan exceeds root file scope
- undeclared overlap in write paths

### Phase 1 - Static Lease Issuance

Goal:

- generate and persist `worker_lease` artifacts from a valid root envelope
- do not activate any worker runtime

Implementation targets:

- `calyx/cbo/intent_pipeline/plan.py`
- `calyx/execution/hub_runner.py`
- `calyx/kernel/swarm_lease.py`

Required outputs:

- static `worker_leases.json`
- receipt-backed issuance events

Validation cases:

- valid root envelope produces leases
- duplicate `worker_id` denied
- lease scope wider than root envelope denied
- missing `success_criteria` denied

### Phase 2 - Conflict Detection And Enforcement Hooks

Goal:

- detect ownership conflicts and block future activation paths
- add enforcement hooks without enabling worker execution

Implementation targets:

- `calyx/kernel/swarm_lease.py`
- `calyx/execution/hub_runner.py`
- tests for scope conflicts and forbidden overlap

Required outputs:

- `ownership_map.json`
- `conflict_report.json`
- conflict detection receipts

Validation cases:

- overlapping write paths without declaration -> deny
- write path outside root file scope -> deny
- tool-class request outside root tool scope -> deny
- network scope widened by worker lease -> deny

## Section VIII - Risk Boundaries And Non-Goals

Hard boundaries for this implementation-prep pass:

- no live worker execution
- no sandbox preparation yet
- no trace graph implementation yet
- no overlapping write enablement
- no parallel write behavior

This pass prepares WO1 implementation without advancing into WO2 or WO3 runtime behavior.

## Section IX - Recommended File Change Set For The Future Implementation Pass

Primary code targets:

- `calyx/kernel/envelope.py`
- `calyx/kernel/contract.py`
- `calyx/cbo/intent_pipeline/plan.py`
- `calyx/execution/hub_runner.py`
- `calyx/kernel/swarm_work_envelope.py` (new)
- `calyx/kernel/swarm_lease.py` (new)

Primary tests:

- `tests/test_swarm_work_envelope.py` (new)
- `tests/test_worker_lease_validation.py` (new)
- `tests/test_swarm_hub_runner_staging.py` (new)

Possible policy touchpoint in later phase:

- `CALYX_CONTRACT.yaml`

Note:

Phase 0 should avoid contract expansion unless schema validation cannot be expressed through current contract hooks. If a contract update becomes necessary, it should be staged separately because contract edits are governance-sensitive.

## Section X - Success Criteria And Intent Confirmation

This implementation-prep pass is successful when:

- WO1 planning schema is translated into concrete module targets
- integration points with the existing spine are explicit
- receipt locations are defined
- Phases 0 through 2 can be implemented without redefining WO1 terminology
- no worker capability is enabled prematurely

Intent confirmation:

This artifact prepares governed implementation.

It does not activate swarm behavior.
