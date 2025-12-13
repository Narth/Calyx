# Calyx Core Pillars Manifest
Generated: 2025-11-04T05:33:32Z

## Pillar Summary
| Pillar | Latest Score | Status | Primary Source |
|--------|--------------|--------|----------------|
| **AGII** | 97.0 | Green | `reports/agii_report_latest.md` |
| **TES** | 96.95 (avg last 50) | Green | `reports/agii_report_latest.md` |
| **AREI** | 98.72 | Green | `logs/agent_resilience.jsonl` |

---

## Autonomous Governance Integrity Index (AGII)
- Reliability: 100.0 (window 50 runs)  
- Observability: 91.0 (warn ratio 3.57%)  
- Safeguards: 100.0 (apply-mode enabled, watchdog actions 0)  
- Latest alert: 2025-11-03T01:49:32Z :: Observability thresholds within guardrails.

AGII remains in the green band (>= 90). Continue nightly refresh via the Calyx Observability Snapshot.

---

## Task Evaluation Scoring (TES)
- Latest TES: 97.20 (from `reports/autonomy_observability_status.md`)  
- Mean TES (last 50): 96.95  
- Velocity and footprint components tracking above 0.9.  
- v3 schema prepares to incorporate compliance, coherence, and ethics signals already logged in `logs/agent_metrics.csv`.

Action: execute v3 integration tests once AREI telemetry has two full days of coverage.

---

## Autonomous Resilience & Ethics Index (AREI)
- Latest snapshot (50-run window):  
  - Integrity of Self: 1.00  
  - Empathic Alignment: 1.00  
  - Sustainability: 0.949  
  - AREI Score: 98.72  
- Status counts: `{"done": 50}`

Action: confirm `tools/metrics_cron.py` is running on the hourly cadence and ingest `logs/agent_resilience.jsonl` into dashboards.

---

## Bloom Readiness
- Bloom plan activated (see `docs/AUTONOMY_BLOOM_PLAN.md`). Scheduler cadences tightened and Agent4 re-enabled for multimodal drills.  
- Autonomy gates: AGII >=95, TES >=95, AREI >=90, WARN <=5%. All criteria currently satisfied.
- Guardrail hook: If WARN ratio exceeds 5% or any pillar dips below threshold, revert to research templates and pause promotions.
