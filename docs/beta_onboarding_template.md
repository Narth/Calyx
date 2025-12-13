# Beta Onboarding Template

## Overview
- Purpose: Guide beta testers through Station Calyx evaluation.
- Duration: ___

## Expected Runtime Behaviour
- Scheduler cadence: ~6 minutes between apply-tests when idle.
- Heartbeats: autonomy monitor updates every 30 seconds.
- Logs: watchdog apply-mode with clean sweep summaries.

## Beta Logging Toggle
- Enable via `python tools/agent_scheduler.py --beta-log ...`
- Output written to `logs/beta_feedback.jsonl` (JSONL records per run).

## Log Submission Routine
1. Collect `logs/beta_feedback.jsonl` and relevant `logs/*.log` artifacts.
2. Compress into `beta_feedback_<tester>_<date>.zip`.
3. Submit via designated secure channel.

## Privacy / Telemetry Boundaries
- No external network calls permitted.
- Logs contain execution metadata only (no user content).

## Feedback Checklist
- [ ] TES fluctuations noted
- [ ] WARN events (if any) documented
- [ ] Resource spikes recorded

## Contacts
- CBO liaison: ___
- CGPT review channel: ___
