# Station Calyx - Bridge Pulse Report

Timestamp: 2025-12-04 20:54:42
Pulse ID: bp-0031
Operator: CBO
Report Agent: bridge_pulse_generator
Directive Context: Maintain system uptime > 90% over 24h

## 1. Core Metrics
| Metric | Value | Threshold | Status |
| --- | --- | --- | --- |
| Uptime (24h rolling) | 100.0% | > 90% | OK |
| Samples (24h) | 153 | > 0 | OK |
| Mean TES | 90.2 | >= 95 | Attention |
| CPU Load Avg | 25.0% | < 70% | OK |
| RAM Utilization | 66.3% | < 75% | OK |
| GPU Utilization | 0.0% | < 85% | OK |
| Active Agents | 5 | <= configured limit | OK |

## 1.a Governance & Provenance
- Intent: health_pulse
- Respect frame: neutral_observer
- Provenance: {"trigger": "manual_run", "agent": "bridge_pulse_generator", "source_files": ["C:\\Calyx_Terminal\\logs\\agent_metrics.csv", "C:\\Calyx_Terminal\\logs\\system_snapshots.jsonl", "C:\\Calyx_Terminal\\outgoing\\cbo.lock"]}
- Causal chain: snapshots + cbo.lock metrics -> bridge_pulse_generator -> markdown report
- Reflection window: {"evidence": "153 snapshots (24h); see events list", "risk": "Low; report-only action", "next_checks": "Review TES if <95; refresh heartbeat if stale"}

## 2. System Events (last pulse)

[2025-12-05T03:54:00.5796121Z] System snapshot: 12 Python processes
[2025-12-05T03:17:50Z] CBO heartbeat pulse

## 3. Alerts and Responses
| Alert ID | Severity | Trigger | Response | Resolved |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 4. Learning & Adjustments

Observation: System operating within guardrails with active monitoring.

Action Taken: Generated bridge pulse report and refreshed telemetry.

Result: Baseline metrics captured for the current research session.

Confidence Level: Initial measurement for this session.

Notes: Clean template and ASCII-safe output confirmed.

## 5. Human Oversight
| Field | Entry |
| --- | --- |
| Last human logoff | 2025-12-04 20:54:42 |
| Expected return | N/A |
| Manual overrides since last pulse | 0 |
| manual_shutdown.flag detected | No |

## 6. Summary

During this pulse, Station Calyx maintained operational integrity within defined parameters. Primary directive compliance: 100.0%. System samples analyzed: 153. Overall status: Amber.