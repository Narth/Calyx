---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_WEATHER_MARKET_RESEARCH_LAYER_V1

## Status Note

This work order is parked and on hold alongside the current Kalshi planning set. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define the governed weather-market research layer by which Station Calyx may gather, normalize, compare, and evaluate weather-related evidence for use in Kalshi shadow-mode market research and trade-thesis formation.

### Scope

This work order governs:

- allowed weather-market research inputs
- evidence normalization for weather-related candidate markets
- forecast comparison logic
- divergence identification
- timing and freshness expectations
- research outputs intended for the Kalshi strategy layer

This work order applies only to weather-related prediction markets considered under the Kalshi planning stack, including but not limited to:

- temperature markets
- precipitation or rain markets
- snowfall markets
- related weather-threshold markets where the resolution basis is observable and bounded

This work order is subordinate to:

- `WO_KALSHI_AGENT_HARNESS_V1`
- `WO_KALSHI_STRATEGY_LAYER_V1`
- `WO_KALSHI_SIGNAL_SCORING_PROFILE_V1`
- `WO_KALSHI_ARTIFACT_AND_RECEIPT_SCHEMA_V1`
- `WO_KALSHI_POST_RESOLUTION_REVIEW_V1`

This work order does not:

- authorize execution
- authorize live portfolio management
- authorize unsupervised market polling loops
- define order placement logic
- treat weather data alone as sufficient for execution readiness
- replace wallet, presence, or execution gates

## Section II - Definitions

### `weather_research_layer`

The bounded research surface that gathers and evaluates weather evidence relevant to a candidate weather market.

### `weather_candidate_market`

A Kalshi market whose resolution depends on measurable weather outcomes.

### `forecast_source`

A weather information source used to inform candidate-market evaluation.

### `forecast_snapshot`

A time-bounded captured record of forecast data from one source at one moment.

### `forecast_bundle`

A normalized grouped set of forecast snapshots for the same candidate market and evaluation window.

### `forecast_divergence`

Meaningful difference between market-implied probability or pricing and forecast-informed expectation.

### `freshness_window`

The time interval in which a captured forecast remains eligible for governed research use.

### `resolution_basis`

The observable criterion by which the market settles, such as daily high temperature, measurable rainfall, or snowfall accumulation.

### `weather_thesis_support`

The evidence summary produced by the weather research layer for downstream strategy evaluation.

## Section III - Core Principles

### Observable Reality Over Narrative

Weather markets should be evaluated from measurable forecast and observation data, not story-like reasoning.

### Research Before Recommendation

The layer exists to inform strategy, not to produce implicit trade authority.

### Freshness Matters

Weather evidence decays quickly. Stale forecasts must not be treated as current truth.

### Multiple Sources Are Better Than One

Where feasible, weather judgments should be informed by source comparison, not a single forecast in isolation.

### Resolution Fit Is Mandatory

Research must align to the market’s actual settlement condition, not merely a related weather narrative.

### Tradability Still Governs

Strong weather evidence cannot rescue a non-tradable market.

### Uncertainty Must Remain Visible

Forecast spread, disagreement, and shifting conditions must remain explicit in downstream artifacts.

## Section IV - Allowed Market Classes and V1 Boundaries

The weather research layer may support only bounded, observable weather market classes in v1.

### Allowed V1 Market Classes

- daily high temperature markets
- daily low temperature markets
- measurable rain or precipitation markets
- measurable snowfall markets
- threshold-based weather event markets where the resolution rule is legible and externally monitorable

### Disfavored or Excluded in V1

- broad seasonal or long-range climate-style markets
- markets with ambiguous local measurement boundaries
- markets whose resolution depends on hard-to-access private or delayed data
- composite weather-event markets with excessive interpretation burden
- markets requiring continuous intraday micromanagement to remain valid

### V1 Operating Boundary

- shadow-mode only
- read-only research only
- single-operator review
- bounded set of manually selected markets
- no autonomous discovery loops required

## Section V - Allowed Evidence Sources and Source Conduct

The weather research layer must use bounded, attributable evidence sources.

### Preferred Source Classes for V1

- official public forecast sources
- official public observations
- recognized weather forecast services
- manually captured local forecast records for comparison, if provenance is preserved

### Source Conduct Requirements

- every forecast used must be attributable to a named source
- every forecast used must include capture time
- every forecast used must be associated with the relevant location and forecast window
- raw source values must be preservable alongside normalized values

### Required Provenance Fields for Each Forecast Snapshot

- `source_name`
- `captured_at_utc`
- `location_basis`
- `forecast_target_window`
- `forecast_value_summary`
- `raw_reference` or raw captured payload where feasible

### Prohibition

- no unattributed `weather says` reasoning
- no silent blending of multiple sources into one synthetic claim without traceability
- no use of stale forecast data without explicit freshness labeling

## Section VI - Forecast Normalization and Research Artifact Requirements

The weather research layer must normalize source data into a bounded research artifact suitable for downstream strategy use.

### Required Normalized Concepts, as Applicable to Market Type

