---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_RUNTIME_MULTIPLICITY_ENFORCEMENT_AND_VALIDATION_V1

## Purpose and Scope

### Purpose

Define the enforcement and validation framework by which Station Calyx verifies declared runtime multiplicity, emits canonical `runtime.launch_notice` receipts for additional runtime surfaces, and classifies undeclared or noncompliant runtime expansion.

### Scope

This work order governs:

- canonical `runtime.launch_notice` receipt requirements
- per-service multiplicity declaration registry requirements
- sunrise and runtime validation behavior for multiplicity states
- classification of declared, undeclared, and noncompliant duplicate runtime
- posture expectations when runtime shape expands beyond declared contract

This work order is subordinate to:

- `WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1`

This work order applies to governed Station services that may:

- remain single-instance
- operate as wrapper/child pairs
- launch bounded additional resident surfaces
- temporarily expand runtime shape during valid operation

This work order does not:

- require immediate process termination upon every noncompliant state
- impose universal hard numeric limits on service count
- prohibit bounded creative orchestration when declared and attributable
- redefine existing service purpose or runtime roles outside multiplicity governance
- authorize silent multiplicity merely because it was observed previously

## Definitions

### `runtime.launch_notice`

A canonical receipt emitted before or at launch-adjacent time for an additional resident or child runtime surface.

### `multiplicity_declaration_registry`

The governed registry of per-service topology and multiplicity expectations.

### `declared_multiplicity`

Additional runtime shape that is explicitly permitted by the service's topology and multiplicity contract.

### `undeclared_multiplicity`

Additional runtime shape with no governing declaration supporting its existence.

### `multiplicity_noncompliance`

A runtime state where multiplicity is foreseeably allowed but required launch notice, lifecycle, or posture conditions were not met.

### `topology_valid`

A runtime state consistent with declared topology class and multiplicity posture.

### `duplicate_concerning`

A duplicate or extra runtime state that conflicts with single-instance or otherwise constrained expectations.

### `launch_adjacent`

A time boundary sufficiently close to process creation that attribution still truthfully describes intent rather than post-hoc reinterpretation.

### `reconciliation_condition`

The declared condition under which an additional runtime surface should terminate, merge, or return to compliant steady state.

## Core Principles

### Declared Before Trusted

Foreseeable multiplicity must be declared before or at launch, not legitimized only after observation.

### Known Is Not Enough

A process may be known, governed, and still be noncompliant if its multiplicity was not properly declared.

### Validation Before Suppression

The first duty of enforcement is truthful classification, not reflexive termination.

### Multiplicity Must Remain Attributable

Every additional resident or child surface must have a visible reason, role, and lifecycle expectation.

### Topology and Multiplicity Are Distinct

A valid wrapper/child topology does not automatically imply valid duplicate residency or additional peers.

### Post-Hoc Classification Has Limited Authority

Retrospective legitimacy analysis may classify observed runtime, but it must not replace required prior declaration where multiplicity was foreseeable.

### Creative Orchestration Is Allowed, Silent Expansion Is Not

The system may coordinate internal complexity, but it must surface that complexity through governed notice.

## Per-Service Declaration Registry Requirements

Each governed service must declare multiplicity-relevant fields in a canonical registry or equivalent governed declaration surface.

Required per-service fields:

- `service_name`
- `topology_class`
- `multiplicity_posture`
- `expected_runtime_roles`
- `wrapper_child_allowed`
- `duplicate_resident_allowed`
- `launch_notice_required`
- `launch_notice_scope`
- `steady_state_multiplicity_expectation`
- `temporary_expansion_allowed`
- `reconciliation_condition`
- `validation_severity_if_violated`

Allowed `multiplicity_posture` values:

- `single_instance_only`
- `wrapper_child_expected`
- `bounded_multiplicity_optional`
- `bounded_multiplicity_required`

Registry semantic requirements:

- `single_instance_only` means any additional resident duplicate is presumptively concerning
- `wrapper_child_expected` permits the declared pair shape only, not open-ended duplication
- `bounded_multiplicity_optional` permits additional surfaces only when accompanied by valid notice and reconciliation expectation
- `bounded_multiplicity_required` means certain operations legitimately require more than one runtime surface, but still require attributable notice

Hard rule:

Absence of multiplicity declaration must not be interpreted as permissive.

## Canonical `runtime.launch_notice` Receipt Requirements

A `runtime.launch_notice` receipt must be emitted for additional resident or child surfaces whenever multiplicity is not trivially identical to the single-process steady state.

Required receipt fields:

- `schema_name`
- `schema_version`
- `receipt_type`
- `corr_id`
- `timestamp_utc`
- `service_name`
- `declared_by_surface`
- `topology_class`
- `multiplicity_posture`
- `launch_reason`
- `parent_process_identity`
- `child_or_additional_process_identity` if known
- `intended_runtime_role`
- `steady_state_or_temporary`
- `expected_lifecycle`
- `reconciliation_condition`
- `launch_notice_status`

Allowed `launch_notice_status` values:

- `prelaunch_declared`
- `launch_adjacent_declared`
- `retroactive_classification_only`

Semantic rules:

- `retroactive_classification_only` must never count as full compliance where prior notice was foreseeable
- `steady_state_or_temporary` must reflect whether the additional surface is expected to persist or collapse later
- `intended_runtime_role` must distinguish wrapper, child, supervisor, duplicate peer, helper, or other governed runtime role

Constraint:

A `runtime.launch_notice` receipt provides attribution and declaration. It does not by itself authorize unsafe or otherwise prohibited runtime expansion.

## Sunrise and Runtime Validation Behavior

Multiplicity validation must occur both at startup posture assessment and during runtime observation.

