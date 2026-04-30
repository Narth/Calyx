---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1

## Purpose

Normalize Calyx runtime topology so each canonical service has:

- a declared topology contract
- one effective runtime
- explicit shutdown semantics
- clear sunrise validation criteria

This work order is the governed normalization plan that follows `WO_RUNTIME_TOPOLOGY_LABELING_V1`.

## Status

Planning and governance definition only.

This document does not authorize immediate process mutation by itself.

## Background

Recent observation established that several canonical Calyx services currently appear as resident parent/child Python pairs:

- parent launcher path:
  - `C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe`
- effective child runtime path:
  - `C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe`

Observed services affected:

- Dev Harness
- CBO Core
- Avatar Web
- Telemetry Gateway
- Bridge Overseer
- CLI Avatar
- Discord Gateway

Observed listener ownership today:

- `7777` -> effective child runtime
- `7778` -> effective child runtime
- `7780` -> effective child runtime
- `7781` -> effective child runtime
- Discord transport -> effective child runtime

## Objective

Define and later execute a governed normalization path that determines:

1. whether resident parents are true supervisors, wrappers, or inert remnants
2. whether current wrapper-child behavior is intentional or accidental
3. which topology should be declared per service
4. what sunrise should validate
5. what shutdown should stop
6. how to reduce unjustified resource overhead without breaking service continuity

## Non-Goals

- No mutation during this design phase
- No sunrise behavior change during this design phase
- No production-path expansion
- No authority transfer from effective runtime to launcher presence
- No OpenClaw integration work
- No dependency-lane work

## Inputs and Evidence

Primary evidence:

- `C:\Calyx_Terminal\docs\planning\WO_RUNTIME_TOPOLOGY_LABELING_V1.md`
- `C:\Calyx_Terminal\runtime\receipts\governance\duplicate_runtime_classification__20260328_123553.json`
- `C:\Calyx_Terminal\runtime\receipts\governance\runtime_topology_labeling_design__20260328_125214.json`
- `C:\Calyx_Terminal\runtime\receipts\sunrise_receipt__20260328_114904.json`
- `C:\Calyx_Terminal\Scripts\start_calyx_core_services.ps1`

## Required Topology Contract

Each canonical service should eventually declare:

- `service_name`
- `topology_mode`
  - `single_process`
  - `wrapper_child_runtime_pair`
- `expected_parent_executable`
- `expected_child_executable`
- `effective_runtime_rule`
  - `listener_owner`
  - `active_network_child`
- `listener_ports`
- `supervision_required`
- `shutdown_scope`
- `resource_overhead_class`
  - `resource_overhead_expected`
  - `resource_overhead_excessive`

## Proposed Phase Order

### Phase 1 — Proof of Parent Role

Goal:

- determine whether each parent is:
  - `launcher_wrapper`
  - `runtime_supervisor`
  - `inert_resident_wrapper`

Required evidence:

- child survivability if parent exits
- restart semantics if child fails
- handle/relationship evidence where observable
- shutdown coupling evidence

Outputs:

- one receipt per service role classification

### Phase 2 — Effective Runtime Confirmation

Goal:

- confirm the exact effective runtime for each service

Rules:

- for core services, effective runtime defaults to the listener owner
- for Discord Gateway, effective runtime defaults to the `active_network_child`

Outputs:

- per-service effective runtime receipts

### Phase 3 — Contract Declaration

Goal:

- declare topology contract per canonical service

Candidate outcomes:

- keep `wrapper_child_runtime_pair` for some services
- normalize to `single_process` where justified

Outputs:

- topology contract artifact for each canonical service

### Phase 4 — Resource Normalization Decision

Goal:

- determine which resident parents are justified and which are wasteful

Decision classes:

- `resource_overhead_expected`
- `resource_overhead_excessive`

Outputs:

- resource classification receipt per service
- proposed cleanup set, if any

