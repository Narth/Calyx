---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_STATION_HEALTH_LOOP_EFFICIENCY_AND_TRUTH_PRESERVATION_V1

## Purpose

Define a governed optimization and normalization plan for `station_health_loop.ps1` that reduces steady-state CPU cost while preserving truthful health reporting, derived-truth freshness, stale handling, and multiplicity governance.

This work order treats `station_health_loop.ps1` as a truth-bearing Station surface, not merely a background convenience loop.

## Status

Planning and governance definition only.

This document does not authorize runtime mutation, restart, deduplication, or cadence changes by itself.

## Scope

This work order governs:

- singleton or multiplicity-safe operation for `station_health_loop.ps1`
- cadence and duty-cycle redesign options
- cheaper health sampling strategies
- separation of authoritative health truth from lower-priority observability enrichments
- preservation of downstream `STATE.md` and truth-contract semantics

This work order applies to:

- `Scripts\station_health_loop.ps1`
- `Scripts\update_state_checks.ps1`
- `runtime\station_health.json`
- `runtime\station_health_history.jsonl`
- derived-truth expiry sweep behavior currently attached to the health loop cadence

This work order does not:

- reduce health truth to best-effort telemetry
- authorize silent duplicate suppression
- remove stale or unknown-state semantics
- weaken BloomOS or CBO visibility into station health

## Background

Recent read-only assessment identified `station_health_loop.ps1` as the primary governed efficiency target.

Observed conditions:

- two resident `station_health_loop.ps1` processes are currently active
- both are materially CPU-expensive
- the operational audit for Station health describes a single PowerShell process, not declared multiplicity
- the current implementation performs multiple expensive system and process scans in the main loop
- the current sleep calculation does not enforce a true one-second cadence under the default parameter set

At the same time, this loop carries real governance value:

- it writes the authoritative `runtime\station_health.json`
- it feeds `update_state_checks.ps1`
- it supports stale handling and operator-visible unknown-state behavior
- it already hosts the derived-truth expiry sweep as a minimum cadence source

Optimization must therefore preserve truth before reducing cost.

## Relationship to Existing Governance

This work order is complementary to:

- `WO_RUNTIME_TOPOLOGY_LABELING_V1`
- `WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1`
- `WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1`
- `WO_RUNTIME_MULTIPLICITY_ENFORCEMENT_AND_VALIDATION_V1`

This work order also relies on the Station health contract documented in:

- `docs\operations\STATION_HEALTH_BLOOMOS_AUDIT.md`

## Core Principles

### Truth Before Optimization

Health cost reduction is acceptable only if authoritative health freshness and stale semantics remain trustworthy.

### Single Authoritative Writer by Default

The health loop should behave as a `single_instance_only` truth surface unless a different multiplicity posture is explicitly declared.

### Fast Health, Slower Enrichment

Not every field in `station_health.json` requires the same cadence.

Authoritative health should remain fast.

Expensive enrichments should be sampled more slowly when possible.

### Stale Is Honest

If health truth cannot be freshly produced, the station should degrade to explicit stale or unknown handling rather than fake continuity.

### Multiplicity Must Be Visible

Duplicate health loops must not be silently normalized into legitimacy.

If multiplicity occurs, it should be receipt-backed and classifiable.

## Current Truth Obligations

The current Station health path is expected to preserve:

- `health`
- `health_ts`
- `cpu_pct`
- `ram_pct`
- freshness metadata added through the runtime truth contract
- derived-truth expiry sweep coverage
- operator-visible stale and unknown-state outcomes

The current downstream consumer of this truth path includes:

- `Scripts\update_state_checks.ps1`
- `STATE.md`
- heartbeat and liveness consumers that react to stale or failed health

These obligations must remain intact under any optimization plan.

## Current Cost Drivers

The present implementation appears to incur steady-state cost from:

- repeated `Get-CimInstance` CPU polling
- repeated `Get-CimInstance` RAM polling
- repeated `Get-Process` top-process scanning
- repeated `Win32_PerfFormattedData_PerfProc_Process` attribution scans
- repeated `nvidia-smi` polling where available
- JSON artifact writes every loop
- loop cadence behavior that effectively allows near-continuous iteration under default settings

The strongest design problem is not merely “one expensive call.”

It is the combination of:

- duplicate residency
- expensive enrichments inside the fast path
- and cadence behavior that does not strongly enforce the intended interval

## Required Design Outcomes

Any future implementation shaped by this work order should satisfy all of the following:

- one authoritative health writer in steady state
- explicit multiplicity classification when duplicate launch is attempted
- true bounded fast cadence for authoritative health
- slower cadence for non-authoritative enrichments where safe
- no loss of stale detection semantics
- no loss of derived-truth expiry sweep behavior
- no silent reduction in governance visibility

