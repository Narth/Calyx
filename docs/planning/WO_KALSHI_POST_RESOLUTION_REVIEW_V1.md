---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_KALSHI_POST_RESOLUTION_REVIEW_V1

## Status Note

This work order is parked and on hold. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define the governed post-resolution review process for Kalshi-related market evaluations and trades, so that Station Calyx can assess decision quality, thesis quality, scoring quality, and policy alignment after a market resolves.

### Scope

This work order governs post-resolution review for:

- abstained candidate markets that were materially considered
- research-only recommendations
- execution-ready recommendations
- executed trades placed through the governed Kalshi harness

This work order applies to artifacts and receipts produced under:

- `WO_KALSHI_AGENT_HARNESS_V1`
- `WO_KALSHI_STRATEGY_LAYER_V1`
- `WO_KALSHI_SIGNAL_SCORING_PROFILE_V1`
- `WO_KALSHI_ARTIFACT_AND_RECEIPT_SCHEMA_V1`

This work order does not:

- authorize retroactive mutation of prior artifacts
- authorize automatic strategy drift or scoring changes
- treat profit alone as proof of good reasoning
- treat loss alone as proof of bad reasoning
- redefine earlier operator intent or execution authority

## Section II - Definitions

### `post_resolution_review`

A governed retrospective assessment performed after a Kalshi market reaches resolution.

### `decision_quality`

The quality of the reasoning and governance process independent of final profit or loss.

### `outcome_quality`

The realized market result, including whether the trade won, lost, or was avoided.

### `thesis_quality`

The degree to which the original thesis was coherent, evidence-backed, legible, and properly invalidatable.

### `score_quality`

The degree to which signal scoring accurately reflected the true strength and weakness of the candidate.

### `variance_assist`

A situation in which a trade succeeded despite weak reasoning or inflated confidence.

### `variance_penalty`

A situation in which a trade failed despite generally sound reasoning and disciplined entry logic.

### `abstention_quality`

The degree to which a no-trade outcome was the correct governed choice.

### `review_artifact`

The canonical post-resolution record describing what happened and what should be learned from it.

## Section III - Core Principles

### Reasoning Must Be Judged Separately from Outcome

A winning trade can still be poorly reasoned. A losing trade can still be well reasoned.

### Abstention Must Be Reviewable

No-trade decisions must be evaluated as seriously as executed trades.

### No Retroactive Self-Flattery

The system must not reinterpret vague earlier signals as stronger than they were.

### No Retroactive Self-Condemnation

A loss must not erase evidence that the process was disciplined and sound.

### Learning Must Be Receipt-Bound

Review conclusions must be grounded in previously emitted artifacts, not reconstructed from memory.

### Variance Must Be Named Explicitly

Luck, timing rescue, and accidental wins must not be confused with true edge.

### Governance Quality Matters

The review must assess not only strategy correctness, but also whether Station behavior remained within authorized boundaries.

## Section IV - Review Eligibility and Required Coverage

A post-resolution review must be created for any Kalshi candidate that reaches one of the following thresholds:

- a thesis artifact was formed
- a signal score record was emitted
- a strategy gate result was emitted
- an execution-readiness receipt was emitted
- a trade was executed

### Coverage Requirements

#### Executed Trades

Always require full post-resolution review.

#### Execution-Ready but Not Executed Candidates

Require review when they were materially considered and later resolved.

#### Research-Only Recommendations

Require review when they are relevant to strategy calibration.

#### Abstentions

Require review when the abstention reflected a meaningful decision boundary rather than trivial dismissal.

### V1 Guidance

CBO should prefer over-review to under-review for materially considered markets.

## Section V - Required Inputs and Source Artifacts

Every post-resolution review must be grounded in the canonical upstream artifacts.

### Required Input References Where Available

- `trade_thesis_artifact`
- `signal_score_record`
- `strategy_gate_result`
- `execution_readiness_receipt`
- execution attempt, success, or failure receipts
- market resolution result
- operator action record, if execution occurred

### Review Integrity Requirements

- All referenced artifacts must remain immutable
- Review must cite the original score and classification, not a reconstructed version
- Missing upstream artifacts must be explicitly called out as review gaps

### Prohibition

The review process must not fill in missing earlier discipline with post-hoc assumptions.

## Section VI - Review Dimensions and Assessment Questions

Each post-resolution review must evaluate the candidate or trade across the following dimensions.

### 1. Thesis Quality

- Was the thesis clear, legible, and evidence-backed?
- Did it identify a real proposed edge?
- Was the invalidation condition meaningful?

### 2. Signal Score Quality

