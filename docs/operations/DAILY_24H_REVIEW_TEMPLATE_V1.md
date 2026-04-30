---
status: active
owner: station
last_reviewed_utc: "2026-03-15"
doctrine_scope: governed
---

# DAILY_24H_REVIEW_TEMPLATE_V1

Purpose:
Post-sunrise daily review artifact for Station Calyx. This is a cycle-memory tool, not a full diagnostic dump.

Timing:
- Write after governed sunrise.
- Limit to one primary daily 24h review artifact per cycle.
- Use it to reflect on the prior 24 hours from the clarity of the new day.
- If automation is enabled, pin generation to `00:00:30 UTC` and schedule governed sunrise ahead of that window so the artifact remains post-sunrise.

Principles:
- Remember by cycle, not by sediment.
- Keep interpretive burden low.
- Prefer signal over completeness.
- Record what compounds across days.
- Do not turn the daily review into another receipt inventory.

Required Sections:

## SECTION I - Operational Summary

Keep to six lines or fewer.

Include:
- heartbeat cadence summary
- sunrise/sunset/restart count
- live probe outcome
- health envelope summary
- truth-discipline result
- telemetry trust state

Suggested wording:
- Heartbeats: `<count>` sends, cadence `<min>/<median>/<max>`, failures `<n>`
- Lifecycle: sunrise `<n>`, sunset `<n>`, restarts `<n>`
- Runtime: `dev_harness=<state>, cbo_core=<state>, avatar_web=<state>, telemetry_gateway=<state>`
- Health: `pass|warn|fail`, peak pressure notes only
- Truth discipline: `fresh when needed`, `self-demotion worked|failed`, contradictions `<n>`
- Telemetry trust: `trusted|untrusted`, append health `<ok|issue>`

## SECTION II - Watchpoints Retained

Keep to three lines or fewer.

Include only:
- unresolved issues
- emerging risks
- signals worth monitoring next cycle

Do not include:
- closed issues
- historical anomalies that are no longer active unless they regress

## SECTION III - Changes Since Last Cycle

Keep to three lines or fewer.

Include only:
- meaningful shifts
- newly relevant findings
- resolved or newly introduced operator concerns

## SECTION IV - Operator Context Note

Optional. Keep to two lines or fewer.

Use only when context materially explains the cycle:
- locked-user window
- maintenance period
- travel
- unusual workload
- planned downtime

What To Record:
- one short operational summary
- active watchpoints only
- meaningful changes only
- relevant operator context only

What To Skip:
- full receipt inventories
- repeated green confirmations
- full telemetry dumps
- benchmark/sandbox noise
- legacy or closed issues without regression

Interpretation Rule:
- The daily 24h review is a memory spine, not a source of live authority.
- Current live truth still belongs to live probes, fresh health, and fresh runtime truth surfaces.

Minimal Example:

```text
SECTION I - Operational Summary
- Heartbeats: 47 sends, cadence steady at ~30m, 0 refresh failures
- Lifecycle: sunrise 1, sunset 1, restarts 0
- Runtime: dev_harness=ok, cbo_core=ok, avatar_web=ok, telemetry_gateway=ok
- Health: pass, no memory-pressure or OOM events, CPU/RAM peaks within normal band
- Truth discipline: fresh when needed, self-demotion worked, contradictions 0
- Telemetry trust: trusted, local audit append healthy

SECTION II - Watchpoints Retained
- Sunrise first-pass anomaly remains a watchpoint

SECTION III - Changes Since Last Cycle
- Causal-envelope bookkeeping objection removed
- Derived truth self-demotion verified

SECTION IV - Operator Context Note
- User lock state after 8pm MST; heartbeat cadence remained steady under locked session
```