### Phase 5 — Shutdown Semantics Contract

Goal:

- define exact stop semantics for each service

Required outcome per service:

- parent only
- child only
- pair
- topology contract stop

Recommended default:

- stop the logical topology contract, not a guessed PID

### Phase 6 — Sunrise Validation Update

Goal:

- update sunrise validation from port-only/service-only assumptions to topology-contract validation

Validation should answer:

- is topology declared
- does the observed runtime match the declared topology
- is there exactly one effective runtime
- is extra residency justified

## Per-Service Normalization Targets

### Dev Harness

Preferred end state:

- `single_process`, unless wrapper-child is proven necessary

### CBO Core

Preferred end state:

- `single_process`, unless wrapper-child is proven necessary

### Avatar Web

Preferred end state:

- `single_process`, unless wrapper-child is proven necessary

### Telemetry Gateway

Preferred end state:

- `single_process`, unless wrapper-child is proven necessary

### Bridge Overseer

Preferred end state:

- only keep a resident parent if true supervision is proven

### CLI Avatar

Preferred end state:

- `single_process`

### Discord Gateway

Preferred end state:

- topology explicitly declares whether a resident parent is required
- effective runtime remains the transport-owning process

## Acceptable Outcomes

Acceptable normalization outcomes:

- declared wrapper-child pair with justified parent residency
- direct single-process runtime where no parent value is proven

Unacceptable outcomes:

- two effective runtimes for one logical service
- parent residency with no declared value and no measured need
- sunrise validating only parent presence when child is the actual runtime
- shutdown semantics that leave orphaned effective runtimes behind

## Resource Classification Rules

Mark a pair as `resource_overhead_expected` when:

- topology contract explicitly allows the pair
- parent provides actual lifecycle or governance value
- one logical service still maps to one effective runtime

Mark a pair as `resource_overhead_excessive` when:

- parent does not supervise
- parent does not own the effective port or active transport
- child remains fully operational without the parent
- residency materially contributes avoidable station heat

## Shutdown Semantics

Recommended future shutdown contract:

- if topology is `single_process`: stop the effective runtime
- if topology is `wrapper_child_runtime_pair`: stop the topology pair
- if service has active transport child: validate child shutdown, not merely parent disappearance

## Sunrise Validation Implications

Sunrise should evolve to validate:

1. declared topology contract exists
2. observed topology matches declaration
3. one effective runtime is present
4. no unexpected second listener exists
5. any extra resident parent is justified by contract

Recommended validation results:

- `pass`
  - topology matches contract
- `warn`
  - service is reachable but parent role remains unresolved
- `fail`
  - multiple effective runtimes
  - topology mismatch
  - listener conflict
  - declared shutdown scope cannot be reasoned about

## Required Receipts for Future Execution

If this work order later moves from design to execution, it should emit:

- `topology_parent_role__<service>__<timestamp>.json`
- `topology_effective_runtime__<service>__<timestamp>.json`
- `topology_contract_declared__<service>__<timestamp>.json`
- `topology_resource_classification__<service>__<timestamp>.json`
- `topology_shutdown_semantics__<service>__<timestamp>.json`
- `topology_sunrise_validation_update__<timestamp>.json`
- `topology_normalization_summary__<timestamp>.json`

## Success Criteria

This work order is successful when:

- every canonical Calyx service has an explicit topology contract
- every service has one effective runtime
- every resident parent is either justified or marked for normalization
- shutdown semantics are explicit
- sunrise validation is topology-aware rather than PID-guessing

## Recommended First Execution Order

1. Dev Harness
2. CBO Core
3. Avatar Web
4. Telemetry Gateway
5. Discord Gateway
6. Bridge Overseer
7. CLI Avatar

## Operator Notes

The current evidence suggests the observed duplication is real but not currently a service-bind conflict. That means normalization should prioritize topology clarity and measured cleanup rather than emergency intervention.
