---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_WEATHER_SIGNAL_INTERPRETATION_PROFILE_V1

## Status Note

This work order is parked and on hold alongside the current Kalshi planning set. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define the governed weather signal interpretation profile by which Station Calyx translates weather research artifacts into bounded, auditable scoring support for Kalshi weather-market evaluation.

### Scope

This work order governs:

- interpretation of weather forecast evidence
- mapping of forecast conditions into scoring support signals
- treatment of source agreement and disagreement
- treatment of threshold proximity and ambiguity
- freshness decay effects on signal interpretation
- weather-specific downgrade behavior for downstream strategy scoring

This work order applies only to weather-related candidate markets evaluated under the Kalshi shadow-mode stack and is subordinate to:

- `WO_KALSHI_STRATEGY_LAYER_V1`
- `WO_KALSHI_SIGNAL_SCORING_PROFILE_V1`
- `WO_KALSHI_ARTIFACT_AND_RECEIPT_SCHEMA_V1`
- `WO_KALSHI_POST_RESOLUTION_REVIEW_V1`
- `WO_WEATHER_MARKET_RESEARCH_LAYER_V1`

This work order does not:

- authorize execution
- replace the general Kalshi signal scoring profile
- define wallet, presence, or execution gates
- permit hidden weighting or adaptive interpretation
- allow weather interpretation outputs to become terminal authority classifications

## Section II - Definitions

### weather_signal_interpretation_profile

The governed ruleset for converting weather research evidence into bounded scoring support inputs.

### interpretation_support

A structured indication of how weather evidence should strengthen, weaken, or leave unchanged downstream scoring dimensions.

### source_agreement

The degree to which forecast sources align on the relevant metric and threshold direction.

### source_disagreement

The degree to which forecast sources materially diverge in values or implications.

### threshold_proximity

The closeness of forecast values to the market's settlement threshold.

### threshold_ambiguity

A condition in which forecast spread or uncertainty makes threshold crossing unclear.

### freshness_decay

Reduction in support quality due to forecast age relative to the decision moment.

### weather_downgrade_flag

An explicit signal that weather evidence must reduce downstream confidence, evidence strength, or suitability.

### support_band

A bounded interpretation outcome such as weak, moderate, or strong support.

## Section III - Core Principles

### Interpretation Must Remain Mechanical Enough to Audit

Weather evidence must not be converted into judgment through vague intuition.

### Uncertainty Must Reduce Support

Forecast spread, threshold ambiguity, and freshness loss must penalize downstream scoring.

### Threshold Markets Require Precision

Small forecast differences near the settlement line matter more than broad narrative confidence.

### Agreement Strengthens, Disagreement Weakens

Cross-source convergence should raise support only when tied to the actual settlement metric.

### Freshness Is Part of Meaning

Old weather evidence is not merely weaker; it is a different quality of evidence.

### Support Is Not Authority

Even strong weather support may only inform the strategy layer; it may not directly create execution readiness.

### Tradability Still Overrides Weather Quality

Strong interpretation support cannot rescue a non-tradable market.

## Section IV - Supported Market Interpretation Classes

The weather signal interpretation profile must explicitly handle, at minimum, the following v1 weather market classes:

### Temperature Threshold Markets

Example: daily high above or below a specified degree threshold.

### Daily Low Temperature Threshold Markets

Example: overnight low above or below a specified threshold.

### Precipitation Occurrence Markets

Example: measurable rain yes or no.

### Precipitation Threshold Markets

Example: rainfall above or below a defined accumulation amount.

### Snowfall Threshold Markets

Example: measurable snowfall or snowfall accumulation above threshold.

V1 exclusion guidance:

- long-range climate-style interpretation
- severe-weather composite narratives
- highly custom weather composites requiring extensive human inference
- any market where the settlement metric cannot be cleanly matched to forecast inputs

## Section V - Temperature Signal Interpretation Rules

For temperature markets, interpretation must be based on settlement-threshold relation, source spread, and freshness.

Required temperature interpretation inputs:

- settlement threshold
- source-by-source forecast values
- spread between highest and lowest forecast
- capture times and freshness state
- any observed temperature context if relevant and timely

Interpretation rules:

### Strong support is possible only when:

- most or all relevant sources fall on the same side of the threshold
- the spread is modest relative to threshold distance
- the bundle is fresh
- threshold crossing appears materially clear rather than marginal

### Moderate support applies when:

- sources lean one direction but some uncertainty remains
- spread is noticeable but not disqualifying
- threshold distance is meaningful but not decisive

### Weak support or downgrade applies when:

- forecasts cluster too near the threshold
- source spread materially overlaps both sides of the threshold
- freshness has degraded
- the apparent edge depends on very small differences likely within normal forecast error

Required weather downgrade cases for temperature markets:

- `temperature.threshold_ambiguity`
- `temperature.high_source_spread`
- `temperature.stale_bundle`
- `temperature.marginal_edge`

Hard rule:

A 1-2 degree apparent edge near threshold must not be treated as strong support unless source agreement and freshness are unusually strong.

## Section VI - Precipitation and Snow Signal Interpretation Rules

For rain and snow markets, interpretation must distinguish between occurrence, accumulation, and vague forecast language.

Required precipitation or snow interpretation inputs:

- source-by-source probability of precipitation where available
- source-by-source expected accumulation where available
- settlement threshold or occurrence condition
- forecast window alignment
- source disagreement and freshness state

### Occurrence markets

Support should rely on meaningful source agreement that measurable precipitation is or is not likely within the settlement window.

Vague wording alone must not be treated as strong support.

### Threshold accumulation markets

