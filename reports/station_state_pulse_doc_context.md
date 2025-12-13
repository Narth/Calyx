# Station State Pulse Report – Documentation Context

## 1. Core Architecture Snapshot
| Aspect | Details |
| --- | --- |
| Top-level structure | Directories include 	ools/, logs/, outgoing/, eports/, docs/, config/, scripts/; 	ools/ hosts operational scripts, config.yaml holds runtime policy, outgoing/ carries locks/dispatch files. |
| Scheduler cadence | 	ools/agent_scheduler.py interval baseline 150 s; adaptive loop currently reports next launch in ~360 s with 100 % success over last 50 runs. |
| Agent status | Active locks: utonomy_monitor, 
avigator, svf, sysint, 	riage (updated <24 h). Dormant: utonomy_runner, cp19, cp20, gent1 (older timestamps). |
| Message bus | File-based dispatch (outgoing/bridge/dispatch/*.json), heartbeat JSON locks under outgoing/. |
| Memory management | Context rehydration trims logs/autonomy_decisions.jsonl to recent 20 entries, archives legacy rc codes, merges run logs into logs/context_digest.jsonl on demand. |

- Notes: Core loops (watchdog, scheduler, autonomy monitor) are supervised via Windows scheduled tasks; memory guard restored to 78 % ceiling after refresh.

## 2. Task Evaluation System (TES) Implementation
| Aspect | Details |
| --- | --- |
| Formula | TES = 100 * (0.5*Stability + 0.3*Velocity + 0.2*Footprint). Stability considers status/failure context; velocity maps 90s→1.0, 900s→0.0; footprint maps ≤1 file→1.0, ≥10→0.0 (	ools/agent_metrics.py). |
| Storage | Per-run data appended to logs/agent_metrics.csv; granular entries logged to logs/granular_tes.jsonl. |
| AGII linkage | Observability phase reads TES averages for reliability reporting; otherwise TES logic independent. |
| Known issues | None active; hint system suggests autonomy escalation when stability ≥0.8. |

- Notes: Latest 20-run TES average ≈ 97.02; CSV headers include status, duration, mode, hint for auditability.

## 3. AGII Runtime Implementation
| Aspect | Details |
| --- | --- |
| Metric windows | Reliability uses last 50 un_complete events (success/total). Observability checks WARN ratio & memory skips over same window plus LLM latency. Safeguards counts watchdog actions/apply mode flag. |
| Data sources | Pulls from logs/autonomy_decisions.jsonl, logs/agent_metrics.csv, outgoing/watchdog/process_watchdog.log. |
| Reporting | 	ools/observability_phase1.py writes Markdown (eports/agii_report_YYYYMMDD.md, eports/agii_report_latest.md) and appends alerts to outgoing/observability_alerts.log. |
| Thresholds | ≥90 green, 70–89 amber, <70 red (applied per dimension and overall). Latest run: Reliability 100, Observability 100, Safeguards 87.5 (green). |

- Notes: AGII refresh triggered manually post-cleanup and nightly by observability scheduled task.

## 4. Observability Layer
| Aspect | Details |
| --- | --- |
| Logging | Primary logs under logs/ (agent_metrics.csv, autonomy_decisions.jsonl, beta_feedback.jsonl), watchdog outputs under outgoing/watchdog/, scheduled task logs under outgoing/tasks/*.log. Rotation handled by watchdog autorepair and manual archive scripts. |
| Dashboards | Static HTML dashboard at eports/live_dashboard.html; AGII & reliability reports for snapshot review; no external telemetry endpoints. |
| Latency metrics | LLM p95 currently 69.6 s (p50 69.6 s); queue skips 0 %; memory guard warns if >78 %. |

- Notes: Observability task (`Calyx Observability Snapshot`) regenerates metrics on schedule; outputs stored for offline review.

## 5. Safeguards & Permissions
| Aspect | Details |
| --- | --- |
| Watchdog | 	ools/process_watchdog.py --apply --once executed hourly via scheduled task; summaries in outgoing/watchdog/process_watchdog.log. |
| Apply mode | Scheduler runs in supervised apply-tests; watchdog apply mode terminates stale processes only (no autonomous file writes). |
| Sandboxing | Network default OFF (per harness); filesystem scope limited to C:\Calyx_Terminal\ workspace. |
| Overrides | Emergency stop via removing authority gates (outgoing/gates/*.ok) and disabling scheduled tasks; manual scripts (Grant-CBOAuthority.ps1, Start-AdaptiveSupervisor.ps1) manage privileges. |

- Notes: Safeguards score lifted after rc 127 archival; remaining watchdog candidates tracked per run.

## 6. Versioning & Sync
| Aspect | Details |
| --- | --- |
| Core baseline | eports/core_agent_baseline.md records hashes (config.yaml, scheduler, etc.) and notes missing configs. |
| Manifest | eleases/core_agent_v1_manifest.md captures module checksums, schema summary, TES baseline 97.02. |
| Last update | Scheduler last modified 2025-10-29 19:49; AGII report regenerated 2025-10-30 02:48Z. |
| Schema versions | TES CSV header unchanged since 2025-10-22; AGII schema implicit via observability report. |
| Pending work | Core + Agent consolidation window (4 h) scheduled before public beta; experimental beta logging (--beta-log) now available. |

- Notes: Maintain manifest & baseline updates whenever modules change to ensure downstream reproducibility.

## 7. Documentation Readiness
| Aspect | Details |
| --- | --- |
| Current docs | Key files: docs/CBO.md, docs/AGENT_WATCHER.md, docs/beta_onboarding_template.md. |
| Gaps | Need refresh for README/CONFIG sections describing new observability flow; SECURITY.md not present. |
| Public-ready artifacts | Reports in eports/ (bridge pulse, AGII, reliability), manifests, baseline snapshots. |
| Internal-only paths | logs/, outgoing/, memory/, raw task logs under outgoing/tasks/ should remain private. |

- Notes: Documentation update backlog includes README integration of beta logging toggle and observability instructions.

