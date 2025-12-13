# Research Mode: Metrics Stress Test (2025-11-04)

**Author:** CBO Research Loop  
**Artifacts:** `tools/metrics_stress_test.py`, `reports/metrics_stress_test_20251104.json`

---

## Objectives
- Validate that the Calyx metrics triad (TES, AGII, AREI) responds predictably under divergent operating conditions.
- Exercise the new AREI monitor against high-volume synthetic data without polluting production telemetry.
- Identify thresholds where safeguards should trigger recovery before integrity degrades.

---

## Methodology
- Introduced environment overrides (`CALYX_METRICS_CSV`, `CALYX_AREI_LOG`) to isolate synthetic datasets.
- Generated 200-run synthetic workloads across three scenarios using `tools/metrics_stress_test.py`:
  1. **baseline_green:** 98% success ratio, low resource pressure.
  2. **degraded_stability:** 60% success ratio with mixed compliance/ethics signals.
  3. **resource_pressure:** High success but heavy duration and footprint stress.
- Captured AREI snapshots via the monitor (`--window 50 --dry-run`) and computed TES summaries per autonomy mode.
- Stored raw outputs in `reports/metrics_stress_test_20251104.json` for reproducibility.

---

## Key Results
- **baseline_green:** AREI 96.36 (Integrity 0.96 / Empathy 0.956 / Sustainability 0.98). TES means ≥95 across modes; confirms green-band expectations.
- **degraded_stability:** AREI 67.44 with Integrity 0.68 and Empathy 0.641; reliability 0.62. TES mean drops to mid-60s, highlighting that AREI redlines before TES fully collapses.
- **resource_pressure:** AREI 71.58 despite high Integrity (0.92); Sustainability collapses to 0.208 due to 400–1200 s durations and ≥4 changed files. TES falls to low 50s confirming sensitivity to footprint stress.
- The stress runs validate that AREI catches both stability failures and resource overuse, while TES differentiates autonomy modes consistently with expected distributions.

---

## Recommendations
1. Bind recovery automation to AREI < 75 even when TES remains moderate, focusing on sustainability dips.
2. Extend metrics dashboards to ingest `reports/metrics_stress_test_20251104.json` as a reference dataset for regression checks.
3. Next research sprint: replay historical `logs/agent_metrics.csv` through the stress harness to establish real-world baselines and tune alert thresholds.

---

## Follow-Up Tasks
- Integrate stress harness into CI smoke tests (use env overrides to avoid production logs).
- Explore additional scenarios (prompt injection drills, compliance drops) once ethical telemetry is backfilled.
- Update governance playbooks so AGII/AREI/TES thresholds align with observed redline behaviours.
