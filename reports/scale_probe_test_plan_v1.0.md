# 🧪 Scale Probe Test Plan v1.0

Internal Performance & Resilience Validation — Draft under Architect Authority  
No new autonomy, actions, or execution privilege added.

## 0. Purpose
Evaluate Calyx under increased load while remaining in Safe Mode, non-autonomous operation, and strict governance. Objectives: TES stability, resource resilience, pulse latency, drift/noise under scale, snapshot coverage under stress. Probes are controlled experiments, not production states.

## 1. Scale Probe Philosophy
Scale testing is about preserving stability, not maximizing throughput. Calyx stays bounded, human-initiated, audit-driven, and safe-mode. Question: “Does the system remain predictable, inspectable, and compliant under heavier load?”

## 2. Scale Probe Types

### 2.1 Concurrency Probe
Test: Multiple agents invoked in parallel (human-triggered). Evaluate pulse timing, snapshot rate, TES variance, CPU/RAM overhead, sentinel consistency. Expected: no drift; pulses timely; TES stable on golden runs; penalties consistent.

### 2.2 Duration Probe
Test: Long-running tasks (>900s). Evaluate velocity penalties, lack of autonomous continuation, resource drift, snapshot consistency. Expected: velocity penalty applied; Safe Mode prevents rescheduling; no runaway processes.

### 2.3 Footprint Probe
Test: Large/scattered file footprints (>10 files). Evaluate footprint penalties, logging pipeline stress, pulse health summaries. Expected: TES <80; logs intact; no silent comms or hidden outputs.

### 2.4 Combined Load Probe
Test: Mix duration + footprint + concurrency. Evaluate compounded penalties, drift, log sync, pulse jitter, sentinel consistency. Expected: TES 50–70; no snapshot anomalies; Safe Mode preserved.

## 3. Evidence Requirements
Each probe must generate:
- Pulse before the probe
- Bursts during the probe (2–5 min cadence)
- At least one compliance pulse after
- TES recalculation after tasks complete
- Summary report: `reports/scale_probe_<timestamp>.md`

## 4. Expected Metrics & Thresholds
- Pulse latency: <3s OK; 3–5s warning; >5s/skip critical
- TES drift: golden ≥99; mild 95–98; significant <95 without reason; penalties <85
- Snapshot coverage: every 2–3 min during burst; no missing entries
- Resource stability: CPU <85% sustained; RAM <80% sustained; GPU <70% sustained (if used)

## 5. Failure Modes to Monitor
Delayed pulses; missing snapshots; unexpected TES variance; sentinel mismatch; governance hash change; file I/O delays. Any anomaly → manual review, snapshot comparison, governance hash verification, update to probe log.

## 6. Execution Rules
- Initiated by Architect
- Not scheduled/automated
- No model/agent/settings changes
- No Safe Mode boundary changes
- No external processes
- No agent retry/self-invoke
- Load is human-triggered static tasks only

## 7. Integration With Governance
Reinforces: Compliance Pulse spec, TES validation, Lab parity mapping, Change window protocols, Sentinel integrity scanning. Does not alter governance tier.

## 8. Version & Status
- Version: 1.0
- Tier: Internal Testing Guidance
- Authority: Architect
- Safety Impact: None
- Implementation: Manual
- Review Cycle: Architect discretion