## Singleton and Multiplicity Design Requirements

`station_health_loop.ps1` should be governed as:

- `topology_class = single_process`
- `multiplicity_posture = single_instance_only`

unless a later governed declaration explicitly changes that posture.

### Required Future Behavior for Duplicate Launch

If a second health loop launch is attempted, acceptable governed outcomes may include:

- refuse secondary writer entry
- emit `runtime.launch_notice` or multiplicity validation receipt
- classify the attempted expansion as `undeclared_multiplicity` or `duplicate_concerning`
- preserve the original authoritative writer if still healthy

Unacceptable behavior:

- two authoritative writers silently racing on the same truth surface
- duplicate residency treated as benign merely because both loops write valid-looking JSON

### Acceptable Singleton Enforcement Approaches

Planning-acceptable approaches include:

- file lock or lockfile with stale-owner handling
- named mutex or equivalent host-local singleton primitive
- explicit leader election only if it preserves auditability and is more complex for a good reason

Preferred planning outcome:

- the simplest singleton mechanism that preserves attributable duplicate-launch classification

## Cadence and Duty-Cycle Design Requirements

The health loop should preserve fast truth while avoiding needless oversampling.

### Authoritative Fast Path

The following should remain on the fast path:

- health tier derivation
- health timestamp and freshness
- minimum CPU and RAM state required for truthful health posture
- derived-truth expiry sweep invocation

### Slower Enrichment Path

The following may move to slower sub-cadences if freshness is represented honestly:

- cumulative top-process list
- current-CPU entropy-source attribution
- GPU detail polling
- non-critical history metadata enrichment

### Cadence Rule

A future implementation should enforce real elapsed-time-based sleeping, not implicit best-effort looping that becomes continuous under default parameters.

Hard rule:

Optimization must not fake a one-second truth contract while internally sampling much slower without explicit schema or freshness meaning.

## Cheaper Sampling Strategy Requirements

Future optimization work should distinguish:

- authoritative health inputs
- observability enrichments

### Authoritative Health Inputs

These should remain trustworthy, bounded, and simple:

- CPU percent
- RAM percent
- health classification
- health timestamp
- memory pressure tier
- truth freshness metadata

### Observability Enrichments

These may be sampled less frequently if clearly labeled or recent-enough by contract:

- top three processes by cumulative CPU
- top entropy sources by current CPU
- GPU utilization, VRAM, and temperature
- extended diagnostic metadata not required for every heartbeat consumer

### Sampling Integrity Constraint

If enriched fields are sampled more slowly, the artifact contract should preserve enough meaning for later review to distinguish:

- authoritative health time
- enrichment sample time or recency

## Derived Truth and Stale Handling Requirements

The current role of `station_health_loop.ps1` as a cadence source for derived-truth expiry sweep must remain visible in the design.

Future optimization should not:

- move expiry behavior to an undeclared extra daemon
- weaken stale-state self-demotion
- create a second truth-maintenance process merely to reduce health-loop cost

Preferred direction:

- keep truth expiry sweep attached to the existing authoritative health cadence source

## Validation Expectations

Any future implementation based on this work order should be validated against:

- one and only one authoritative writer in steady state
- duplicate launch visibility and classification
- correct stale or unknown behavior if the loop stops
- preserved `update_state_checks.ps1` compatibility
- preserved downstream `STATE.md` health semantics
- lower steady-state CPU cost than the current design under comparable workstation conditions

Validation should explicitly measure:

- cost of authoritative health path
- cost of enrichment path
- effect of singleton enforcement
- correctness under duplicate launch attempt

## Constraints

Hard constraints:

- no silent duplicate-writer normalization
- no weakening of stale or unknown-state semantics
- no removal of derived-truth expiry sweep coverage without governed replacement
- no optimization that hides reduced freshness behind unchanged field meaning

Explicit prohibitions:

- treating all health fields as equally cadence-critical when they are not
- treating duplicate health loops as acceptable because the JSON still updates
- adding a second daemon just to carry truth-expiry work that the existing loop already covers
- reducing health cadence in a way that breaks Station health contract without explicit contract revision

## Preferred Phase Order

### Phase 1

Declare `station_health_loop` multiplicity posture and authoritative writer rule.

### Phase 2

Implement and validate singleton enforcement with visible duplicate-launch classification.

### Phase 3

Restore true elapsed-time cadence enforcement for the fast path.

### Phase 4

Split fast authoritative health from slower enrichments.

### Phase 5

Measure cost reduction and confirm downstream truth semantics remain intact.

## Desired Outcome

Station health remains fast, truthful, and stale-aware.

But it no longer pays avoidable steady-state CPU cost through:

- duplicate authoritative writers
- continuous oversampling
- or treating all observability detail as if it required the same cadence as truth.
