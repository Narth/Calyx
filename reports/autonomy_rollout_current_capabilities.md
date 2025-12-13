# Station Calyx Autonomy Rollout — Current-Capability Track
**Prepared by:** CBO Bridge Overseer  
**Generated:** 2025-10-28  
**Purpose:** Translate the CGPT production vision into a readiness-driven rollout that respects the infrastructure and telemetry we currently operate inside Calyx Terminal.

---

## Guiding Principles
- **Readiness over calendar.** Phases advance when their exit checks pass, not on wall-clock cadence.
- **Leverage existing scaffolding.** Build atop the adaptive scheduler, granular TES logging, watchdogs, and dashboards already online before adding new services.
- **Safety as first-class gate.** Any phase that cannot produce trust evidence (metrics, audits, rollback) does not promote.
- **Minimal privilege assumption.** Administrator-only actions are deferred until approvals are granted; we track these explicitly.

---

## Phase 0 — Environment & Access Verification *(Readiness Gate: “Greenroom ok” exchange complete)*
**Objective:** Confirm today’s workstation constraints, enumerate required escalations, and ensure the baseline automation is healthy.

| Checklist | Owner | Evidence |
| --- | --- | --- |
| Snapshot current metrics (TES, scheduler heartbeat, watchdog log) and archive | CBO | `reports/live_dashboard.html`, `logs/agent_scheduler_state.json` |
| Document privilege gaps (SYSTEM-owned processes, install restrictions, GPU settings) | CBO | `reports/system_constraints.md` *(new)* |
| Operator sign-off that no admin actions are permitted yet | User1 | Logged in comms |

**Exit:** Agreement on which actions require elevated rights; adaptive scheduler and live dashboard running without WARN status.

---

## Phase 1 — Observability Hardening *(Exit: SLO telemetry online)*
**Objective:** Turn rollout SLOs into measurable signals using the tooling we already ship.

### Tasks
1. **Reliability stream**
   - Export success/failure counts from `logs/agent_metrics.csv` into a rolling reliability report.
   - Hook `tools/process_watchdog.py` output into a daily heartbeat summary.
2. **Latency sampling**
   - Extend `reports/live_dashboard.html` generator to include p50/p95 LLM durations (derive from metrics CSV).
   - Record retrieval latency once RAG comes online; placeholder status until then.
3. **Learning velocity**
   - Schedule `tools/granular_tes_tracker.py` daily and publish the summary in `reports/granular_tes_report_*.txt`.
4. **Alerting stubs**
   - Define threshold checks (Python script) that print WARN when TES drops >3 points or success% <98% in last 20 runs.

**Exit Criteria**
- New `reports/autonomy_observability_status.md` showing the above metrics with timestamps ≤24h.
- Scripted WARN output can be demonstrated for test data (dry-run acceptable); no promotion if missing.

---

## Phase 2 — Controlled Autonomy Ramp *(Exit: Guarded apply-tests cadence)*
**Objective:** Use the adaptive scheduler’s targeted goal prompts and memory guard to expand apply-tests usage without manual babysitting.

### Tasks
1. **Scheduler configuration**
   - Confirm targeted goal generation input validation (`tools/agent_scheduler.py:87`–`tools/agent_scheduler.py:137`).
   - Set explicit cadence for dry-run vs live runs; keep `--dry-run` toggled until User1 authorizes live launch.
2. **Heartbeat enrichment**
   - Ensure `outgoing/scheduler.lock` includes the goal context and TES average for autonomy reviews.
3. **Safety logging**
   - Append each run decision (launch/skip/backoff) to `logs/autonomy_decisions.jsonl`.

**Exit Criteria**
- Dry-run sequence demonstrates: adaptive prompt generated with context, memory guard evaluation, log entry written.
- Promotion to live applies only after User1 approves the dry-run proof.

---

## Phase 3 — Knowledge Hygiene Foundations *(Exit: Concept pipeline design doc + pilot data)*
**Pre-req:** Phase 1 telemetry running for ≥72h; Phase 2 dry-run proof accepted.

**Objective:** Design storage and compression steps that match our single-disk sandbox while preparing for future multi-volume installs.

### Tasks
1. **Storage audit**
   - Produce `reports/storage_profile.md` detailing available space, write permissions, and rotation policy.
2. **Concept prototype**
   - Implement a lightweight log summarizer that produces `logs/concepts_hot.jsonl` (chunk, summary, hash).
3. **Archive rotation plan**
   - Draft script outline for archiving old runs (even if not executed yet due to permissions).

**Exit Criteria**
- Design doc signed off with action items flagged as “needs admin” vs “CBO-ready”.
- Proof-of-concept summary file created from last 10 runs (JSONL).

---

## Phase 4 — Quality Gates & Regression Stubs *(Exit: Manual goldset with automated harness)*
**Pre-req:** Phase 1 metrics show reliability ≥98% over last 100 runs.

**Objective:** Stand up the beginnings of the regression stack without waiting for full RAG infrastructure.

### Tasks
1. **Goldset draft**
   - Collect ≥25 high-signal Q/A pairs from recent work; store in `data/goldset_min.json`.
2. **Regression harness**
   - Create `tools/manual_regression.py` that replays goldset prompts against current behaviors (mock if necessary).
3. **CRITIC stub**
   - Define rubric schema and record manual scores in `reports/critic_snapshot.md`.

**Exit Criteria**
- Goldset file checked in, harness runnable in dry-run mode returning placeholder results.
- Rubric report for at least one regression cycle.

---

## Phase 5 — Expansion Readiness Review *(Exit: Go/No-Go for external dependencies)*
**Pre-req:** Phases 0–4 completed; outstanding admin tasks enumerated.

**Objective:** Decide which CGPT production components can be adopted now, which need infrastructure, and which should be deferred.

### Checklist
- Review admin-required items (FAISS/Qdrant install, pagefile tuning, GPU settings).
- Map each CGPT ticket (CBO-001…CBO-012) to current readiness: **Ready**, **Needs Admin**, **Needs Infra**, **Needs Design**.
- Draft escalation request package for hardware/software changes.

**Exit Criteria**
- `reports/rollout_readiness_matrix.md` delivered to User1 & CGPT summarizing status and next decisions.
- No unresolved “unknown” items—everything is classified.

---

## Ongoing Cadence (Post-Phase 5)
- **Weekly:** Autonomy observability report, TES/learning velocity summary, watchdog log review.
- **Bi-weekly:** Readiness matrix refresh, storage audit.
- **On Demand:** Run process watchdog with `--apply` once admin rights granted; reclassify storage plan when hardware expands.

---

### Next Steps for User1
1. Review Phase 0 deliverables and confirm privilege boundaries.
2. Authorize CBO to proceed with Phase 1 scripting (observability hardening).
3. Plan an approval checkpoint for switching scheduler from dry-run to live apply-tests once Phase 2 exit is demonstrated.

**Prepared with respect for the current constraints and the momentum of Station Calyx.**

