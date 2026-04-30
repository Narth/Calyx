---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_KALSHI_STRATEGY_LAYER_V1

## Status Note

This work order is parked and on hold. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Define the governed strategic decision layer by which a Calyx agent may evaluate Kalshi markets, form trade recommendations, and prepare bounded execution proposals under Station Calyx authority.

### Scope

This work order governs:

- market research logic
- trade candidate selection
- trade thesis formation
- abstention behavior
- confidence and evidence signaling
- recommendation-to-execution readiness

This work order applies only when operating through the governed Kalshi harness defined by `WO_KALSHI_AGENT_HARNESS_V1`.

This work order does not:

- authorize execution by itself
- define API wiring or exchange transport details
- authorize unsupervised portfolio management
- authorize continuous always-on market scanning
- permit strategy mutation without explicit review
- treat profitable behavior as sufficient proof of legitimacy

## Section II - Definitions

### `strategy_layer`

The bounded reasoning surface that evaluates markets and produces governed trade recommendations or abstentions.

### `trade_thesis`

A concise, evidence-backed statement explaining why a market may be mispriced or worth entering.

### `candidate_market`

A market under evaluation for possible action.

### `actionable_opportunity`

A candidate market whose evidence, timing, liquidity, risk, and policy fit collectively pass the strategy gate.

### `abstention`

An explicit governed outcome indicating no trade should be taken.

### `confidence_signal`

A bounded expression of how strongly the strategy layer supports a thesis.

### `evidence_signal`

A bounded expression of whether the thesis is sufficiently grounded in available information.

### `time_to_resolution`

The remaining time before the market resolves.

### `decision_horizon`

The interval during which the thesis is expected to remain valid enough for entry consideration.

### `execution_readiness`

A classification indicating whether a recommendation is sufficiently formed to be handed to the execution harness, pending operator intent and execution gates.

## Section III - Core Strategic Principles

### Abstention Is Success When Warranted

The strategy layer must prefer no trade over weak trade.

### Legibility Over Cleverness

Every recommendation must be explainable in plain operational language.

### Signal Before Size

Trade quality matters more than trade frequency.

### Research First, Action Second

Market observation and thesis formation must precede any execution proposal.

### Time Matters

A trade thesis without a valid decision horizon is not execution-ready.

### Governed Modesty

The system must not present uncertainty as conviction.

### Bounded Experimentation

V1 is an experimental decision layer, not a generalized autonomous trader.

### Authority Awareness

The strategy layer may recommend; it does not own capital, grant authority, or self-initiate execution.

## Section IV - Strategic Objective and V1 Operating Posture

The v1 strategy layer shall optimize for:

- sound entry discipline
- bounded downside
- high legibility of reasoning
- operator-trustworthy abstention
- measurable decision quality over time

The v1 strategy layer shall not optimize for:

- trade volume
- constant market participation
- maximum theoretical profit
- complex multi-market portfolio balancing
- hidden heuristic exploitation that cannot be audited later

### V1 Posture

The system is operating as a bounded market researcher and proposal engine with optional execution handoff only when engaged by the operator at the main workstation.

The strategy layer must behave like:

- a careful analyst
- a conservative scout
- a poor candidate for compulsive overtrading

## Section V - Candidate Market Selection Requirements

The strategy layer may only elevate markets for serious consideration when the market satisfies baseline candidate filters.

### Required Candidate Dimensions

#### Resolvable Question Clarity

The market prompt and resolution condition must be understandable and materially unambiguous.

#### Evidence Availability

There must exist enough observable information to form a defensible thesis.

#### Time-Bounded Relevance

The market must have a usable decision horizon relative to its resolution time.

#### Liquidity / Tradability Sufficiency

The market must not be so thin or erratic that bounded execution becomes unreliable.

#### Policy Fit

The market must fit within current wallet, risk, and governance bounds.

### Disfavored Market Classes in V1

- markets whose resolution criteria are difficult to monitor reliably
- ultra-thin or chaotic markets
- markets requiring continuous live reaction to maintain edge
- markets whose apparent edge depends mostly on speed rather than thesis quality
- markets where the system lacks reliable evidence access

A market may be interesting without being actionable.

The strategy layer must preserve that distinction.

## Section VI - Trade Thesis Construction Requirements

For every actionable recommendation, the strategy layer must produce a minimally complete trade thesis.

### Required Trade Thesis Fields

- market identifier
- proposed side (`yes` or `no`)
- current observable price context
- intended entry logic
- expected source of edge
- decision horizon
- invalidation condition
- abstention alternative
- confidence signal
- evidence signal

### Expected Source-of-Edge Classes for V1

- weather or forecast divergence
- event-probability mismatch
- stale retail pricing
- lagging market reaction to new public information
- overreaction or underreaction relative to observed evidence

