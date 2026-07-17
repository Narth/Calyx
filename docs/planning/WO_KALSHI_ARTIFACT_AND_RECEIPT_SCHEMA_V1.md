---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_KALSHI_ARTIFACT_AND_RECEIPT_SCHEMA_V1

## Status Note

This work order is parked and on hold. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define the canonical artifact and receipt schema contract for Kalshi-related strategy, scoring, and execution-readiness outputs within Station Calyx, so that all Kalshi planning surfaces share one governed, auditable data shape.

### Scope

This work order governs the canonical structure, required fields, classification semantics, and handoff expectations for:

- trade thesis artifacts
- signal scoring receipts
- strategy gate result artifacts
- execution-readiness receipts
- post-resolution review artifacts

This work order applies to all Kalshi-related artifacts emitted under:

- `WO_KALSHI_AGENT_HARNESS_V1`
- `WO_KALSHI_STRATEGY_LAYER_V1`
- `WO_KALSHI_SIGNAL_SCORING_PROFILE_V1`

This work order does not:

- authorize execution
- define exchange transport implementation details
- define wallet policy values
- define strategy weights beyond those already governed elsewhere
- permit schema mutation without explicit governance review

## Section II - Definitions

### `artifact_contract`

The canonical schema boundary that defines what a Kalshi decision artifact must contain and mean.

### `trade_thesis_artifact`

A structured record describing a candidate trade thesis and its reasoning basis.

### `signal_score_record`

A structured scoring receipt for a market candidate under the governed signal profile.

### `strategy_gate_result`

A structured decision artifact expressing abstention, research-only recommendation, or execution-readiness classification.

### `execution_readiness_receipt`

A receipt emitted when a candidate market passes the strategy gate and is eligible for operator review under the harness.

### `post_resolution_review_artifact`

A structured review of how the thesis performed relative to the resolved outcome.

### `canonical_field`

A required field whose meaning is fixed and may not drift across implementations.

### `schema_version`

An explicit version identifier attached to artifacts governed by this work order.

## Section III - Core Principles

### Same Meaning, Same Field

A concept must not be represented by different field names across Kalshi artifacts without governance review.

### Artifacts Must Be Self-Describing

Every artifact must contain enough context to be interpreted without hidden implementation assumptions.

### Receipts Must Reconstruct the Decision Path

A later reviewer must be able to trace how a market moved from scan to score to classification.

### No Semantic Drift Across Layers

Strategy, scoring, and execution-readiness artifacts must use consistent classification language.

### Abstention Must Be First-Class

The schema must represent no-trade outcomes as positively and explicitly as trade-ready outcomes.

### Execution Readiness Is Not Execution Authority

Artifact shape must preserve that distinction at the data-contract level.

### Versioned Stability Before Adaptation

V1 prioritizes stable auditable schema over flexibility.

## Section IV - Required Canonical Artifact Set

The following artifacts and receipts are required for Kalshi v1:

- `trade_thesis_artifact`
- `signal_score_record`
- `strategy_gate_result`
- `execution_readiness_receipt`
- `post_resolution_review_artifact`

### Minimum Lifecycle Expectation

- market observed
- thesis formed or explicitly not formed
- signal scored
- strategy gate classified
- if applicable, execution readiness emitted
- after resolution, post-resolution review recorded

### Constraint

No execution-ready recommendation may exist without a corresponding:

- thesis artifact
- signal score record
- strategy gate result

## Section V - Trade Thesis Artifact Schema Requirements

The `trade_thesis_artifact` must be the canonical reasoning artifact for a candidate trade.

### Required Fields

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `market_title`
- `resolution_rule_summary`
- `proposed_side`
- `price_context`
- `entry_rationale`
- `expected_edge_source`
- `decision_horizon`
- `invalidation_condition`
- `abstention_alternative`
- `evidence_summary`
- `confidence_signal`
- `evidence_signal`
- `operator_engagement_state`

### Field Meaning Requirements

- `proposed_side` must be bounded to governed values such as `yes`, `no`, or `none`
- `decision_horizon` must reflect when the thesis is expected to remain actionable
- `invalidation_condition` must describe what would cause stand-down or re-evaluation
- `abstention_alternative` must state what no-trade outcome would look like if the thesis is not strong enough

### Prohibition

A thesis artifact must not imply execution authority.

## Section VI - Signal Score Record Schema Requirements

The `signal_score_record` must be the canonical scoring receipt for a candidate market.

### Required Fields

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `score_dimensions`
- `composite_score`
- `classification_band`
- `confidence_signal`
- `downgrade_flags`
- `decay_state`
- `evidence_summary`
- `scoring_notes`

### `score_dimensions` Required Subfields

