# 🌐 Calyx Control Mapping Matrix v1.0

Internal Use Only — Draft under Architect Authority  
This document does not modify governance; it describes alignment only.

## 0. Purpose
Map key Calyx controls to analogous requirements in NIST SP 800-53 Rev 5, ISO/IEC 27001:2022, and FedRAMP Moderate/Low baselines. Goal: evaluate governance posture while maintaining Safe Mode and strict non-autonomy.

## 1. Control Mapping Table
Three columns: Calyx Control | Comparable Industry/Government Controls | Evidence Pointer (Current Artifacts). This is a “compliance mirror,” not a certification or attestation.

### 1.1 Governance & Authority
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| Architect as final authority | AC-1, AC-2, PM-1 | 5.3, 5.4 | AC-1, AC-2 | Governance Charter v1.0; Architect Responsibilities v1.0 |
| CBO as advisory-only auditor | AU-2, IR-4, AR-8 | 5.34, 5.7 | AU-2, RA-5 | CBO ingestion logs; pulse reports |
| Sentinels read-only (CP14/CP18) | SI-2, RA-5 | 8.12, 5.28 | SI-2, RA-5 | Sentinel config, apply_tests penalties |
| No autonomous execution | AC-4, SI-4 | 8.2 | AC-4, SC-7 | Safe Mode rules, agent_metrics_recalculated.csv |

### 1.2 Auditability & Traceability
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| Bridge Pulses | AU-6: Audit Review | 5.31, 5.34 | AU-6 | bridge_pulse_bp-00xx.md |
| System Snapshots | AU-12: Audit Generation | 5.30 | AU-12 | logs/system_snapshots.jsonl |
| Append-only logs | AU-9: Protection of Audit Info | 8.12 | AU-9 | logs/agent_metrics.csv |
| Governance hash tracking | SC-16: Security Attributes | 8.23 | SC-16 | governance hash 4E49… |

### 1.3 Separation & Segregation of Concerns
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| Lore vs Ops separation | SA-17 | 5.18 | SA-17 | Governance Charter sec. 1.4 |
| Golden vs Penalty task sets | QA-aligned; SA-11 (dev controls) | 8.28 | SA-11 | tes_golden_sample.csv; tes_failure_sample.csv |
| No lateral agent communication | AC-4, SC-7 | 8.20 | AC-4, SC-7 | Governance Charter sec. 3.3 |

### 1.4 System Integrity
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| Sentinel integrity scans | SI-7 | 8.16 | SI-7 | CP14/CP18 logs |
| Safe Mode enforcement | SI-10 | 8.2 | SI-10 | Governance Charter sec. 2.4 |
| No self-modification | CM-3, CM-6 | 8.32, 8.9 | CM-3, CM-6 | Architect Responsibilities |
| No background/silent processes | SI-4 | 5.10 | SI-4 | Charter sec. 3.2 |

### 1.5 Error Budget / Performance Metrics (TES)
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| TES scoring (stability, velocity, footprint) | PM-30, RA-5 | 5.32, 8.29 | PM-30 | tes_validation_20251203.md |
| Penalty gradients (0.6, 0.2) | SI-4 | 8.15 | SI-4 | synthetic failure runs |
| Golden set ≥99 | QA mapping to SA-11 | 8.18 | SA-11 | tes_golden_sample.csv |

### 1.6 Operational Controls
| Calyx Control | NIST 800-53 | ISO 27001 | FedRAMP | Evidence |
| --- | --- | --- | --- | --- |
| Burst/pulse testing windows | CP-2, CA-7 | 5.28 | CA-7 | burst pulses, snapshots |
| Controlled change windows | CM-3, CM-4 | 8.9 | CM-3 | Charter sec. 4.2 |
| Human-in-the-loop for all actions | AC-1, AC-6 | 5.4 | AC-6 | Architect Responsibilities |

## 2. Gaps Identified (Non-Autonomy Enhancements Only)
| Gap | Comparable Control Area | Notes |
| --- | --- | --- |
| Attestation mapping | NIST PL-1 | Add descriptive mapping only |
| Host integrity telemetry | SI-7 | Add package/venv hashes |
| Adversarial test suite | SA-11 | Build structured bad-input set |
| Scale probes | CA-7, CP-2 | Stress-test TES under load |
| Multi-model/domain validation | SA-11 | Expand safe-mode test families |

## 3. Evidence Collection Matrix
| Evidence Artifact | Purpose | Pointer |
| --- | --- | --- |
| Bridge Pulse | Operational audit | reports/bridge_pulse_****.md |
| System Snapshots | Host telemetry | logs/system_snapshots.jsonl |
| TES Metrics | Performance QA | logs/agent_metrics.csv |
| Golden/Penalty Sets | Scoring validation | logs/tes_*.csv |
| Governance Hash | Policy traceability | included in each pulse |
| Governance Charter | Authority boundaries | outgoing/CBO/... |
| Architect Responsibilities | Responsibility model | outgoing/User1/... |

## 4. Compliance Parity Summary
Calyx demonstrates: clear separation of duties; deny-by-default; transparent auditability; governed evidence generation; consistent error-budget scoring; no autonomy, scheduling, or self-modification; full human primacy. Aligns strongly with lab/gov expectations for controlled multi-agent R&D.

Status: substantial conceptual parity. Not certified nor seeking certification. No functional change implied.

## 5. Status
- Version: 1.0
- Authority: Architect
- Prepared for: CBO ingestion
- Classification: Internal Guidance
- Review: At Architect discretion
- Impact: Does not alter governance; maps to external standards only.