### A. Sunrise Validation

At sunrise or equivalent startup posture check, the station must evaluate:

- declared services expected to be present
- observed runtime topology
- multiplicity compliance against registry
- presence or absence of required launch notices

Required sunrise outcomes include:

- `topology_valid`
- `multiplicity_declared_and_compliant`
- `multiplicity_declared_but_noncompliant`
- `undeclared_multiplicity`
- `duplicate_concerning`

### B. Runtime Validation

During runtime, the station must observe whether new additional surfaces emerge and whether they remain aligned with declaration.

Runtime validation checks should include:

- process lineage where observable
- role consistency with declared topology
- receipt presence for newly expanded runtime shape
- reconciliation behavior for temporary surfaces
- persistence of duplicate states beyond declared expectations

Hard rule:

A service that transitions from compliant single-instance posture into expanded runtime shape must become visible through validation artifacts, not merely through later operator inspection.

## Multiplicity Classification Outcomes and Posture

The system must classify multiplicity states explicitly and deterministically.

Required classification states:

### `topology_valid`

Observed runtime shape matches declared topology and posture.

### `multiplicity_declared_and_compliant`

Additional runtime surfaces exist and are properly declared with valid notice.

### `multiplicity_declared_but_noncompliant`

Multiplicity was contractually foreseeable, but receipt, lifecycle, or reconciliation conditions were not met.

### `undeclared_multiplicity`

Additional runtime surfaces exist with no declaration basis.

### `duplicate_concerning`

Observed duplication conflicts with service contract or creates unsafe ambiguity.

Posture expectations by class:

- `topology_valid`
  - no escalation required
- `multiplicity_declared_and_compliant`
  - allowed, observable, receipt-backed
- `multiplicity_declared_but_noncompliant`
  - allowed to exist temporarily for observation, but posture should degrade or warn
- `undeclared_multiplicity`
  - posture should visibly reflect governance concern
- `duplicate_concerning`
  - posture should visibly reflect stronger governance concern and may affect future launch eligibility or operator review requirements

Constraint:

Classification must remain distinct from immediate remediation action.

## Enforcement Posture and Escalation Rules

This work order governs validation and posture first, with bounded escalation behavior.

Primary enforcement sequence:

- observe
- classify
- emit validation artifact or receipt
- surface posture impact
- optionally gate future launches or require operator review

Allowed enforcement consequences in v1:

- warning posture
- degraded trust posture
- sunrise noncompliance classification
- launch eligibility warning for future runs
- explicit operator review requirement before continued expansion is treated as acceptable

Disallowed by default in v1 unless separately authorized:

- automatic killing of observed duplicate processes
- automatic restart churn to "fix" topology
- silent deduplication
- silent normalization of undeclared multiplicity into compliant state

Escalation guidance:

Repeated occurrences of:

- `undeclared_multiplicity`
- `duplicate_concerning`

across sunrise, restart, or recurring runtime windows should increase severity and reduce tolerance for treating the state as observationally benign.

## Receipts, Validation Artifacts, and Review Expectations

Multiplicity enforcement must remain receipt-backed and reconstructable.

Required receipt or artifact classes may include:

- `runtime.launch_notice`
- `runtime.multiplicity.validation`
- `runtime.multiplicity.noncompliance`
- `runtime.multiplicity.undeclared`
- `runtime.multiplicity.reconciled`

Required validation artifact content:

- service identity
- observed process identities
- declared topology and multiplicity contract
- receipt presence or absence
- classification outcome
- posture consequence
- reconciliation expectation if applicable
- timestamp and correlation context

Review expectations:

A reviewer must be able to determine:

- what runtime shape appeared
- whether it was declared
- whether it was compliant
- whether it persisted beyond expectation
- whether post-hoc legitimacy was wrongly being used as a substitute for prior declaration

Hard rule:

No repeated duplicate state should remain merely anecdotal if it is recurrent enough to become a stable Station behavior.

## Constraints, Prohibitions, Validation Expectations, and V1 Boundaries

Hard constraints:

- no service may silently expand runtime shape where multiplicity was foreseeable
- no missing declaration may be interpreted as implicit permission
- no post-hoc legitimacy classification may fully substitute for absent launch notice when notice was required
- no enforcement logic may collapse multiplicity classification into immediate kill/restart behavior by default
- no creative orchestration claim may override the need for attributable runtime expansion

Explicit prohibitions:

- declaring duplicate runtime legitimate only because it has happened before
- treating wrapper/child legitimacy as blanket permission for duplicate peers
- silently carrying noncompliant duplicate states across sunrise without visible classification
- using runtime ambiguity as cover for missing declaration discipline
- mutating a service contract after observation merely to make observed runtime appear compliant

Validation expectations for CBO:

CBO should validate that:

- every governed service has multiplicity registry fields
- required `runtime.launch_notice` receipts are schema-valid
- sunrise checks can distinguish compliant from undeclared multiplicity
- runtime validation can identify declared-but-noncompliant states
- repeated duplicate states produce visible severity rather than normalization
- process topology and multiplicity are assessed separately where required

V1 boundary:

- classification-first enforcement
- receipt-backed visibility
- no universal hard process-count caps
- no automatic destructive remediation by default
- preservation of creative internal orchestration, provided it is declared and attributable

## Implementation Note for CBO

CBO should treat this work order as the transition from:

"we can explain duplicate runtime after the fact"

to

"the station must know when extra runtime shape belongs before or as it appears."

The aim is not to suppress complexity.

It is to ensure that complexity arrives with:

- declared shape
- declared reason
- declared lifecycle
- visible governance posture

That is what turns multiplicity from ambiguity into attributable structure.
