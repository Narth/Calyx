# Station Calyx - Bridge Pulse Report

Timestamp: 2025-12-07 00:32:54
Pulse ID: burst-20251207T073254
Operator: CBO
Report Agent: bridge_pulse_generator
Directive Context: Maintain system uptime > 90% over 24h

## 1. Core Metrics
| Metric | Value | Threshold | Status |
| --- | --- | --- | --- |
| Uptime (24h rolling) | 99.2% | > 90% | OK |
| Samples (24h) | 131 | > 0 | OK |
| Mean TES | 90.2 | >= 95 | Attention |
| CPU Load Avg | 18.4% | < 70% | OK |
| RAM Utilization | 96.3% | < 75% | Attention |
| GPU Utilization | 0.0% | < 85% | OK |
| Active Agents | 5 | <= configured limit | OK |

## 1.a Governance & Provenance
- Intent: health_pulse
- Respect frame: neutral_observer
- Provenance: {"trigger": "manual_run", "agent": "bridge_pulse_generator", "source_files": ["C:\\Calyx_Terminal\\logs\\agent_metrics.csv", "C:\\Calyx_Terminal\\logs\\system_snapshots.jsonl", "C:\\Calyx_Terminal\\outgoing\\cbo.lock"]}
- Causal chain: snapshots + cbo.lock metrics -> bridge_pulse_generator -> markdown report
- Reflection window: {"evidence": "131 snapshots (24h); see events list", "risk": "Low; report-only action", "next_checks": "Review TES if <95; refresh heartbeat if stale"}

## 2. System Events (last pulse)

[2025-12-07T07:32:54.4412714Z] System snapshot: 11 Python processes
[2025-12-06T21:17:27Z] CBO heartbeat pulse

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
| Last human logoff | 2025-12-07 00:32:54 |
| Expected return | N/A |
| Manual overrides since last pulse | 0 |
| manual_shutdown.flag detected | No |

## 6. Summary

During this pulse, Station Calyx maintained operational integrity within defined parameters. Primary directive compliance: 99.2%. System samples analyzed: 131. Overall status: Amber.