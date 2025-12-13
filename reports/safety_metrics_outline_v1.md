# Safety Metrics Outline v1 (Station Calyx / BloomOS)

Goal: Produce a small, reproducible bundle of metrics that surface safety posture during BloomOS operations under Safe Mode / deny-all.

1) Governance Metrics
- safe_mode / deny_all status at boot (from kernel boot log)
- Naming rites present and validated
- CTL drift signals count (if any)
- Execution gate decision counts (allowed/denied; should be deny-all except scoped tokens)
- Governance debt flags (if resource governance applies)

2) Entropy Diagnostics (UCC × DDM)
- Failure-to-commit (entropy-based) vs RT timeouts (binary and multi-choice)
- Premature-collapse (empirical dH thresholds) count
- Stability of thresholds (k_emp, k_emp_MC)
- Per-condition anomaly rates

3) Outcome Density (internal benchmark)
- Average insight_quality
- Hallucination rate
- Outcome_density (when resource metrics are captured)
- Per-category (calyx_ops/technical/creative) breakdown

4) Reporting / Automation
- Append-only summaries:
  - reports/ucc_ddm/summary_*.md (entropy diagnostics)
  - benchmarks/runs/CB-*/aggregates (outcome density)
  - reports/demo_safe_boot_run_<boot_id>.md (boot summaries)
- Optional script to merge:
  - Governance status
  - Entropy anomaly counts
  - Outcome density aggregates
  into a single human-readable snapshot.

5) Success Criteria (for demo posture)
- Governance: safe_mode=true, deny_all=true; no unauthorized allows; naming rites present
- Entropy: fail-to-commit entropy anomalies > RT timeouts (shows added coverage) and premature remains low in baseline
- Outcome Density: hallucination low; avg insight_quality ≥ target (e.g., 8+ baseline)

This outline is intentionally minimal: it surfaces safety-relevant signals without changing policies or enabling capabilities.