- Did the score reflect the actual strength of the setup?
- Were downgrade flags appropriate?
- Was confidence properly calibrated to evidence?

### 3. Timing Quality

- Was the entry timing sound?
- Did the thesis remain valid across the decision horizon?
- Did late entry or premature entry distort the result?

### 4. Market Fit Quality

- Was the market suitable for v1 strategy posture?
- Were liquidity, tradability, and resolution clarity handled correctly?

### 5. Governance Quality

- Did the system remain within presence, authority, and policy boundaries?
- Was execution properly separated from readiness?

### 6. Outcome Interpretation

- Did the final result validate the reasoning, or merely coincide with it?
- Was the outcome materially driven by sound edge, variance, or timing accident?

### 7. Abstention Quality

- If no trade was taken, was abstention the better governed outcome?
- Did abstention preserve capital against a weak or noisy setup?

## Section VII - Required Review Outcomes and Classification Bands

Each review must produce explicit governed classifications.

### Decision Quality Classifications

- `decision_quality.strong`
- `decision_quality.acceptable`
- `decision_quality.weak`
- `decision_quality.unsound`

### Outcome Interpretation Classifications

- `outcome.validated_edge`
- `outcome.partial_validation`
- `outcome.variance_assist`
- `outcome.variance_penalty`
- `outcome.false_positive_signal`
- `outcome.correct_abstention`
- `outcome.missed_opportunity_but_valid_abstention`

### Policy Alignment Classifications

- `policy.aligned`
- `policy.minor_drift_observed`
- `policy.review_gap_observed`
- `policy.misaligned`

### Constraint

A profitable outcome must still be allowed to classify as `decision_quality.weak` or `outcome.variance_assist` where warranted.

## Section VIII - Required Review Artifact Schema Content

The post-resolution review artifact must include at minimum:

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `timestamp_utc`
- `market_id`
- `market_title`
- `resolved_outcome`
- `position_taken`
- `trade_executed`
- `thesis_ref`
- `score_ref`
- `gate_result_ref`
- `execution_ref`
- `original_composite_score`
- `original_gate_outcome`
- `thesis_quality_assessment`
- `score_quality_assessment`
- `timing_quality_assessment`
- `governance_quality_assessment`
- `decision_quality_classification`
- `outcome_interpretation_classification`
- `policy_alignment_classification`
- `profit_loss_result`
- `attention_cost_estimate`
- `abstention_counterfactual`
- `review_notes`
- `recommended_followup`

### `recommended_followup` Allowed V1 Shapes

- `none`
- `watch_for_pattern`
- `review_signal_thresholds`
- `review_market_selection`
- `review_timing_logic`
- `review_confidence_calibration`
- `review_artifact_completeness`

## Section IX - Learning Boundaries and Governance Constraints

The post-resolution review may inform future governance discussion, but it must not silently rewrite the active system.

### Allowed Effects of Review

- identifying repeated false-positive patterns
- identifying repeated abstention success
- surfacing weak timing logic
- surfacing confidence inflation
- informing future work-order revisions or controlled tuning proposals

### Not Allowed in V1

- automatic adjustment of signal weights
- automatic threshold changes
- silent strategy mutation
- automatic wallet-policy expansion
- retroactive promotion of a lucky trade into validated doctrine

### Hard Rule

The review is a learning surface, not an autonomous optimization engine.

## Section X - Constraints, Prohibitions, Validation, and V1 Boundaries

### Hard Constraints

- No post-resolution review may modify prior receipts
- No review may collapse reasoning quality into profit and loss alone
- No missing-artifact case may be treated as fully trusted
- No review may skip variance analysis when warranted
- No execution-related learning may bypass governance review before becoming policy

### Explicit Prohibitions

- `We won, therefore it was good`
- `We lost, therefore it was bad`
- rewriting earlier confidence after the fact
- masking abstention success because no trade occurred
- using review notes as implicit authorization to change runtime behavior

### Validation Expectations for CBO

CBO should validate that each review:

- resolves against actual market outcome
- references canonical upstream artifacts
- contains explicit decision-quality and outcome classifications
- distinguishes variance from real edge where possible
- preserves the difference between review insight and runtime authority

### V1 Boundary

- retrospective only
- human-auditable
- no automatic tuning
- no background optimization loop
- single-operator, low-capital governed experimentation

## Implementation Note for CBO

CBO should treat this work order as the mechanism that prevents Kalshi v1 from becoming a superstition engine.

The key question after each resolved market is not merely:

`Did we win?`

It is:

`Did we reason in a way worth trusting again?`

That distinction is what protects Station Calyx from learning the wrong lesson from noisy markets.