Support should rely more heavily on explicit accumulation expectations than on generic precipitation chance.

A high chance of precipitation does not automatically imply threshold-crossing support.

### Strong support is possible only when:

- multiple sources align materially on occurrence or threshold direction
- accumulation or occurrence evidence fits the actual market rule
- freshness is acceptable
- disagreement is limited

### Weak support or downgrade applies when:

- probability of precipitation is high but accumulation is uncertain relative to threshold
- sources disagree materially on amount or timing
- support depends mostly on interpretive wording rather than measurable forecast values
- bundle freshness has degraded

Required weather downgrade cases for precipitation or snow markets:

- `precipitation.high_disagreement`
- `precipitation.accumulation_uncertain`
- `precipitation.window_mismatch`
- `precipitation.stale_bundle`
- `snow.threshold_ambiguity`

Hard rule:

Probability of precipitation must not be treated as a direct settlement proxy for an accumulation threshold market.

## Section VII - Source Agreement, Freshness, and Downgrade Mapping

The interpretation profile must explicitly translate source agreement and forecast freshness into downstream scoring effects.

Source agreement guidance:

- high agreement may strengthen:
  - evidence strength
  - mispricing potential
  - decision horizon fit
- high disagreement must weaken:
  - evidence strength
  - confidence calibration
  - execution suitability

Freshness guidance:

- fresh bundles may preserve support
- aging bundles should reduce support moderately
- stale bundles should strongly reduce support or force re-evaluation

Required downgrade mapping outputs:

### weather_support_band

- `weak`
- `moderate`
- `strong`

### weather_downgrade_flags

List of explicit downgrade reasons.

### downstream_signal_effects

Bounded suggestions such as:

- `reduce_evidence_strength`
- `reduce_mispricing_potential`
- `reduce_timing_quality`
- `reduce_decision_horizon_fit`
- `force_research_only_ceiling`
- `force_abstention_review`

Constraint:

Downgrade outputs may constrain downstream scoring, but must not silently rewrite general Kalshi scoring semantics.

## Section VIII - Integration With Kalshi Scoring and Strategy Gates

Weather interpretation outputs must feed the Kalshi stack in a bounded and legible manner.

Expected downstream uses:

- strengthen or weaken `evidence_strength`
- strengthen or weaken `mispricing_potential`
- strengthen or weaken `timing_quality`
- strengthen or weaken `decision_horizon_fit`
- support explicit downgrade flags in the signal score record
- influence whether the strategy gate should cap the result at:
  - `abstain.market_not_suitable`
  - `recommend.research_only`
  - `recommend.execution_ready_low_confidence`

Hard integration rules:

- weather interpretation must not directly emit `recommend.execution_ready`
- high weather support must not override low tradability
- stale or highly conflicted weather evidence should generally cap outcomes below strong execution-readiness
- threshold ambiguity should be visible in both thesis and score records when material

Preferred behavior in v1:

The weather interpretation layer should err toward constraining over-permissive outcomes rather than inflating support.

## Section IX - Required Artifacts, Traceability, and Review Expectations

The weather signal interpretation profile must produce interpretable and reviewable outputs.

Required interpretation output content:

- `schema_name`
- `schema_version`
- `artifact_type`
- `corr_id`
- `market_id`
- `weather_market_type`
- `source_bundle_ref`
- `interpretation_timestamp_utc`
- `weather_support_band`
- `threshold_proximity_assessment`
- `source_agreement_assessment`
- `freshness_assessment`
- `weather_downgrade_flags`
- `downstream_signal_effects`
- `interpretation_notes`

Review expectations:

Post-resolution review must be able to assess:

- whether the weather support band was appropriate
- whether disagreement was under- or over-penalized
- whether threshold ambiguity was handled honestly
- whether freshness decay should have constrained the outcome more strongly
- whether the weather layer contributed to a false-positive or prevented one

Prohibition:

Interpretation outputs must not contain execution-authority language or imply permission to trade.

## Section X - Constraints, Prohibitions, Validation, and V1 Boundaries

Hard constraints:

- no adaptive interpretation weights in v1
- no hidden confidence inflation
- no silent averaging-away of disagreement
- no treating vague forecast language as hard metric evidence
- no support band assignment without explicit threshold and freshness consideration where applicable
- no bypass of tradability or strategy gates

Explicit prohibitions:

- calling a near-threshold temperature forecast `strong` without clear supporting spread and freshness conditions
- treating high probability of precipitation alone as strong support for accumulation-threshold markets
- carrying forward stale forecast support into later decision states without downgrade
- using weather interpretation to justify decisions that the broader Kalshi gate should block
- collapsing source disagreement into a single averaged narrative without preserved raw references

Validation expectations for CBO:

CBO should validate that:

- temperature and precipitation interpretation rules are represented explicitly
- downgrade flags are emitted for ambiguity, disagreement, and staleness
- downstream signal effects remain bounded and auditable
- interpretation outputs preserve source bundle references
- no interpretation artifact contains execution-authority fields or terms
- post-resolution review can compare interpretation-time support against actual resolved weather outcome

V1 boundary:

- static interpretation profile
- weather-only domain specialization
- shadow-mode support only
- human-auditable outputs
- no autonomous optimization or hidden tuning
- subordinate to existing Kalshi governance and scoring layers

## Implementation Note for CBO

CBO should treat this work order as the boundary between:

weather data being present

and

weather data being interpreted consistently.

That distinction matters because most future drift will not come from missing forecasts. It will come from inconsistent judgment about what the same forecast means.

The goal here is not to make the system aggressive.

It is to make the system predictably conservative, legible, and reviewable when weather evidence is close, stale, or conflicted.
