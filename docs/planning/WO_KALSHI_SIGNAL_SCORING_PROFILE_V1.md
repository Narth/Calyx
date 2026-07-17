---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_KALSHI_SIGNAL_SCORING_PROFILE_V1

## Status Note

This work order is parked and on hold. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define a governed signal scoring framework that standardizes how the Calyx strategy layer evaluates, ranks, and classifies trade candidates prior to execution readiness.

### Scope

This work order governs:

- signal generation and normalization
- scoring dimensions and weighting
- classification thresholds
- confidence calibration constraints
- interaction with strategy gate outcomes

This work order applies only within the strategy layer defined in `WO_KALSHI_STRATEGY_LAYER_V1`.

This work order does not:

- authorize execution
- replace thesis construction requirements
- override wallet policy or execution gates
- introduce adaptive or self-modifying scoring without governance review

## Section II - Definitions

### `signal_profile`

The structured set of scoring dimensions used to evaluate a trade candidate.

### `signal_dimension`

A single evaluative axis such as evidence strength or timing quality.

### `signal_score`

A normalized value assigned to a dimension.

### `composite_score`

Aggregated score derived from all signal dimensions.

### `classification_band`

A governed range mapping composite scores to outcomes.

### `confidence_calibration`

Adjustment ensuring confidence reflects evidence, not intuition or narrative strength.

### `false_positive_signal`

A high-scoring trade that lacks real edge.

### `signal_decay`

Reduction in score due to time or changing conditions.

## Section III - Core Principles

### Score the Edge, Not the Story

Narrative strength must not inflate scoring without evidence.

### Consistency Over Brilliance

A repeatable scoring system is preferred over sporadic great calls.

### Penalty for Weak Evidence

Lack of evidence must actively reduce score, not remain neutral.

### Confidence Must Be Earned

Confidence is a derivative signal, not a primary one.

### Comparability Across Trades

Scores must allow side-by-side evaluation of different markets.

### Abstention Is a Valid High-Quality Outcome

A low composite score should confidently produce abstention.

### No Hidden Weights

All scoring dimensions and their effects must be auditable.

## Section IV - Signal Dimensions

### V1 Required Set

Each candidate market must be evaluated across the following dimensions.

### 1. Evidence Strength (`E`)

Question: Is there credible, relevant, and sufficient information?

- High: Multiple aligned, current data sources
- Medium: Partial or indirect evidence
- Low: Sparse, outdated, or speculative

### 2. Market Mispricing Potential (`M`)

Question: Is the current price likely deviating from reality?

- High: Clear divergence between evidence and market price
- Medium: Possible but uncertain divergence
- Low: Price appears efficient or justified

### 3. Timing Quality (`T`)

Question: Is this the right moment to enter?

- High: Near optimal entry window
- Medium: Acceptable but not ideal timing
- Low: Too early, too late, or unstable conditions

### 4. Resolution Clarity (`R`)

Question: Is the outcome definition clear and monitorable?

- High: Clear, objective resolution criteria
- Medium: Some ambiguity but manageable
- Low: Ambiguous or difficult to verify

### 5. Liquidity / Tradability (`L`)

Question: Can the trade be executed reliably at expected terms?

- High: Active market, stable pricing
- Medium: Moderate liquidity
- Low: Thin or erratic market

### 6. Decision Horizon Fit (`H`)

Question: Does the thesis align with the remaining time?

- High: Thesis and resolution timing align well
- Medium: Some mismatch
- Low: Thesis likely invalid before resolution

### 7. Risk Clarity (`K`)

Question: Are the downside and invalidation conditions well-defined?

- High: Clear invalidation and bounded downside
- Medium: Some uncertainty
- Low: Poorly defined risk

## Section V - Scoring Methodology

Each dimension must be scored on a normalized scale:

- `0.0` = unacceptable
- `0.5` = moderate
- `1.0` = strong

### Composite Score Calculation

V1 uses a simple average:

`composite_score = (E + M + T + R + L + H + K) / 7`

### Constraints

- No dimension may be omitted
- A single `0.0` in critical dimensions (`E`, `R`, `K`) should strongly bias toward abstention
- Scores must be explicitly recorded in receipts

### Critical-Dimension Override Rule

Even when the simple average lands in a recommendation band, the profile must downgrade the outcome if:

- `E` is too weak to support the thesis
- `R` is too ambiguous for reliable monitoring
- `K` is too unclear to define bounded downside

This override exists to prevent average-based masking of foundational weakness.

## Section VI - Classification Bands

Composite score maps to governed outcomes:

- `0.00 - 0.39` -> `abstain.insufficient_edge`
- `0.40 - 0.59` -> `abstain.low_quality_candidate`
- `0.60 - 0.74` -> `recommend.research_only`
- `0.75 - 0.89` -> `recommend.execution_ready_low_confidence`
- `0.90 - 1.00` -> `recommend.execution_ready`

### Additional Rule

Even high composite scores must be downgraded if:

- evidence is weak relative to confidence
- timing is unstable
- risk is unclear

### Relationship to Strategy Gate Outcomes

This scoring profile informs but does not replace the strategy gate defined by `WO_KALSHI_STRATEGY_LAYER_V1`.

If the scoring band and the strategy gate disagree, the more conservative outcome wins.

## Section VII - Confidence Calibration Rules

Confidence must be derived, not assigned.

### Baseline Rule

`confidence <= min(E, K)`

### Additional Constraints

- Confidence cannot exceed `composite_score`
- Confidence must degrade under conflicting evidence
- Confidence must degrade under unstable conditions
- Confidence must degrade under incomplete data

### Prohibited Behavior

- expressing high confidence with medium or low evidence
- using narrative certainty as justification

## Section VIII - Signal Decay and Re-evaluation

Signals must degrade over time.

### Decay Triggers

- elapsed time without new evidence
- market price movement invalidating thesis
- approaching resolution without confirmation

### Required Behavior

- previously `execution_ready` signals must be re-evaluated before execution
- stale signals must not be auto-promoted

### Receipt

- `kalshi.signal.decay.applied`

## Section IX - Receipts and Traceability

Each scoring event must emit:

- `kalshi.signal.scored`

### Required Fields

- `corr_id`
- `market_id`
- individual dimension scores (`E`, `M`, `T`, `R`, `L`, `H`, `K`)
- `composite_score`
- `classification_band`
- `confidence`
- `evidence_summary`
- `timestamp`

### Audit Requirement

Any execution-ready recommendation must have a directly traceable scoring receipt.

## Section X - Constraints, Prohibitions, and V1 Boundaries

### Hard Constraints

- No adaptive weighting in v1
- No hidden scoring dimensions
- No retroactive score manipulation after outcome known
- No skipping scoring for obvious trades

### Explicit Prohibitions

- inflating scores to justify action
- suppressing low scores to avoid abstention
- allowing recent wins to bias scoring upward
- allowing recent losses to bias scoring downward

### V1 Boundary

- static scoring model
- human-auditable
- simple averaging
- no ML optimization
- no self-learning weight adjustment
