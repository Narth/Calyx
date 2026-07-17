---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1

## Purpose

Require any Calyx service that may create additional resident or child runtime surfaces to declare that multiplicity in advance, distinguish contract-declared multiplicity from observed undeclared duplication, and preserve operator visibility without imposing naive hard process-count limits.

This work order defines a governance contract for runtime-shape declaration and launch-adjacent notice.

## Status

Planning and governance definition only.

This document does not authorize runtime mutation, service restarts, launcher changes, or cleanup by itself.

## Formalization Rule

Observed relevance is not enough to formalize new recurring background behavior.

Any new background, helper, training, counseling, monitoring, or machine-learning surface must be introduced through an explicit launch notice before it is treated as a declared Station activity. Until then, the surface remains provisional even if it is beneficial and within guardrails.

Launch notice should identify:

- the surface or routine name
- purpose and operator-facing value
- cadence or trigger
- owning service or work order
- whether the activity is provisional or formalized

## Scope

This work order governs:

- multiplicity declaration for canonical Station services
- launch notice requirements when additional resident or child surfaces are created
- classification of undeclared multiplicity
- runtime receipts that preserve attributable launch intent
- sunrise and audit expectations for multiplicity-aware validation

This work order applies to:

- services launched by Station sunrise paths
- services launched by governed helper wrappers
- services that may spawn child runtimes, helper workers, or temporary auxiliary processes

This work order does not:

- ban all multi-process designs
- require hard-coded one-PID-per-service assumptions
- authorize process termination
- replace existing topology labeling or normalization work

## Background

Recent runtime observation shows that process duplication is not always simple conflict.

Examples include:

- wrapper-child Python runtime pairs
- duplicate resident launchers
- helper loops started more than once
- services whose hot state may reflect useful work, idle spin, or undeclared churn

Post-hoc classification is useful, but it is insufficient when multiplicity was foreseeable at design time.

If a service is expected to create additional runtime surfaces, that possibility should be declared before or at launch, not inferred only after duplicate observation.

## Relationship to Existing Runtime Governance

This work order is complementary to:

- `WO_RUNTIME_TOPOLOGY_LABELING_V1`
- `WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1`

Topology labeling answers:

- what runtime shape was observed
- which process is the effective runtime

This work order adds:

- what multiplicity was declared in advance
- whether additional runtime surfaces were attributable at launch time
- whether observed multiplicity should be treated as declared, optional, required, or undeclared

## Core Principles

### Declared Multiplicity Beats Surprise Multiplicity

If a service may create additional resident or child runtime surfaces, that possibility should be declared before observation forces reactive interpretation.

### Visibility Without Naive Process Counting

Governance should preserve internal orchestration freedom without collapsing into simplistic rules such as "more than one PID means failure."

### Foreseeable Multiplicity Requires Notice

If a launcher, wrapper, or service is expected to create additional surfaces, launch-adjacent receipts should make that expansion attributable.

### Post-Hoc Classification Still Matters

Observed runtime can still be classified after the fact, but post-hoc legitimacy cannot substitute for a declaration when multiplicity was foreseeable.

### Operator Trust Depends on Runtime Shape Legibility

Creative orchestration is acceptable. Silent runtime shape expansion is not.

## Required Per-Service Multiplicity Declaration

Each canonical service should declare a multiplicity contract that is stable, auditable, and attributable.

Required fields:

- `service_name`
- `topology_class`
- `multiplicity_posture`
- `effective_runtime_rule`
- `additional_surface_kinds`
- `steady_state_multiplicity_expected`
- `temporary_multiplicity_allowed`
- `launch_notice_required`
- `reconciliation_expectation`

### Required Topology Class

Each service should declare an expected topology class such as:

- `single_process`
- `wrapper_child_runtime_pair`
- `bounded_multi_surface_runtime`

This work order does not require only these values forever, but runtime governance must not leave topology class implicit.

### Required Multiplicity Posture

Each service should declare one of:

- `single_instance_only`
- `wrapper_child_expected`
- `bounded_multiplicity_optional`
- `bounded_multiplicity_required`

Meaning:

`single_instance_only`

- one resident runtime surface is expected in steady state
- additional resident surfaces are presumptively anomalous unless separately declared as temporary

`wrapper_child_expected`

- one logical service may legitimately appear as a parent/child pair
- the child or explicitly declared effective runtime remains the authoritative service runtime

`bounded_multiplicity_optional`

- additional helper or auxiliary surfaces may be launched when conditions justify them
- the allowed shape must still be bounded and receipted

`bounded_multiplicity_required`

- more than one resident surface is expected for correct steady-state operation
- the bounded set and runtime roles must be declared

## Launch Notice Requirement

When a service launches an additional resident or child runtime surface, it should emit a pre-launch or launch-adjacent receipt.

This receipt should exist when:

- a wrapper spawns a child runtime
- a service starts an auxiliary worker
- a helper loop is started in addition to a canonical loop
- a temporary reconciliation or recovery process is launched

Required receipt fields:

- `schema_name`
- `schema_version`
- `receipt_type`
- `timestamp_utc`
- `service_name`
- `parent_surface`
- `parent_pid` where observable
- `launch_event_id` or equivalent correlation identifier
- `reason_for_additional_launch`
- `intended_runtime_role`
- `multiplicity_posture`
- `topology_class`
- `steady_state_or_temporary`
- `expected_termination_or_reconciliation_condition`
- `declared_effective_runtime_rule`
- `operator_visibility_class`