- target location
- target resolution date or window
- relevant weather metric
- source-by-source forecast values
- forecast spread or disagreement
- latest captured observations if available
- freshness state
- resolution-rule fit assessment

### For Temperature Markets, Normalization Should Capture

- forecast highs or lows by source
- range spread across sources
- threshold relation to market strike
- degree of confidence suggested by source clustering or dispersion

### For Rain or Precipitation Markets, Normalization Should Capture

- probability of precipitation where available
- expected accumulation where available
- forecast wording severity or confidence only as a secondary signal
- threshold relation to market condition
- disagreement across sources

### Required Research Output Artifact Content

- market identifier
- weather market type
- research timestamp
- source summary table or equivalent structured summary
- divergence note
- freshness note
- uncertainty note
- preliminary suitability note

This output must remain research-supporting, not execution-authorizing.

## Section VII - Divergence Logic and Candidate Suitability

The weather research layer must explicitly assess whether a meaningful divergence may exist between market pricing and forecast-informed expectation.

### Required Divergence Questions

- What outcome is the market implying?
- What do the captured forecast sources imply?
- Do those implications materially differ?
- Is the difference large enough to matter after uncertainty and tradability are considered?

### Candidate Suitability Factors Must Include

- resolution clarity
- weather-source freshness
- source agreement or disagreement
- metric fit to settlement rule
- time remaining before market resolution
- market tradability state
- whether the apparent edge depends on forecast lag versus true mispricing

### Required Suitability Outcomes

- `weather_research.unsuitable`
- `weather_research.inconclusive`
- `weather_research.possible_divergence`
- `weather_research.supportive_but_uncertain`
- `weather_research.supportive`

### Constraint

Even `weather_research.supportive` must not bypass strategy scoring or execution gates.

## Section VIII - Timing, Freshness, and Re-Evaluation Requirements

Weather research is highly time-sensitive and must decay accordingly.

### Freshness Rules for V1

- every forecast bundle must declare a capture timestamp
- every forecast bundle must declare whether it is current, aging, or stale
- aging or stale bundles must reduce downstream confidence or trigger re-evaluation

### Required Re-Evaluation Triggers

- meaningful forecast change
- meaningful source disagreement increase
- approach to resolution window
- movement in observed conditions that materially changes thesis relevance
- elapsed time beyond defined freshness window

### Hard Constraint

No weather-informed candidate may remain execution-ready in shadow analysis without verifying that its supporting forecast bundle is still fresh relative to the decision moment.

### Receipt or Artifact Expectation

Forecast refreshes and freshness degradations should be observable in staging artifacts or receipts.

## Section IX - Interfaces to Strategy, Scoring, and Review

The weather research layer must feed the Kalshi stack without redefining it.

### Downstream Interface Obligations

- provide structured evidence summaries usable by the strategy layer
- provide uncertainty visibility for scoring
- preserve raw and normalized research references for later review
- support post-resolution review with source snapshots that existed at decision time

### Expected Downstream Contributions

To `trade_thesis_artifact`:

- evidence summary
- expected edge source
- invalidation cues

To `signal_score_record`:

- evidence strength support
- mispricing potential support
- timing quality support
- decision horizon fit support

To `post_resolution_review_artifact`:

- whether forecast evidence was sound
- whether source spread was handled honestly
- whether timing and freshness were respected

### Semantic Rule

The weather research layer may strengthen or weaken a thesis, but it may not directly emit `execution_ready` as a terminal authority classification.

## Section X - Constraints, Prohibitions, Validation, and V1 Boundaries

### Hard Constraints

- no execution authority
- no portfolio or order-path access
- no silent source substitution
- no stale-data use without explicit labeling
- no weather thesis support without location and resolution alignment
- no tradability bypass because a forecast looks compelling

### Explicit Prohibitions

- treating one dramatic forecast update as certainty
- overreading vague forecast language into hard market edge
- using generalized `bad weather expected` claims where the market resolves on a precise metric
- silently carrying forward old forecast bundles into new evaluations
- collapsing source disagreement into artificial confidence

### Validation Expectations for CBO

CBO should validate that:

- each weather research artifact references attributable sources
- capture times are present
- normalization preserves source distinctions
- divergence claims are grounded in explicit source values
- non-tradable market states still result in abstention at the strategy or gate layer
- post-resolution review can reconstruct what the weather evidence actually looked like at decision time

### V1 Boundary

- weather-specialized research only
- shadow-mode support only
- manually reviewed markets
- read-only evidence collection
- human-auditable source normalization
- no automatic execution escalation

## Implementation Note for CBO

CBO should treat this work order as a domain-specialization layer, not a shortcut around the Kalshi governance stack.

The goal is not to let weather data pick trades.

The goal is to let Station Calyx reason about a domain where:

- evidence is measurable
- divergence is more legible
- post-resolution review can more honestly distinguish edge from noise

The weather layer should therefore improve:

- evidence quality
- thesis quality
- abstention quality

without changing the fundamental authority boundaries already established.