- `evidence_strength`
- `mispricing_potential`
- `timing_quality`
- `resolution_clarity`
- `liquidity_tradability`
- `decision_horizon_fit`
- `risk_clarity`

### `downgrade_flags` Required Semantics

Possible values may include:

- `weak_evidence_relative_to_confidence`
- `ambiguous_resolution`
- `unclear_risk`
- `poor_timing_stability`
- `signal_decay_applied`

### Constraint

Composite score alone must never be treated as sufficient without downgrade evaluation.

## Section VII - Strategy Gate Result and Execution Readiness Schema Requirements

### A. `strategy_gate_result`

This artifact must express the governed decision outcome of strategy evaluation.

### Required Fields

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `gate_outcome`
- `gate_reasons`
- `thesis_ref`
- `score_ref`
- `operator_legibility_status`
- `wallet_policy_fit`
- `presence_requirement`
- `next_allowed_action`

### Allowed `gate_outcome` Values

- `abstain.insufficient_evidence`
- `abstain.low_confidence`
- `abstain.poor_timing`
- `abstain.market_not_suitable`
- `recommend.research_only`
- `recommend.execution_ready_low_confidence`
- `recommend.execution_ready`

### Required Semantic Constraint

`recommend.execution_ready` means strategically coherent and ready for operator review only. It must not imply execution authorization.

### B. `execution_readiness_receipt`

This receipt must be emitted only after a valid `strategy_gate_result` with an execution-ready classification.

### Required Fields

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `execution_readiness_class`
- `thesis_ref`
- `score_ref`
- `gate_result_ref`
- `presence_gate_required`
- `wallet_policy_required`
- `execution_authorized = false`
- `operator_action_required = true`

### Hard Semantic Rule

The receipt must explicitly preserve that execution is still pending operator intent and harness gates.

## Section VIII - Post-Resolution Review Artifact Requirements

The `post_resolution_review_artifact` must be the canonical learning artifact for Kalshi v1.

### Required Fields

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `resolved_outcome`
- `position_taken`
- `entry_context`
- `thesis_summary`
- `score_snapshot`
- `gate_outcome_snapshot`
- `thesis_result`
- `invalidation_observed`
- `decision_quality_assessment`
- `profit_loss_result`
- `attention_cost_estimate`
- `review_notes`

### Required Review Emphasis

The review must evaluate:

- whether the reasoning was sound
- whether abstention would have been better
- whether the score was inflated or conservative
- whether the trade was aligned with policy and strategic edge

### Prohibition

Post-resolution review must not retroactively alter earlier artifacts.

## Section IX - Cross-Artifact Constraints, References, and Canonical Semantics

All Kalshi artifacts under this work order must support traceable linkage.

### Required Cross-Artifact Linking Rules

- every artifact must include `corr_id`
- all downstream artifacts must reference upstream artifacts where applicable
- references must be immutable once emitted
- each artifact must declare `schema_name` and `schema_version`

### Canonical Semantic Requirements

- `confidence_signal` must mean the same thing across thesis, score, and gate artifacts
- `evidence_signal` must not be used interchangeably with `confidence_signal`
- `execution_ready` must never mean `execution_authorized`
- `abstain` classifications must always indicate a valid governed outcome, not an error state

### Naming Constraint

CBO should avoid synonyms that drift meaning, such as:

- `ready_to_trade` for `execution_ready`
- `approved` for `execution_ready`
- `weak_signal` where a formal abstention classification should exist

## Section X - Constraints, Prohibitions, Validation, and V1 Boundaries

### Hard Constraints

- No artifact may omit schema versioning
- No execution-related receipt may exist without upstream strategy artifacts
- No freeform-only artifacts for governed execution handoff
- No hidden fields carrying authority not represented in the canonical schema
- No retroactive mutation of emitted receipts

### Explicit Prohibitions

- semantic drift between planning docs and runtime artifacts
- implementation-specific aliases replacing canonical fields
- collapsing abstention into null or missing-state artifacts
- treating execution readiness as financial approval
- reusing stale score artifacts without explicit re-evaluation state

### Validation Expectations for CBO

CBO should implement schema validation that checks:

- required fields present
- allowed enum values enforced
- cross-artifact references resolvable
- execution readiness never sets `execution_authorized=true`
- downgrade flags preserved where applicable

### V1 Boundary

- static governed schema
- human-auditable JSON-shaped artifacts
- no adaptive schema negotiation
- no self-modifying artifact contract
- single-node, single-operator Kalshi experiment scope

## Implementation Note for CBO

CBO should treat this work order as the canonical meaning boundary for Kalshi runtime artifacts.

The main implementation goal is not just serialization.

It is preservation of governance meaning across the full chain:

`market research -> thesis -> score -> gate result -> execution readiness -> post-resolution review`

If one layer changes language carelessly, the whole Kalshi stack becomes harder to trust.
