🛰 Station Calyx — Phase II Launch Manifest

Document ID: phase_ii_partial_launch.md
Generated: 2025-10-24
Authorizing Officer: User1 (Jorge Castro)
Consulting Agents: Cheetah Agent | Calyx Bridge Overseer (CBO)
Reference Plan: tools/plans/phase_ii_infra.md
Feasibility Review: reports/cbo_phase_ii_feasibility_review.md

1 Objective

Authorize activation of low-impact infrastructure improvements while system capacity normalizes.
Phase II focuses on expanding memory, analytics, coordination, and visibility without exceeding current CPU/RAM limits.

2 Authorized Tracks for Immediate Execution
Track	Title	Purpose	Status
A	Persistent Memory & Learning Loop	Create experience.sqlite, enable recall, nightly compaction	✅ Approved
D	Bridge Pulse Analytics	Parse logs, generate trends, feed confidence Δ data	✅ Approved
E	Multi-Agent Protocol (SVF 2.0)	Introduce atomic manifest flow and ack system	✅ Approved
G	Human Interface Upgrade	Deploy local dashboard for uptime/TES/alerts	✅ Approved
3 Deferred Tracks (pending capacity normalization)

| Track | Title | Activation Condition |
|:--|:--|
| B Autonomy Ladder Expansion | CPU < 50 % for 24 h and TES ≥ 95 for 5 pulses |
| C Resource Governor | CPU < 50 %, RAM < 75 %, capacity score > 0.5 |
| F Safety & Recovery Automation | Governor active + playbooks validated offline + human sign-off |

4 Implementation Directives

Execute authorized tracks in the order A → D → E → G.

Log each activation event in the next Bridge Pulse report.

Schedule heavy tasks only when CPU < 40 %.

Postpone new agent spawns until capacity normalization is confirmed.

Maintain full rollback snapshots before each deployment.

5 Human Oversight Protocol

CBO to request written confirmation before promoting any deferred track.

Manual shutdown flag remains active as master halt signal.

Weekly Bridge Pulse Review meeting (virtual or asynchronous log) required.

6 Success Metrics for Partial Launch
KPI	Target	Review Window
Uptime (rolling 24 h)	≥ 95 %	Daily
Mean TES	≥ 96	Every Bridge Pulse
RAM Utilization	≤ 75 %	Continuous
Policy Violations	0	Continuous
Confidence Δ growth	≥ +1 %/day	Weekly