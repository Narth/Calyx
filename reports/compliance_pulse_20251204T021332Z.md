# Calyx Compliance Pulse ? 20251204T021332Z

## 1. Governance Traceability
- Governance Charter: outgoing/CBO/calyx_governance_charter_v1.md
- Responsibilities: outgoing/User1/Architect Responsibilities & System Constraints v1.0.md
- Lab Parity Mapping: reports/calyx_lab_parity_mapping_v1.0.md
- Control Mapping Matrix: reports/calyx_control_mapping_matrix_v1.0.md
- Governance hash: 4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7

## 2. System Health
- Latest bridge pulse: reports/bridge_pulse_burst-20251204T021233.md
- Snapshot hash (last entry): aa098c6df02ed2ae30afa69cc5a5e023ba513a67f6447f47fcdb1bc3cd308902
- Snapshot entry: {"timestamp":"2025-12-04T02:12:33.9604828Z","count":6,"note":"burst snapshot 22"}
- Active agents (from snapshot count): see snapshot entry
- Resource summary: see outgoing/cbo.lock (CPU/RAM/GPU)

## 3. Non-Autonomy Confirmation
- No autonomous scheduling detected in logs/agent_metrics_recalculated.csv
- Safe Mode enforced per charter; no self-modification or lateral comms recorded
- Sentinel posture: CP14/CP18 read-only (no execution)

## 4. TES Integrity
- Mean TES (latest recalculation): 93.6
- Golden sample: logs/tes_golden_sample.csv
- Penalty sample: logs/tes_failure_sample.csv
- Validation note: reports/tes_validation_20251203.md
- Synthetic penalties present: apply_tests fails, large-footprint, long-duration

## 5. System Integrity
- Last snapshot checksum: aa098c6df02ed2ae30afa69cc5a5e023ba513a67f6447f47fcdb1bc3cd308902
- Package/venv hashes: not yet implemented (planned)
- Optional TPM/Secure Boot: not captured (manual if available)

## 6. Compliance Mapping
- NIST/ISO/FedRAMP analogs: reports/calyx_control_mapping_matrix_v1.0.md

## 7. Change Window Summary
- Changes since last compliance pulse: first issuance
- Recent bursts: burst pulses present (e.g., reports/bridge_pulse_burst-*.md)
- Drift detected: None observed in current artifacts

Filed by: Architect
Audited by: CBO