The strategy layer must not produce thesis language that:

- implies certainty where only probability exists
- hides the core assumption
- omits the invalidation condition
- uses confidence as a substitute for evidence

A valid thesis should answer:

- What do we think is mispriced?
- Why do we think that?
- For how long might that belief matter?
- What would make us stand down?

## Section VII - Decision Gate, Abstention Logic, and Execution Readiness

Before any recommendation can become execution-ready, it must pass a strategy gate.

### Strategy Gate Minimum Checks

- evidence sufficiency
- thesis clarity
- confidence calibration
- time-to-resolution fitness
- market tradability
- wallet-policy compatibility
- duplication and replay awareness
- operator legibility

### Required Governed Outcomes

- `abstain.insufficient_evidence`
- `abstain.low_confidence`
- `abstain.poor_timing`
- `abstain.market_not_suitable`
- `recommend.research_only`
- `recommend.execution_ready`

The strategy layer must favor explicit abstention classifications over vague prose such as `maybe`, `looks decent`, or `worth a shot`.

`recommend.execution_ready` means only:

- the thesis is strategically coherent
- the market is suitable
- the recommendation is ready for operator review and possible execution handoff

It does not mean execution is authorized.

Any eventual execution handoff must still enter the canonical Calyx spine through explicit operator intent, Intent Artifact formation, Work Envelope minting, contract gating, and harness-level execution checks.

## Section VIII - Risk Model and Capital Conduct Requirements

The strategy layer must remain subordinate to wallet policy, but it must also apply its own strategic discipline.

### V1 Strategic Capital Conduct Rules

- Prefer small, bounded entries
- Do not treat full wallet capacity as a target
- Avoid correlated overexposure across similar markets
- Avoid repeated revenge-entry into the same thesis after invalidation
- Avoid treating sunk cost as evidence
- Prefer cleaner single-thesis trades over layered speculative stacking

### Strategic Sizing Guidance in V1

- A trade may be valid but still too weak for capital deployment
- A strong thesis with poor timing may still warrant abstention
- Higher confidence does not override wallet policy
- Low-confidence trades should not be upgraded by enthusiasm or boredom

### Hard V1 Strategic Posture

The system must behave as though preserving decision quality is more important than using available budget.

## Section IX - Receipts, Metrics, and Evaluation Requirements

The strategy layer must emit receipts for both action and abstention so that Station Calyx can learn from decision quality over time.

### Required Receipt Classes

- `kalshi.strategy.market_scanned`
- `kalshi.strategy.candidate_evaluated`
- `kalshi.strategy.thesis.formed`
- `kalshi.strategy.abstained`
- `kalshi.strategy.execution_ready`
- `kalshi.strategy.invalidation.observed`
- `kalshi.strategy.post_resolution.review`

### Required Receipt Fields

- `corr_id`
- `market_id`
- `thesis_summary`
- `evidence_summary`
- `confidence_signal`
- `evidence_signal`
- `decision_horizon`
- `abstention_or_recommendation_outcome`
- `operator_engagement_state`
- `wallet_policy_snapshot_reference`

### V1 Evaluation Metrics

- recommendation win/loss rate
- abstention quality
- false-positive rate
- invalidation rate before resolution
- profit or loss per trade
- profit or loss per minute of operator attention
- thesis legibility on post-review
- policy-compliance rate

The system must be evaluable not just on whether it won, but on whether it reasoned responsibly.

## Section X - Constraints, Prohibitions, and V1 Boundaries

### Hard Constraints

- No self-directed continuous strategy loop
- No background market monitoring for execution purposes
- No mutation of strategy criteria without explicit governance review
- No hidden ranking model whose outputs cannot be receipted
- No execution recommendation absent a minimally complete thesis
- No execution handoff from research-only output unless re-evaluated through the strategy gate
- No use of `gut feel` language as substitute for strategy classification

### Explicit Prohibitions

- Overtrading to generate activity
- Treating recent wins as authority escalation
- Martingale-like recovery logic
- Emotional framing such as `make back losses`
- Implicit carryover from prior operator intent
- Auto-promotion of stale research into current execution readiness

### V1 Boundary

- single operator
- single workstation
- low-capital bounded experimentation
- thesis-driven, not speed-driven
- recommendation-first, execution-second
- abstention-positive operating doctrine

## Implementation Note for CBO

CBO should treat this work order as defining a governed decision surface, not a prediction engine in the abstract.

The expected output shape of the strategy layer is not `best guess`.

It is a bounded classification artifact such as:

- market scanned
- candidate rejected
- research-only recommendation
- execution-ready recommendation
- abstention with cause

That makes the strategy layer composable with the canonical spine and auditable after the fact.
