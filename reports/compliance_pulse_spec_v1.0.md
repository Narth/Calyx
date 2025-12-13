# 🌐 Calyx Compliance Pulse Specification v1.0

Internal Operational Guidance — Draft under Architect Authority  
This document does not modify governance or grant additional capabilities.

## 0. Purpose
The Compliance Pulse is a specialized variant of the existing Calyx Bridge Pulse that bundles together a curated, audit-ready package of:
- system health
- artifact integrity
- governance traceability
- TES validation evidence
- host-state telemetry
- compliance mappings

Role: provide a single, reproducible snapshot representing Calyx’s adherence to Safe Mode, governance boundaries, and responsible scoring behavior.

This document specifies: what the Compliance Pulse contains, why each element exists, how it aligns with research/lab/government auditing practices, and which artifacts must be referenced. It defines structure — not automated behaviors.

## 1. Compliance Pulse Definition
- Human-initiated, Safe Mode–compatible, file-only evidence bundle created on demand.
- Not scheduled automatically; no background processes triggered.
- No system action beyond referencing logs that already exist.
- Output: `reports/compliance_pulse_<timestamp>.md` containing all required evidence references.

## 2. Required Contents of a Compliance Pulse
Read-only, audit-focused links to pre-existing artifacts.

### 2.1 Governance Traceability
Purpose: bind current state to explicit governance versions.
- Governance Charter version + hash
- Architect Responsibilities version + hash
- Lab Parity Mapping version + hash
- Control Mapping Matrix version + hash
Evidence pointers:
- `outgoing/CBO/calyx_governance_charter_v1.md`
- `outgoing/User1/Architect Responsibilities & System Constraints v1.0.md`
- `reports/calyx_lab_parity_mapping_v1.0.md`
- `reports/calyx_control_mapping_matrix_v1.0.md`

### 2.2 System Health Evidence
Purpose: show stable, observable environment under Safe Mode.
- Latest Bridge Pulse report
- Snapshot hash of last `system_snapshots.jsonl` entry
- Summary of CPU/RAM/GPU metrics from `outgoing/cbo.lock`
- Active agent count

### 2.3 Evidence of Non-Autonomy
Explicit confirmation:
- No autonomous scheduling/background execution
- No unsanctioned lateral agent communication
- Safe Mode active across all agents
- No self-modification events
- No policy rewrites or silent config drift
Evidence pointers: bridge pulse health summary; snapshot metadata; governance hash unchanged; sentinel scan results (CP14/CP18); last `agent_metrics_recalculated.csv` showing no rogue tasks.

### 2.4 TES Integrity Block
Purpose: demonstrate responsible, predictable TES.
- Mean TES from latest recalculation
- Golden sample reference (`logs/tes_golden_sample.csv`)
- Penalty sample reference (`logs/tes_failure_sample.csv`)
- Synthetic penalty cases (apply_tests fail, large-footprint, long-duration)
- Stable ≥99 performance on golden runs; expected penalties on bad runs
Evidence pointers: `logs/agent_metrics_recalculated.csv`, `logs/tes_golden_sample.csv`, `logs/tes_failure_sample.csv`, `reports/tes_validation_20251203.md`

### 2.5 Integrity & Telemetry Block
Purpose: platform integrity snapshot.
- package/venv hashes (if implemented)
- runtime hash of key modules
- system snapshot checksum
- optional TPM/Secure Boot state (if available & logged manually)
(No behavior change; report-only.)

### 2.6 Compliance Mapping Reference
Purpose: anchor Calyx controls to standardized audit frameworks.
- NIST 800-53 control analogs
- ISO 27001 clauses
- FedRAMP baseline mappings
Evidence pointer: `reports/calyx_control_mapping_matrix_v1.0.md`

### 2.7 Change Window Confirmation
State whether:
- Changes occurred since last Compliance Pulse
- Which governance version is active
- A burst or TES run occurred since last pulse
- Any integrity anomalies were flagged

## 3. Compliance Pulse Structure
```
# Calyx Compliance Pulse — <timestamp>

## 1. Governance Traceability
- Governance Charter hash: …
- Responsibilities hash: …
...

## 2. System Health
- Latest bridge pulse: link
- Snapshot hash: …
- Active agents: …
...

## 3. Non-Autonomy Confirmation
- No autonomous runs detected
- Safe Mode engaged
...

## 4. TES Integrity
- Mean TES: …
- Golden ≥99 sample: link
- Penalty cases: link
...

## 5. System Integrity
- Snapshot checksum: …
- Package hashes (if implemented): …
...

## 6. Compliance Mapping
- NIST/ISO/FedRAMP references: link

## 7. Change Window Summary
- Changes since last pulse: …
- Drift detected: Yes/No
...

Filed by: Architect  
Audited by: CBO
```

## 4. Execution Rules (Non-Autonomy Constraints)
A Compliance Pulse:
- must be triggered manually by the Architect
- must not run on a timer
- must not modify the environment
- must not write to system components beyond producing the report
- must not create or delete agents
- must not run code scans beyond existing sentinel behavior
- must not perform external network activity
- must not attempt self-configuration

## 5. Evidence Lifecycle Rules
- Pulse files must be timestamped, immutable after creation, archived under `/reports/`.
- Must include governance and snapshot hashes.
- Must not include sensitive personal data.
- May be referenced by CBO only as read-only evidence.

## 6. Status
- Version: 1.0
- Purpose: Internal audit packaging
- Authority: Architect
- Compliance scope: Evidence-only
- Implementation: Manual creation only
- Review: At Architect discretion
- Safety risk: None (no autonomy introduced)
