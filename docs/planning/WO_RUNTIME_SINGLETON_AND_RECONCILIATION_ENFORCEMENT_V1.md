---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_RUNTIME_SINGLETON_AND_RECONCILIATION_ENFORCEMENT_V1

## Section I — Purpose And Scope

### Purpose

Establish a governed runtime discipline for steady-state Station surfaces that must not accumulate duplicate residency.

This work order exists to:

- prevent repeated launches from silently multiplying equivalent runtime surfaces
- require runtime reconciliation before a new instance is permitted to become resident
- preserve declared multiplicity where explicitly authorized
- fail-close undeclared or excess duplication

### Scope

This work order applies to long-running or repeating Station runtime surfaces, especially:

- `station_health_loop`
- `bridge_overseer`
- `navigator_triage_loop`
- `cp6_cp7_loop`
- `energy_churn_cp9_loop`
- `service_failure_watch`
- `cli_avatar`

This work order applies to:

- launch surfaces
- wrapper launches
- scheduler launches
- manual or operator-triggered launches

This work order governs:

- runtime residency
- runtime reconciliation

This work order does not itself authorize destructive remediation behavior without separate approval.

## Section II — Problem Statement

Current Station runtime behavior indicates multiplicity drift rather than disciplined declared multiplicity.

Observed issues include:

- repeated residency of equivalent long-running loops
- duplicate wrapper/child pairs accumulating across repeated launches
- idle surfaces continuing to consume workstation resources
- host-process ambiguity preventing safe manual operator intervention
- lack of a canonical pre-launch reconciliation step

This causes:

- sustained workstation CPU pressure
- governance ambiguity
- operator uncertainty
- loss of steady-state restraint

The immediate issue is not code duplication.

It is runtime residency duplication without bounded authority.

## Section III — Governance Intent

The system must move from:

`launch when requested`

to:

`reconcile before launch, then permit only declared runtime shape`

The intended posture is:

- singleton by default
- multiplicity only when explicitly declared
- reconciliation before new residency
- visibility before correction
- authority before launch

## Section IV — Definitions

### singleton service

A runtime surface declared to allow only one active resident instance or one logical wrapper-child runtime pair.

### declared multiplicity

A governance-approved runtime posture explicitly allowing more than one resident instance or pair.

### runtime reconciliation

A pre-launch evaluation that compares the requested launch against already-resident processes and declared service posture.

### equivalent resident

An already-running process or wrapper-child runtime pair that satisfies the same logical Station service role as the requested launch.

### launch refusal

A governed decision to deny new residency because an equivalent resident already exists and declared multiplicity does not permit expansion.

### reconciliation receipt

A receipt emitted before launch decision that records observed equivalent runtime, declared posture, and resulting disposition.

### host-process ambiguity

A condition where OS-visible process identity is insufficient to distinguish which Station script or loop is being hosted.

## Section V — Required Behavior

For every governed launch surface targeting an eligible long-running runtime, the system must:

- perform pre-launch reconciliation
- identify:
  - existing equivalent residents
  - declared multiplicity posture
  - wrapper/child topology if applicable
- emit reconciliation result before allowing launch

Allowed outcomes:

- `permit_new_launch`
- `refuse_duplicate_launch`
- `attach_to_existing_runtime`
- `permit_declared_multiplicity`
- `ambiguous_runtime_blocked`

Default rule:

If multiplicity is not explicitly declared, equivalent runtime duplication must fail closed.

## Section VI — Service Posture Requirement

Each governed long-running service must declare one of the following:

- `single_instance_only`
- `single_wrapper_child_pair_only`
- `bounded_multi_instance`
- `bounded_multi_pair`
- `unclassified_no_launch_without_review`

For each service, the declaration must include:

- logical service name
- expected topology class
- permitted multiplicity count
- matching criteria for equivalence
- whether manual override is ever allowed

No service may remain launchable indefinitely under implicit multiplicity assumptions.

## Section VII — Reconciliation Logic Requirements

The reconciliation layer must:

- inspect active runtime prior to launch
- compare requested launch against known service declarations
- use deterministic equivalence rules based on available evidence such as:
  - command line
  - script path
  - parent/child relation
  - declared service label
  - owned ports where relevant
- fail closed when service identity cannot be safely distinguished

The reconciliation layer must not:

- silently ignore existing residents
- silently normalize duplicates after launch
- invent equivalence without evidence
- auto-kill existing processes under this work order alone

## Section VIII — Required Artifacts And Receipts

Implement schema-backed artifacts for at minimum:

### `runtime.reconciliation.request`

Fields should include:

- requested launch identity
- initiating launcher
- declared service target

### `runtime.reconciliation.result`

Fields should include:

- observed equivalent residents
- declared multiplicity posture
- topology comparison
- disposition result

### `runtime.duplicate.runtime_detected`

Emitted when undeclared equivalent residents already exist.

### `runtime.launch.refused`

Emitted when launch is blocked due to duplicate or ambiguous runtime.

### `runtime.runtime_identity_marker`

Optional artifact or launch marker to improve host-process attribution for long-running services.

All receipts must preserve:

- timestamp
- launcher identity
- operator vs scheduler origin
- evidence references
- non-authorizing status where applicable

## Section IX — Operator Visibility Requirements

The operator must be able to answer, without guessing:

- what logical Station services are currently resident
- how many instances of each are active
- which are singleton-compliant
- which are duplicate or noncompliant
- which OS host processes correspond to which Station loops or services

This work order therefore authorizes planning and staging work for:

- process-to-service attribution improvement
- operator-readable duplication summaries
- host-process identity enhancement for PowerShell-hosted scripts

The system should not rely on Task Manager alone for safe intervention.

## Section X — Failure Posture

Duplicate runtime accumulation must become a first-class failure condition, not a tolerated background state.

Failure classes should include:

- `singleton_violation`
- `undeclared_multiplicity`
- `duplicate_wrapper_child_pair`
- `runtime_identity_ambiguous`
- `launch_reconciliation_missing`

These failures should be:

- visible
- receipt-backed
- attributable
- non-silent

They should not automatically imply process termination or liveness loss.

## Section XI — Non-Authorized Actions

This work order does not authorize:

- automatic process termination
- automatic duplicate cleanup
- hidden runtime replacement
- silent attachment to unrelated resident processes
- post-hoc legitimation of already-duplicated runtime

Any destructive or remediating action requires separate approval.

## Section XII — Staging Implementation Target

CBO is authorized to implement, in staging only:

- service declaration models for singleton and bounded multiplicity posture
- reconciliation request/result artifacts
- equivalence and ambiguity classification logic
- duplicate detection fixtures
- operator-readable duplication summaries
- tests covering:
  - singleton refusal
  - declared bounded multiplicity
  - wrapper-child equivalence
  - ambiguous host-process block
  - undeclared duplicate detection

No live runtime mutation or kill behavior is authorized in this phase.

## Section XIII — Success Criteria

This work order is successful when:

- repeated launches of singleton services are refused or attached rather than duplicated
- equivalent long-running services become attributable before launch
- duplicate runtime becomes visible as a first-class failure
- operator can distinguish logical Station services even when OS host processes are ambiguous
- staging tests prove reconciliation works without runtime mutation

## Section XIV — Intent Confirmation

The purpose of this work order is not to make Station more active.

It is to make Station more restrained.

The system must prove that it can:

- recognize what is already alive
- refuse unnecessary new residency
- preserve declared multiplicity only where intentionally authorized
- stop treating repeated launches as harmless

This work order exists to restore coexistence between Station Calyx and the workstation it inhabits.