Recommended receipt types:

- `runtime.launch_notice`
- `runtime.multiplicity.declared_launch`
- `runtime.auxiliary_surface.started`

## Runtime Role Declaration

The launch-adjacent notice should declare the intended role of the additional surface.

Allowed role examples:

- `launcher_wrapper`
- `effective_service_runtime`
- `runtime_supervisor`
- `auxiliary_worker`
- `temporary_reconciler`
- `health_monitor`
- `transport_child`

This prevents later ambiguity about whether a second process was:

- expected supervision
- useful auxiliary work
- temporary recovery activity
- or accidental duplicate residency

## Steady-State vs Temporary Multiplicity

Every declared additional surface should say whether it is:

- `steady_state`
- `temporary`

If `temporary`, the declaration should include the expected reconciliation condition, such as:

- child exits after handoff completes
- worker exits after backlog drains
- reconciling helper exits after state repair
- temporary monitor exits after verification window

If the additional surface remains resident beyond its declared temporary condition, later runtime classification may escalate concern.

## Classification Rules for Undeclared Multiplicity

If additional runtime surfaces are observed without declared multiplicity or without required launch notice, governance should classify them explicitly.

Primary classes:

- `declared_multiplicity`
- `undeclared_multiplicity`
- `duplicate_but_declared`
- `duplicate_concerning`

Apply `undeclared_multiplicity` when:

- multiplicity was reasonably foreseeable
- the service created additional runtime surfaces
- no declaration or launch-adjacent notice made that multiplicity attributable

Apply `duplicate_concerning` when:

- observed multiplicity is undeclared and materially increases ambiguity, heat, or governance uncertainty
- multiple effective runtimes may exist for one logical service
- duplicate helper loops target the same canonical surface without declared need

Apply `duplicate_but_declared` when:

- multiplicity exists
- the topology and posture declared it
- launch notice attributed the additional surface
- the observed runtime remains within the declared bound

## Post-Hoc Legitimacy Classification

Post-hoc legitimacy classification remains allowed.

Examples:

- `wrapper_child_expected`
- `launcher_wrapper`
- `effective_service_runtime`
- `resource_overhead_expected`
- `resource_overhead_excessive`

However:

- post-hoc legitimacy cannot replace declared multiplicity where multiplicity was foreseeable
- "we can explain it later" is not a substitute for launch-adjacent notice

## Sunrise and Audit Expectations

Sunrise validation and runtime audit should become multiplicity-aware.

Validation should answer:

- did the service declare a topology class
- did the service declare a multiplicity posture
- if additional surfaces appeared, was launch notice emitted
- does the observed runtime remain within the declared multiplicity bound
- is any extra residency steady-state, temporary, or undeclared

Audit should distinguish:

- declared wrapper-child topology
- bounded declared helper multiplicity
- undeclared resident duplication
- duplicate effective runtimes

## Operator Visibility Requirements

Multiplicity declaration should preserve operator visibility without flooding the operator with noise.

Recommended operator-visible distinctions:

- declared steady-state multiplicity
- declared temporary multiplicity
- undeclared multiplicity
- duplicate-concerning runtime

The goal is not to expose every fork or thread.

The goal is to make attributable resident runtime expansion visible when it materially changes Station shape.

## Required Governance Outcomes

This work order expects future runtime governance to support the following outcomes:

- `service_shape.declared_single_instance`
- `service_shape.declared_wrapper_child`
- `service_shape.declared_bounded_optional`
- `service_shape.declared_bounded_required`
- `runtime.multiplicity.within_declared_bound`
- `runtime.multiplicity.temporary_declared`
- `runtime.multiplicity.undeclared`
- `runtime.multiplicity.duplicate_concerning`

## Examples

### Example A: Legitimate Wrapper-Child Pair

Service declaration:

- `topology_class = wrapper_child_runtime_pair`
- `multiplicity_posture = wrapper_child_expected`

Launch notice:

- parent surface launches child runtime
- child is declared `effective_service_runtime`
- pair is `steady_state`

Observed outcome:

- two resident processes
- one logical service
- multiplicity is declared, attributable, and not silently expanded

### Example B: Temporary Backlog Worker

Service declaration:

- `topology_class = bounded_multi_surface_runtime`
- `multiplicity_posture = bounded_multiplicity_optional`

Launch notice:

- additional worker launched because backlog crossed threshold
- worker is temporary
- expected reconciliation condition is backlog drain

Observed outcome:

- additional process is not treated as suspicious duplication if it remains within the declared bound

### Example C: Duplicate Health Loop Without Declaration

Service declaration:

- `multiplicity_posture = single_instance_only`

Observed outcome:

- second helper loop appears
- no launch notice exists
- both loops target the same canonical health surface

Classification:

- `undeclared_multiplicity`
- likely `duplicate_concerning`

## Constraints

Hard constraints:

- no service should silently expand resident runtime shape when multiplicity was foreseeable
- no multiplicity posture should remain implicit for canonical services
- launch-adjacent notice should not be optional where additional resident surfaces are an expected possibility
- post-hoc explanation should not erase prior lack of declaration

Explicit non-goals:

- no naive hard global process-count ceiling
- no blanket ban on child processes
- no automatic termination policy defined by this document

## Desired Outcome

Calyx retains creative internal orchestration.

But Station no longer silently expands runtime shape without attributable notice.

Declared multiplicity remains allowed.

Undeclared multiplicity becomes legible.

Operator trust improves because runtime shape is no longer forced to explain itself only after surprise observation.
