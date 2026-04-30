---
status: archived
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_KALSHI_AGENT_HARNESS_V1

## Status Note

This work order is parked and on hold. It is retained for later reactivation and does not currently authorize or prioritize Station activity.

## Section I - Purpose and Scope

### Purpose

Establish a governed integration harness between Station Calyx and the Kalshi API that enables:

- Market research (read-only)
- Conditional trade execution (write-capable)
- Strict operator-mediated engagement

### Scope

This work order:

- Applies only to Kalshi API interaction
- Applies only to Calyx agents operating under CBO Core governance
- Applies only to v1 workstation-bound execution

This work order does not:

- Authorize autonomous trading without operator presence
- Grant persistent or background execution rights
- Allow implicit or inferred trade intent
- Permit external schedulers or agents to initiate trades
- Override wallet or exposure limits defined outside this work order

## Section II - Definitions

### `kalshi_harness`

A governed adapter layer responsible for all Kalshi API communication.

### `research_mode`

Read-only interaction with Kalshi markets, forecasts, and order books.

### `execution_mode`

Write-capable interaction including order placement, modification, or cancellation.

### `operator_presence`

Verified physical and session presence at the main workstation.

### `execution_intent_artifact`

A formal Calyx Intent Artifact explicitly authorizing a trade.

### `trade_envelope`

A Work Envelope containing all parameters required for execution.

### `wallet_policy`

Predefined constraints governing exposure, sizing, and allowed actions.

### `presence_gate`

A hard gate that prevents execution without validated operator presence.

## Section III - Core Principles

### Presence Before Power

No execution without confirmed operator presence.

### Intent Before Action

Every trade must originate from an explicit Intent Artifact.

### Research Does Not Equal Execution

Research pathways must not escalate into execution implicitly.

### Receipts Are Authority

If it is not receipted, it did not happen.

### Deny by Default

All execution pathways are closed unless explicitly opened.

### Local-First Control

All execution authority must originate from the main workstation.

### No Silent Autonomy

The system must never decide to trade without declared intent.

## Section IV - System Architecture Requirements

The harness must be implemented as a bounded adapter layer:

`cbo_core -> kalshi_harness -> kalshi_api`

### Required Components

- `kalshi_client` - API wrapper
- `research_interface` - read-only surface
- `execution_interface` - write surface, gated
- `wallet_guard` - enforces policy constraints
- `presence_validator`
- `receipt_emitter`

### Separation Requirements

- Research and execution must exist as distinct code paths
- Execution interface must not be callable from research pathways
- All execution entry must flow through the canonical Calyx spine:
  `Mail -> Intent Artifact -> Work Envelope -> Contract Gate -> Execution -> Receipts`

### Failure Mode

Any ambiguity fails closed.

## Section V - Presence Gate Requirements

### V1 Critical Constraint

Execution is allowed only if all conditions are true:

- Request originates from the main workstation (`Calyx Terminal` node)
- Active session is locally authenticated
- Session is not remote or relayed
- Presence signals confirm recent operator interaction within a bounded window
- No idle timeout breach is active
- Governance state is not `maintenance` or `stale_state`
- Truth freshness is valid

If any condition fails:

- Block execution
- Emit receipt: `execution.blocked.presence_gate`

## Section VI - Intent to Execution Spine

All trades must follow the canonical spine already recognized by Station Calyx.

### 1. Mail

Operator expresses trade intent.

### 2. Intent Artifact

Structured intent is created with:

- `market_id`
- `position` (`yes` or `no`)
- `price` or `limit`
- `size`
- `rationale` (optional but recommended)

### 3. Work Envelope

Validated and normalized trade parameters are minted from the Intent Artifact.

### 4. Contract Gate

Checks:

- `presence_gate`
- `wallet_policy`
- governance state
- duplication and replay protection

### 5. Execution

Single API call through `kalshi_harness`.

### 6. Receipts

Full execution trace is recorded.

No step may be skipped or inferred.

## Section VII - Wallet Policy Enforcement

The harness must enforce strict constraints.

### Example V1 Policy

- `max_single_transaction`: `$2`
- `max_daily_exposure`: `$5`
- `max_trades_per_day`: `3`

### Allowed Actions

- `open_position`
- `close_position`

### Prohibited Actions

- `leverage`
- `transfers`
- `withdrawals`

### Enforcement Requirements

- Pre-execution validation is required
- Violations hard-block execution
- Emit receipt: `execution.blocked.wallet_policy`

## Section VIII - Research Mode Requirements

Research mode must:

- Be the default mode
- Require no presence gate
- Allow market scanning
- Allow probability analysis
- Allow order book inspection
- Allow historical evaluation

### Strict Prohibition

Research outputs must not trigger execution automatically.

### Escalation Rule

Transition to execution requires:

- Explicit operator intent
- A new Intent Artifact

## Section IX - Receipts, Audit, and Traceability

Every interaction must produce receipts.

### Research Receipts

- `kalshi.research.query`
- `kalshi.market.snapshot`

### Execution Receipts

- `trade.intent.created`
- `trade.envelope.validated`
- `trade.execution.attempted`
- `trade.execution.success`
- `trade.execution.failed`

### Mandatory Fields

- `corr_id`
- `operator_presence_status`
- `wallet_state_snapshot`
- `market_state_snapshot`
- `request_payload` (sanitized)
- `response_payload` (sanitized)

### Audit Requirement

All trades must be reconstructable from receipts alone.

## Section X - Constraints, Prohibitions, and V1 Boundaries

### Hard Constraints

- No background execution
- No scheduled trading
- No external launcher authority
- No Discord-triggered execution
- No API exposure outside the local node

### Explicit Prohibitions

- Auto-trade loops
- Strategy execution without operator-issued intent
- Silent retries that alter trade conditions
- Cross-session execution carryover

### V1 Boundary

- Single-user
- Single-node
- Presence-gated
- Low-capital experimental scope

## Closing Note - Pressure Test

If this work order is followed correctly:

- The agent can assist, recommend, and execute
- It cannot silently act
- It cannot out-authority the operator

If this work order is violated:

- The system drifts into implicit autonomy
- Financial-agent trust collapses with it
