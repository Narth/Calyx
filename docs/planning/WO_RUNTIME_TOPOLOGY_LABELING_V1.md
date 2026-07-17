---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_RUNTIME_TOPOLOGY_LABELING_V1

## Purpose

Formalize Calyx runtime topology labels, expected parent/child behavior, resource semantics, shutdown semantics, and sunrise validation rules for the observed Python runtime pattern.

This work order is design-only. It does not authorize process mutation, startup changes, or normalization work by itself.

## Observed Problem

The canonical sunrise path launches Python services using:

- `C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe`

But the effective resident service runtimes observed after sunrise are frequently child processes using:

- `C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe`

This creates parent/child pairs that look duplicative at a glance, but are not necessarily port conflicts.

## Runtime Topology Definitions

### `launcher_wrapper`

A parent process whose primary role is to launch a service/runtime child and retain minimal residency, without owning the authoritative service port itself.

Expected properties:

- spawned by sunrise or another declared launcher
- may remain resident
- does not need to own the service port
- may retain stdio/process-tree responsibility

### `runtime_supervisor`

A parent process that is expected to observe, restart, or directly govern a child runtime after launch.

Expected properties:

- supervisor intent is explicit and declared
- restart or liveness responsibility is defined
- parent residency is justified by active supervisory function

### `effective_service_runtime`

The process that actually performs the service role for governance and resource accounting purposes.

Expected properties:

- owns the canonical listener, or
- performs the active network/runtime behavior that defines the service

### `wrapper_child_runtime_pair`

A declared topology where a launcher wrapper remains resident and a child process becomes the effective service runtime.

Expected properties:

- one logical service
- one effective runtime
- parent and child are attributable to the same launch event

### `duplicate_runtime_pair_non_listener`

Two resident processes appear to run the same module or service identity, but neither classification nor port ownership alone proves conflict.

Expected properties:

- no duplicate listener conflict
- may still impose overhead
- requires further classification before cleanup

### `active_network_child`

A child runtime that owns the active outbound or inbound network activity that materially defines the service.

Expected properties:

- child, not parent, is the effective runtime for transport governance

### `inert_resident_wrapper`

A launcher wrapper that remains resident but provides no needed supervision, no port ownership, and no meaningful governance function.

Expected properties:

- safe candidate for future normalization review
- not automatically safe to kill without a separate governed pass

### `topology_mismatch`

Observed runtime shape differs from the declared contract for that service.

Expected properties:

- may still function
- should fail topology validation or at least warn during sunrise verification

### `resource_overhead_expected`

Extra residency that is justified by declared runtime topology.

### `resource_overhead_excessive`

Extra residency or duplication that is not justified by declared topology and creates avoidable steady-state cost.

## Per-Service Expected Topology

### Dev Harness

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair`

Effective runtime:

- the process that owns port `7777`

### CBO Core

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair`

Effective runtime:

- the process that owns port `7778`

### Avatar Web

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair`

Effective runtime:

- the process that owns port `7780`

### Telemetry Gateway

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair`

Effective runtime:

- the process that owns port `7781`

