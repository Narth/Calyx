---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_BRIDGE_OVERSEER_IDLE_MODE_AND_MULTIPLICITY_NORMALIZATION_V1

## Purpose

Define a governed optimization and normalization plan for `bridge_overseer` that reduces low-value empty-pulse residency, preserves truthful visibility into idle bridge state, and normalizes multiplicity so only declared and attributable runtime shape remains acceptable.

## Status

Planning and governance definition only.

This document does not authorize process cleanup, restart, topology mutation, or heartbeat changes by itself.

## Formalization Rule

Background or guardrail-compatible activity is not considered formalized merely because it is relevant or observed in practice.

Before new recurring bridge or background activity becomes part of the Station contract, it must:

- be declared explicitly
- be announced to the operator before or at introduction
- be attributable to a named Station surface or work order
- remain reversible until the operator accepts it as formalized

This rule applies to bridge idle behavior, multiplicity handling, and adjacent expansions such as future AI-4-All training or counseling routines.

## Scope

This work order governs:

- idle or empty-work behavior for `calyx.cbo.bridge_overseer`
- multiplicity normalization for duplicated overseer residency
- distinction between active bridge work and empty pulse churn
- design expectations for lower-cost pulse behavior when no objectives are present
- preservation of truthful bridge observability

This work order applies to:

- `calyx\cbo\bridge_overseer.py`
- `metrics\bridge_pulse.csv`
- objective-source and bridge runtime inputs used by the overseer
- runtime topology and multiplicity classification for the overseer surface

This work order does not:

- remove bridge observability
- authorize live bridge execution expansion
- reassign bridge governance authority
- silently normalize duplicate overseer residency into legitimacy

## Background

Recent read-only assessment identified `bridge_overseer` as the secondary low-value churn target.

Observed conditions:

- multiple resident `bridge_overseer` wrapper/child pairs are currently present
- existing governance receipts already classify the runtime shape as duplicate non-listener pairs
- recent `bridge_pulse.csv` rows repeatedly show:
  - `objectives=0`
  - `tasks=0`
  - `dispatched=0`
- downstream pulse evidence appears stale or absent relative to active work expectations
- current bridge cost appears more attributable to idle pulse residency and multiplicity drift than to useful live workload

The optimization target is therefore not “make the bridge aggressive.”

It is “make idle bridge state cheaper, more attributable, and less duplicative.”

## Relationship to Existing Governance

This work order is complementary to:

- `WO_RUNTIME_TOPOLOGY_LABELING_V1`
- `WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1`
- `WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1`
- `WO_RUNTIME_MULTIPLICITY_ENFORCEMENT_AND_VALIDATION_V1`

It also depends on existing runtime evidence that treats `bridge_overseer` as a governed Station surface rather than arbitrary background Python.

## Core Principles

### Idle Visibility Must Remain Truthful

An empty bridge state should still be visible.

But visibility does not require paying the full cost of active orchestration when no work exists.

### One Authoritative Overseer by Default

`bridge_overseer` should not silently expand into multiple resident peer overseers unless multiplicity is explicitly declared and receipted.

### Empty Work Should Be Cheap

When there are no objectives, no tasks, and no dispatches, the bridge should prefer a reduced-cost idle posture over a full active cycle.

### Multiplicity and Utility Must Be Assessed Separately

A wrapper/child runtime pair may be topology-legitimate while still being:

- noncompliant
- low-value
- or duplicative at the service level

### No Silent Backoff Semantics

If idle behavior changes cadence or residency posture, the change should remain observable and attributable.

## Current Utility Distinction

Future optimization should preserve a clear distinction between:

### Active Bridge Work

Bridge pulses where at least one of the following is true:

- objectives are present
- plans are built for real work
- dispatches occur
- coordinator or governance action materially processes current work

### Idle Bridge State

Bridge pulses where:

- no objectives are present
- no tasks are planned
- no dispatches occur
- the pulse primarily confirms continued emptiness

This distinction should become explicit in runtime behavior and receipts.

## Current Churn Drivers

The current bridge loop performs a broad orchestration path that includes:

- sensor snapshot
- objective loading
- TES summary calculation
- planning
- governance evaluation
- optional dispatch
- feedback evaluation
- optional coordinator pulse
- metrics logging

When real work exists, this is justified.

When `objectives=0 tasks=0 dispatched=0` repeatedly persists, the same path can become low-value churn.

## Required Design Outcomes

