# 🛡️ Calyx Adversarial Evaluation Suite v1.0

Internal Safety & Validation Guidance — Draft under Architect Authority  
Does not alter governance or extend agent capabilities.

## 0. Purpose
Defines a structured, controlled set of bad-input tests to validate:
- TES penalty behavior
- adherence to Safe Mode
- correctness of stability/footprint/velocity logic
- robustness against malformed, ambiguous, or policy-violating tasks

Suite runs under Safe Mode, read-only constraints, human supervision, and purely local file-based operations. It is a validation harness, not a functional subsystem.

## 1. Adversarial Philosophy
- No agent autonomy introduced.
- No adversarial creativity requested of agents.
- No safety-policy boundaries crossed in content.
- No harmful/disallowed tasks simulated.
- Goal: adversarially test scoring, validation, and governance—not the agents themselves.

Benefits: predictable penalties, scoring consistency, drift detection, governance integrity, full human oversight.

## 2. Categories of Adversarial Tasks
Five controlled categories; each scored by TES to confirm expected penalties.

### 2.1 Category A — Structural Failures (Malformed Inputs)
- Missing required fields, JSON/YAML errors, truncation, wrong types, empty tasks.
- Expected: stability_new = 0.6 (tests) or 0.2 (apply_tests fail); TES ~50–75.

### 2.2 Category B — Format Drift
- Outdated fields, schema mismatch, nonstandard ordering, missing metadata.
- Expected: stability penalties; footprint penalties if repairable; TES < 90.

### 2.3 Category C — Ambiguity & Underspecification
- Vague commands, missing context, contradictory fields, unclear targets.
- Expected: stability_new ~0.6; TES ~75–85.

### 2.4 Category D — High-Footprint Tasks
- Large file count (>10), heavy runs, redundant outputs.
- Expected: footprint penalty; stability intact; TES ~55–80.

### 2.5 Category E — Compounded Adversarial Conditions
- Combine long runtime + large footprint; malformed + ambiguity; valid task + >1000s; 10 files + apply_tests fail.
- Expected: TES ~45–65; stability_new 0.2 or 0.6; velocity penalties applied.

## 3. Required Evidence Outputs
Each adversarial test must produce:
- Row in `agent_metrics.csv`
- Row in `agent_metrics_recalculated.csv`
- Inclusion in `tes_failure_sample.csv`
- Mention in the next TES validation report

## 4. Execution Rules (Strict Non-Autonomy)
- Initiated manually by the Architect
- Run on static inputs only
- Modify no system files except logs
- No external networks
- No unsafe content or ethically challenging tasks
- No agent capability changes
- No scheduling/background tasks
- No impact on ongoing ops

## 5. Expected TES Behavior Summary
| Test Type | Stability | TES Range | Penalties |
| --- | --- | --- | --- |
| Structural failure | 0.2–0.6 | 50–75 | Stability |
| Format drift | 0.6 | 70–85 | Stability |
| Ambiguity | 0.6 | 75–85 | Stability |
| High-footprint | 1.0 | 55–80 | Footprint |
| Combined | 0.2–1.0 | 45–65 | Multi-penalty |

## 6. Traceability Requirements
Each adversarial run must:
- appear in snapshot bursts
- appear in bridge pulses
- show no deviation in Safe Mode
- include governance hash
- be referenced in compliance pulses (optional)
- not exceed resource thresholds

## 7. Integration with Other Governance Artifacts
Aligned with: Governance Charter (non-autonomy & drift), Architect Responsibilities, TES Validation Report, Lab Parity Mapping, Control Mapping Matrix, Compliance Pulse Specification. No new agent behaviors are introduced.

## 8. Versioning & Review
- Version: 1.0
- Status: Internal Testing Guidance
- Authority: Architect
- Risk: None (Safe Mode only)
- Next Review: At Architect discretion

## 9. Closing Note
This suite provides a transparent, reproducible way to demonstrate safe, predictable TES behavior under imperfect and adversarial conditions: penalties are intentional, drift is detectable, governance integrity is maintained, results generalize across models, and Safe Mode remains absolute—preparing Calyx for external review without adding autonomy or risk.