### Discord Gateway

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair` where the child is the `active_network_child`

Effective runtime:

- the process that owns the live Discord transport activity

### Bridge Overseer

Expected topology:

- one declared logical service
- acceptable:
  - direct single-process runtime, or
  - `wrapper_child_runtime_pair` only if supervisory need is explicit

Effective runtime:

- the process doing live cycle execution

### CLI Avatar

Expected topology:

- interactive/manual surface
- preferred:
  - direct single-process runtime

Acceptable only with justification:

- `wrapper_child_runtime_pair`

## Classification Rules

### When a parent is a `launcher_wrapper`

Classify the parent as `launcher_wrapper` when:

- it is created by sunrise or another declared launcher
- it spawns the effective child runtime
- it does not own the service port
- no active supervisory behavior is yet proven

### When a parent is a `runtime_supervisor`

Classify the parent as `runtime_supervisor` only when:

- restart, health, or lifecycle supervision is explicit
- the supervisory responsibility is documented
- the child depends on the parent remaining alive

### When a parent is an `inert_resident_wrapper`

Classify the parent as `inert_resident_wrapper` when:

- it is resident
- it does not own the effective port or active network behavior
- no supervision semantics are declared or observed

### When a child is `effective_service_runtime`

Classify the child as `effective_service_runtime` when:

- it owns the listener for the service, or
- it owns the active network transport that defines the runtime

### `resource_overhead_expected` vs `resource_overhead_excessive`

`resource_overhead_expected` applies when:

- a declared topology contract allows a resident parent/child pair
- one logical service still maps cleanly to one effective runtime

`resource_overhead_excessive` applies when:

- parent residency is unjustified
- multiple effective runtimes exist for one logical service
- duplication materially raises steady-state heat without declared governance value

## Acceptable vs Wasteful Pairs

Acceptable:

- `wrapper_child_runtime_pair` where the child is clearly the single effective runtime and the pair is declared
- `active_network_child` where transport authority is clearly on the child

Conditionally acceptable pending declaration:

- current sunrise-created parent/child service pairs

Potentially wasteful:

- `duplicate_runtime_pair_non_listener` without declared supervisory semantics
- any resident parent that neither supervises nor contributes governance value

## Shutdown Semantics

### For a `wrapper_child_runtime_pair`

Shutdown semantics should be defined at the topology level, not guessed per PID.

Rule:

- stopping the logical service should stop both parent and child

### For `effective_service_runtime`

The effective runtime is authoritative for service liveness and should be the primary shutdown target in validation reasoning.

### For `launcher_wrapper`

If parent shutdown leaves the child running, the parent is not sufficient as the service shutdown target.

### For `runtime_supervisor`

If the supervisor is real, shutdown should include both:

- the supervisor
- the effective runtime

### For `inert_resident_wrapper`

Potential cleanup target in a future normalization pass, but only after shutdown semantics are proven.

## Sunrise Validation Implications

Sunrise should validate a declared topology contract, not just raw process counts.

### Sunrise should not validate only the parent

Reason:

- the parent may be only a launcher wrapper and not the effective runtime

### Sunrise should not validate only the child

Reason:

- a declared supervisory parent may matter for lifecycle expectations

### Sunrise should validate a declared topology contract

Recommended contract fields per service:

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

### Sunrise pass criteria

- exactly one logical runtime topology per declared service
- exactly one effective runtime per logical service
- no unexpected second listener on canonical service ports
- topology matches declared contract

### Sunrise warn criteria

- topology functions but parent classification is unresolved
- wrapper residency exists without declared justification

### Sunrise fail criteria

- multiple effective runtimes for one service
- unexpected listener conflict
- declared topology contract violated

## Answers to the Required Questions

### 1. Which observed parent processes are true supervisors, wrappers, or inert launch remnants?

Current best governance answer:

- observed `.venv_cbohub311` parents should default to `launcher_wrapper`
- none should yet be promoted to `runtime_supervisor` without explicit supervisory proof
- some may later be reclassified as `inert_resident_wrapper`

### 2. Which child processes are the effective service runtimes?

Current best governance answer:

- the child process that owns the canonical listener is the `effective_service_runtime`
- for Discord Gateway, the child that owns the active network behavior is the effective runtime

### 3. What exact topology is expected per canonical Calyx service?

Recommended:

- either `single_process`
- or declared `wrapper_child_runtime_pair`

### 4. Which resident parent/child pairs are acceptable, and which are wasteful?

Acceptable:

- declared wrapper-child pairs with one effective runtime

Wasteful:

- unresolved or unjustified resident parents with no supervisory value

### 5. What shutdown semantics should apply to each pair?

Recommended:

- logical-service shutdown must target the whole declared topology contract

### 6. What should sunrise validate?

Recommended:

- a declared topology contract

## Recommended Next Normalization Work Order

`WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1`

Scope:

1. Prove whether `.venv_cbohub311` parents supervise or merely launch
2. Declare per-service topology contracts
3. Remove or redesign unjustified resident wrappers
4. Update sunrise validation to check topology contract compliance
5. Keep service authority with the effective runtime, not raw parent presence
