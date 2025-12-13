# Calyx Compliance Pulse ? 20251204T025949Z

## 1. Governance Traceability
- Governance Charter: outgoing/CBO/calyx_governance_charter_v1.md
- Responsibilities: outgoing/User1/Architect Responsibilities & System Constraints v1.0.md
- Lab Parity Mapping: reports/calyx_lab_parity_mapping_v1.0.md
- Control Mapping Matrix: reports/calyx_control_mapping_matrix_v1.0.md
- Adversarial Suite: reports/calyx_adversarial_evaluation_suite_v1.0.md
- Governance hash: 4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7

## 2. System Health
- Latest bridge pulse: reports/bridge_pulse_burst-20251204T025453.md
- Snapshot hash (last entry): c55a2e6cdc664c5a5362ec08cbdf76ed3f72665c9b65405facf77a6f1ba4ec7a
- Snapshot entry: {\"timestamp\": \"2025-12-04T02:59:40.5539804Z\", \"count\": 6, \"note\": \"burst snapshot 43\"}
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

## 5. Integrity Attestation
- Latest attestation: reports/integrity_attestation_20251204T025840Z.md
- Snapshot checksum: c55a2e6cdc664c5a5362ec08cbdf76ed3f72665c9b65405facf77a6f1ba4ec7a
- Package freeze hash: see latest attestation
- Python binary hash: see latest attestation
- Site-packages aggregate hash: see latest attestation

## 6. Compliance Mapping
- NIST/ISO/FedRAMP analogs: reports/calyx_control_mapping_matrix_v1.0.md

## 7. Scale Probe Reference
- Latest scale probe report: reports/scale_probe_20251204T0300Z.md
- Probe pulses: see scale probe report
- Burst snapshots present (see system_snapshots.jsonl)

## 8. Change Window Summary
- Changes since last compliance pulse: attestation integrity_attestation_20251204T025840Z.md, scale probe scale_probe_20251204T0300Z.md
- Recent bursts: included in scale probe
- Drift detected: None observed in current artifacts

Filed by: Architect
Audited by: CBO