Any future implementation shaped by this work order should satisfy all of the following:

- one authoritative overseer in steady state unless multiplicity is explicitly declared
- duplicate overseer launch becomes visible through multiplicity governance
- idle bridge pulses become cheaper than active pulses
- idle visibility remains reconstructable from receipts or metrics
- no silent drift from declared topology or multiplicity posture

## Multiplicity Normalization Requirements

`bridge_overseer` should not rely on post-hoc explanation alone for its runtime shape.

### Required Future Multiplicity Posture

The bridge surface should explicitly declare one of:

- `wrapper_child_expected`
- or `single_instance_only`

If wrapper/child topology is retained, one process must still be declared the authoritative runtime role.

### Duplicate Peer Prohibition

A valid wrapper/child topology must not be treated as blanket permission for:

- multiple overseer pairs
- multiple effective peer overseers
- layered duplicate idle loops

### Required Duplicate-Launch Outcome

If a second overseer instance or pair is launched without declaration:

- emit multiplicity validation or launch notice receipt
- classify as `undeclared_multiplicity` or `duplicate_concerning`
- do not silently convert the extra overseer into accepted steady-state behavior

## Idle Mode Design Requirements

Future `bridge_overseer` design should support an explicit lower-cost idle mode.

### Idle Mode Entry Conditions

Acceptable signals for entering idle mode may include:

- no objectives file present
- objectives source exists but is empty
- no planned tasks
- no dispatchable work after governance screening

### Idle Mode Expectations

Idle mode should:

- preserve pulse visibility
- record that no work was present
- avoid expensive active-work paths when they are not needed
- remain reversible as soon as work appears

### Acceptable Idle Mode Behaviors

Planning-acceptable behaviors include:

- objective-first short-circuit before full sensor and planning work
- reduced sensor set for idle pulses
- smaller metrics payload for idle pulses
- bounded idle cadence backoff if receipted and legible

## Empty-Pulse Reduction Requirements

The system should reduce cost on pulses that are materially empty.

### Preferred Empty-Pulse Strategy

A future implementation should prefer:

- detect no-objective state early
- produce a truthful idle pulse artifact
- skip or reduce expensive active-work components

### Optional Idle Backoff

Bounded idle backoff is acceptable only if:

- it is explicitly represented in receipts or metrics
- it has a declared ceiling
- it immediately collapses back to normal cadence when work appears

Unacceptable behavior:

- hidden cadence drift
- idle slowdown that is not observable to later review

## Observability and Metrics Requirements

Bridge optimization must preserve truthful visibility into what the loop was doing.

Future metrics or receipts should make it possible to distinguish:

- active pulse
- idle pulse
- idle pulse with no objectives source
- idle pulse with empty objectives source
- idle pulse running under backoff

The purpose is not more noise.

The purpose is to prevent cheap idle mode from becoming silent ambiguity.

## Validation Expectations

Any future implementation based on this work order should be validated against:

- lower steady-state CPU cost when bridge work is empty
- unchanged or improved visibility into idle bridge state
- duplicate overseer launch classification
- no loss of observability when work resumes
- no hidden multiplicity normalization

Validation should explicitly test:

- empty objectives file absent
- empty objectives file present
- non-empty objectives
- duplicate launch attempt
- wrapper/child topology with one authoritative runtime

## Constraints

Hard constraints:

- no duplicate overseer normalization without declaration
- no optimization that hides idle state by simply stopping visibility
- no cadence backoff that lacks explicit meaning
- no active-work semantics lost when real objectives appear

Explicit prohibitions:

- treating repeated empty pulses as sufficient justification for silent duplicate residency
- treating wrapper/child legitimacy as permission for duplicate peer overseers
- collapsing active and idle pulses into the same unqualified metric meaning
- normalizing low-value idle churn merely because it is not listener-conflicting

## Preferred Phase Order

### Phase 1

Declare overseer topology class, multiplicity posture, and authoritative runtime rule.

### Phase 2

Normalize duplicate overseer residency through multiplicity validation design.

### Phase 3

Introduce explicit idle mode with truthful idle pulse semantics.

### Phase 4

Add bounded, observable empty-pulse reduction behavior.

### Phase 5

Measure cost reduction and confirm active-work behavior remains intact.

## Desired Outcome

`bridge_overseer` remains a governed Station surface.

But when no bridge work exists, it should behave like an honest idle overseer:

- visible
- attributable
- cheaper than active operation
- and no longer silently duplicated.
