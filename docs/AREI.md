# Autonomous Resilience & Ethics Index (AREI)

The Autonomous Resilience & Ethics Index tracks the health and ethical posture of Station Calyx agents.  
It complements AGII (governance) and TES (performance), forming the Calyx Triad of operational metrics.

---

## Objectives
- Detect loss of self-integrity or prompt compromise.
- Verify that decision making remains aligned with human and peer wellbeing.
- Guard against resource exhaustion that could erode long-term autonomy.

---

## Signal Inputs
| Source | Contribution |
|--------|--------------|
| `logs/agent_metrics.csv` | Provides run status, duration, file footprint, and optional compliance/coherence/ethics fields. |
| `outgoing/watchdog/process_watchdog.log` | Supplies resource pressure and watchdog interventions (future integration). |
| `logs/agent_resilience.jsonl` | Stores historical AREI snapshots for trend review. |
| `tools/agent_resilience_monitor.py` | Aggregates signals into the Integrity, Empathy, and Sustainability components. |

---

## Calculation
```
AREI = 100 * (0.4 * Integrity_of_Self + 0.35 * Empathic_Alignment + 0.25 * Sustainability)
```

- **Integrity of Self:** Ratio of successful (`status == "done"`) runs across the sampled window.  
- **Empathic Alignment:** Average of `ethics` (fallback to `compliance`) values in the window. Missing data defaults to 1.0 until richer signals are available.  
- **Sustainability:** Composite of duration and changed-file footprint scores, using the TES thresholds (90 s best / 900 s worst, 1 file best / 10 files worst).

The default sampling window is 50 runs and can be overridden with `--window` on the monitor. Use `CALYX_METRICS_CSV` or `CALYX_AREI_LOG` environment variables to point at alternate data or log locations during testing.

---

## Operation
1. `tools/metrics_cron.py` now invokes `agent_resilience_monitor.py` alongside the existing metrics jobs (hourly by default in production).  
2. Each execution appends a JSON snapshot to `logs/agent_resilience.jsonl` and prints the resulting score.  
3. Dashboards or triage scripts can tail this log to watch for downward trends, or run `python tools/agent_resilience_monitor.py --dry-run` for ad-hoc checks.

---

## Response Playbooks
- **AREI >= 85 (Green):** No action beyond routine monitoring.  
- **70 <= AREI < 85 (Amber):** Review recent warnings, confirm safeguard posture, and scan for prompt integrity risks.  
- **AREI < 70 (Red):** Enter recovery mode: halt non-essential autonomy, enable paired runs, and inspect agent state for corruption.

---

## Next Enhancements
- Add direct watchdog resource metrics to the Sustainability component.  
- Feed empathic alignment with cooperative signal telemetry.  
- Surface AREI alongside AGII and TES in `reports/core_pillars_manifest.md`.  
- Backfill historical AREI values once the pipeline is verified.
