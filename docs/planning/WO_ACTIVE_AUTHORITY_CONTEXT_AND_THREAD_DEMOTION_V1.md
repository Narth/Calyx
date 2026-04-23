---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# WO_ACTIVE_AUTHORITY_CONTEXT_AND_THREAD_DEMOTION_V1

## Section I - Purpose And Scope

### Purpose

Establish a governed mechanism to:

- separate historical thread context from current operational authority
- prevent completed or superseded directives from influencing active execution
- ensure reasoning and action are grounded in current Station truth and current governing context

This work order exists to eliminate:

- stale intent anchoring
- implicit directive carryover
- misalignment between past prompts and present operations

### Scope

This work order governs:

- definition of Active Authority Context (`AAC`)
- classification of thread-origin directives
- demotion rules for satisfied or superseded objectives
- integration with intake, mediation, reasoning, and execution planning

This work order does not:

- redefine Work Envelope authority
- replace the canonical Calyx spine
- alter execution permissions by itself
- suppress historical traceability

## Section II - Core Principle

At any point in time:

Only Active Authority Context defines what is currently governing, relevant, and actionable.

All other context is:

- historical
- referential
- non-authoritative

Historical context may inform interpretation.

Historical context must not silently govern action once it is no longer active.

## Section III - Definitions

### `thread_origin_objective`

The directive or intent that initiated the conversation thread.

### `objective_state`

One of:

- `active`
- `satisfied`
- `superseded`
- `abandoned`

### `active_authority_context`

The current governing frame derived from:

- current Station truth surfaces
- latest receipts and runtime evidence
- active Work Envelope, if present
- current operation phase
- latest completed work orders materially relevant to the current task

### `thread_demotion`

The act of reclassifying a `thread_origin_objective` from governing to historical.

### `historical_context`

Prior prompts, satisfied directives, superseded plans, and no-longer-governing narrative context retained for traceability only.

## Section IV - Required Behavior

### FR-1: Objective State Evaluation

At the beginning of any reasoning cycle, the system must determine:

`thread_origin_objective -> objective_state`

Minimum evaluation rules:

- if the originating task is completed -> `satisfied`
- if the originating task has been replaced by a newer directive -> `superseded`
- if the originating task is no longer relevant and no longer governs present work -> `abandoned`
- otherwise -> `active`

This evaluation must happen before current action planning.

### FR-2: Thread Demotion Enforcement

If:

`objective_state` is one of:

- `satisfied`
- `superseded`
- `abandoned`

Then:

- the `thread_origin_objective` must be demoted
- it must not drive reasoning
- it must not justify actions
- it must not constrain new operations by continuity alone

After demotion, the original objective may only be used for:

- traceability
- historical reference
- explanation of how the thread arrived at its current state

### FR-3: Active Authority Context Construction

AAC must be explicitly derived from currently authoritative sources.

Required derivation inputs:

- `STATE.md`
- runtime truth surfaces
- runtime topology
- relevant receipts
- active Work Envelope, if present
- active operation being performed
- recently completed work orders that materially shape the current operation

AAC must be internally established before output is produced or execution is planned.

### FR-4: Reasoning Grounding Rule

All reasoning and output must be grounded in:

`active_authority_context`

and not in:

- demoted `thread_origin_objective`
- stale continuity assumptions
- narrative carryover unsupported by current authority

### FR-5: Justification Constraint

The system must not:

- justify current actions using demoted objectives
- reference completed directives as if they were active requirements
- preserve legacy goals as governing merely for continuity

## Section V - Active Authority Context Model

Minimum internal AAC structure for planning purposes:

```text
active_authority_context = {
  thread_origin_objective,
  objective_state,
  current_operation,
  station_truth_inputs,
  governing_artifacts,
  active_work_envelope_ref,
  latest_completed_wo_refs,
  authority_basis_summary
}
```

Minimum field meanings:

- `thread_origin_objective`: the original thread-starting directive
- `objective_state`: current status of that directive
- `current_operation`: the task presently governing work
- `station_truth_inputs`: current runtime/state evidence used
- `governing_artifacts`: current docs, receipts, and WOs shaping authority
- `active_work_envelope_ref`: active Work Envelope if present, otherwise empty
- `latest_completed_wo_refs`: recent completed WOs relevant to the current task
- `authority_basis_summary`: concise statement of what currently governs

## Section VI - Optional Operator Visibility (V1 Light)

AAC does not need to be surfaced in every response.

However, it must be available for:

- audits
- debugging
- governance review

Optional visible form:

```text
Active Authority Context:
- objective_state: satisfied
- current_authority: swarm infrastructure planning
```

This visibility is advisory in v1 and does not replace the internal requirement to establish AAC before reasoning.

## Section VII - Integration Points

AAC must integrate with:

### A. Intake / Mediation Layer

Before Work Envelope creation, the system must determine whether the current task is governed by:

- a still-active originating objective
- or a newer current operation

### B. CBO Reasoning Loop

Before execution planning or artifact drafting, the system must establish AAC and demote stale thread authority if required.

### C. Swarm Orchestration (Future)

Before worker decomposition, the orchestrator must ensure worker planning is grounded in current authority rather than stale thread narrative.

### D. Execution Gating

Current execution must be attributable to current governing authority, not to historical prompts that are no longer active.

## Section VIII - Failure Modes

The system must detect and avoid:

### `stale_directive_anchoring`

Continuing to reason as if a completed directive still governs current action.

### `mixed_authority_state`

Combining old and new directives as though both are active without explicit authority resolution.

### `continuity_bias`

Preserving thread narrative over correctness, current state, or current operation.

### `silent_supersession`

Allowing a new operation to replace an old one without explicitly recognizing the replacement.

### `legacy_justification_reuse`

Using a demoted directive to justify actions that belong to a newer active task.

## Section IX - Receipts, Auditability, And Staging

Recommended future receipt path:

`runtime/receipts/governance/active_authority_context__YYYYMMDD_HHMMSS.json`

Recommended receipt fields:

- `thread_origin_objective`
- `evaluated_objective_state`
- `current_operation`
- `derived_aac_components`
- `governing_artifacts`
- `active_work_envelope_ref`
- `authority_basis_summary`

Staging plan:

### Phase 0 - Concept Enforcement

Reasoning-level implementation only.

No file outputs required.

### Phase 1 - Lightweight Visibility

Optional AAC summary may be surfaced for audits and debugging.

### Phase 2 - Receipt Emission

Structured AAC receipts emitted for governance review.

### Phase 3 - Full Integration

AAC enforced across:

- intake
- mediation
- swarm orchestration
- execution gating

## Section X - Success Criteria And Intent Confirmation

This work order is successful when:

- completed directives no longer influence active reasoning
- current actions are grounded in present authority only
- thread continuity no longer overrides correctness
- operator can distinguish:
  - what was asked
  - what is done
  - what is currently governing

Intent confirmation:

This work order does not reduce context.

It refines context into:

- what matters now
- what mattered before

It ensures Station Calyx behaves as a time-aware governed system rather than a narrative continuation engine.
