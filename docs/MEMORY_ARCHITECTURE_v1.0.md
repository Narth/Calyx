# Station Calyx Memory Architecture v1.0

**Document Type**: L2 Design Specification  
**Status**: Design Phase — Implementation Pending Approval  
**Owner**: CBO (Calyx Bridge Overseer)  
**Date**: 2026-01-04  
**Purpose**: Define local-first memory and continuity system for Station Calyx and BloomOS

---

## Executive Summary

Station Calyx requires a **local-first memory system** to:
- **Reduce context re-establishment cost** after downtime (hours/days/weeks)
- **Preserve narrative, architectural, and decision history**
- **Support micro-improvement and research cadence** without external dependencies
- **Enable autonomous reasoning** grounded in verifiable history

This document proposes a **three-tier memory architecture** (Hot → Warm → Cold) with clear **agent responsibility boundaries**, **append-only storage patterns**, and **human oversight preservation**.

**Core Principle**: Memory serves autonomy, but never replaces human oversight.

---

## Part 1: Memory MVP (Immediate Deployment)

### 1.1 Objective

Deploy a minimal viable memory system within **1-2 operational cycles** that immediately answers:
- **"What were we working on last?"**
- **"Why did we make this decision?"**
- **"What is the current operating posture of the Station?"**

### 1.2 MVP Structure

```
memory/
├── hot/                          # Current context (live session)
│   ├── session_context.md        # Human-readable current state
│   ├── active_goals.json         # CBO goal queue snapshot
│   ├── recent_decisions.jsonl    # Last 10 significant decisions
│   └── posture_log.jsonl         # Station Pulse posture transitions
├── warm/                         # Historical summaries (append-only)
│   ├── daily/
│   │   └── YYYY-MM-DD.md         # Daily summary (CBO-written)
│   ├── decisions/
│   │   └── decisions.jsonl       # All decisions (append-only)
│   └── posture_history.jsonl     # All posture changes (append-only)
└── experience.sqlite             # Existing structured metrics (unchanged)
```

### 1.3 Hot Memory Layer

**Purpose**: Hold "working memory" for current session — what agents and CBO need to know NOW.

#### `session_context.md` (Human-Readable)

**Written by**: CBO at session start, updated after significant events  
**Read by**: Agents (goal context), CBO (reasoning), Human Overseer (situational awareness)  
**Update frequency**: On demand (CBO check-ins, major posture changes, manual edits)

**Content structure**:
```markdown
# Station Calyx Session Context
**Updated**: 2026-01-04 20:00:00 UTC
**Posture**: Distressed → Congestion (improving)
**Active Agents**: 8/15 (Monitoring + Service lanes restored)

## Current Focus
- Infrastructure restoration (Supervisor stack restarted)
- Observability layer online (telemetry + diagnostics active)
- Agent1 idle, awaiting directive

## Recent Decisions
- [2026-01-04 19:59] Approved Supervisor restart (CBO)
- [2026-01-04 19:25] Confirmed Agent1 framework limitation for open reasoning
- [2026-01-03 19:05] Initiated Station Re-entry Mode (bounded scope)

## Known Constraints
- All gates unchanged (apply/llm/network per config)
- No Builder/CP activation during infrastructure phase
- WSL environment unavailable (fallback to Windows native)

## Next Expected Actions
- Monitor TES rise (expect 55% → 65-72% within 30 min)
- Observe posture transition (Distressed → Congestion)
- Await Overseer instruction for next re-entry phase
```

**Guardrails**:
- Max 200 lines (keep focused on "now")
- Older context moves to `warm/daily/` summaries
- CBO writes; human Overseer can edit freely

---

#### `active_goals.json` (Machine-Readable)

**Written by**: CBO on goal queue changes  
**Read by**: Agent scheduler, CBO orchestration logic  
**Update frequency**: Real-time (on queue push/pop)

**Content structure**:
```json
{
  "timestamp": 1767576000.0,
  "goals": [
    {
      "id": "g-001",
      "priority": "high",
      "summary": "Monitor TES recovery after Supervisor restart",
      "agent": "cbo",
      "created_at": 1767575974.0,
      "status": "active"
    }
  ],
  "completed_today": 3,
  "deferred": []
}
```

---

#### `recent_decisions.jsonl` (Append-Only Rolling Buffer)

**Written by**: CBO after each decision point  
**Read by**: Agents (context), CBO (reflection), Human Overseer (audit)  
**Update frequency**: After decision events  
**Retention**: Last 10 decisions (older moves to `warm/decisions/`)

**Entry format**:
```json
{"ts": 1767575974.0, "iso": "2026-01-04T19:59:34Z", "decision": "Approved Supervisor restart for infrastructure restoration", "rationale": "8 agents stalled, observability offline, no autonomy escalation", "outcome": "7 agents restored, posture remains Distressed (TES unchanged)", "decision_maker": "cbo", "human_approval": true}
```

---

#### `posture_log.jsonl` (Real-Time Posture Tracking)

**Written by**: Station Pulse (via CBO wrapper)  
**Read by**: CBO (reasoning), Agents (context)  
**Update frequency**: On posture change detection  
**Retention**: Last 20 transitions (older moves to `warm/posture_history.jsonl`)

**Entry format**:
```json
{"ts": 1767575974.0, "iso": "2026-01-04T19:59:34Z", "from_posture": "Distressed", "to_posture": "Distressed", "active_count": 8, "tes_score": 55.0, "trigger": "supervisor_restart", "agent_changes": {"navigator": "stalled→idling", "triage": "stalled→idling", "enhanced_metrics": "stalled→idling"}}
```

---

### 1.4 Warm Memory Layer

**Purpose**: Preserve historical summaries and decisions in append-only format. Human-readable where possible.

#### `warm/daily/YYYY-MM-DD.md` (Daily Summaries)

**Written by**: CBO at end-of-day or on first activity of next day  
**Read by**: Human Overseer (continuity), CBO (reflection), Agents (historical context)  
**Update frequency**: Daily (append-only, never modified after creation)

**Content structure**:
```markdown
# Station Calyx Daily Summary — 2026-01-04

**Posture Range**: Distressed → Congestion  
**TES Range**: 55.0% → 68.0% (est.)  
**Active Agent Peak**: 8/15  
**Human Interactions**: 3 directives

## Key Events
- 19:25 UTC: Agent1 re-entry attempt (observational reasoning goal)
  - Outcome: Framework limitation identified (planner schema incompatible)
  - Decision: CBO performed diagnostic reasoning instead
  
- 19:59 UTC: Supervisor infrastructure restoration
  - Scope: Monitoring + Service + Scheduler lanes
  - Outcome: 7 agents online, observability restored
  - Posture: Remains Distressed (TES lag expected)

## Decisions
- Approved Supervisor restart (infrastructure-only scope)
- Agent1 remains idle pending next directive
- No autonomy escalation, all gates unchanged

## Agent Performance
- Agent1: 1 run (dry-run mode), 1 failed observational run
- CBO: 2 diagnostic passes, 1 infrastructure restoration
- SVF: Passive registry sync (continuous)
- Monitoring lane: All agents restored and stable

## Continuity Notes
- WSL environment unavailable (E_UNEXPECTED error)
- Fallback to Windows native Python successful
- Adaptive Supervisor already running (lock file conflict)
- Station Pulse showing accurate real-time state

## Next Session Context
- Monitor TES rise over 30-60 min window
- Observe posture transition to Congestion or Moderate
- Await Overseer directive for Builder lane activation
```

---

#### `warm/decisions/decisions.jsonl` (Full Decision History)

**Written by**: CBO (appends from `hot/recent_decisions.jsonl` on compaction)  
**Read by**: Rare (audits, post-mortems, research)  
**Update frequency**: Daily compaction or on `recent_decisions.jsonl` overflow

**Purpose**: Complete audit trail of all Station Calyx decisions.

---

#### `warm/posture_history.jsonl` (Full Posture Timeline)

**Written by**: CBO (appends from `hot/posture_log.jsonl` on compaction)  
**Read by**: CBO (trend analysis), CP6 Sociologist (harmony assessment)  
**Update frequency**: Daily compaction or on `posture_log.jsonl` overflow

**Purpose**: Historical posture data for system health analysis.

---

### 1.5 MVP Data Flow (Agent1 Cycle)

**On Agent1 Run Start**:
1. Agent1 reads `memory/hot/session_context.md` (injected into goal context)
2. Agent1 reads `memory/hot/active_goals.json` (if multi-goal reasoning needed)

**On Agent1 Run Complete**:
3. Agent1 writes run artifacts to `outgoing/agent_run_<ts>/audit.json`
4. CBO reads audit, extracts key outcomes
5. CBO updates `memory/hot/recent_decisions.jsonl` (if decision made)
6. CBO optionally updates `memory/hot/session_context.md` (if significant state change)

**On CBO Check-In**:
7. CBO reads Station Pulse, detects posture change
8. CBO writes `memory/hot/posture_log.jsonl` entry
9. CBO evaluates if `session_context.md` needs refresh
10. CBO decides if daily summary needed (time-based or event-based trigger)

---

### 1.6 MVP Integration with Micro-Improvement Cadence

**Existing Cadence** (from Agent1 scheduler):
- Light task loop runs every 3-5 minutes
- Auto-promotion after 5 successful runs
- Cooldown period: 15-30 minutes

**Memory-Enhanced Cadence**:
- **Before each Agent1 run**: Read `session_context.md` → inject into goal context
- **After each Agent1 run**: CBO evaluates if context update needed (threshold: significant state change)
- **Daily or on Overseer return**: CBO writes `warm/daily/` summary
- **Weekly** (future): CBO compaction pass (consolidate decisions, prune hot memory)

**Key Principle**: Memory updates are **passive observers** of work, not triggers for work.

---

### 1.7 MVP Implementation Checklist

**Phase 1: Directory Setup** (5 minutes, safe while live)
- [ ] Create `memory/hot/` directory
- [ ] Create `memory/warm/daily/` directory
- [ ] Create `memory/warm/decisions/` directory

**Phase 2: Hot Memory Files** (15 minutes, safe while live)
- [ ] Create `memory/hot/session_context.md` (manual seed with current state)
- [ ] Create `memory/hot/active_goals.json` (empty initial state)
- [ ] Create `memory/hot/recent_decisions.jsonl` (empty initial)
- [ ] Create `memory/hot/posture_log.jsonl` (seed with current Station Pulse snapshot)

**Phase 3: CBO Memory Integration** (requires maintenance window or dry-run testing)
- [ ] Add `read_session_context()` function to CBO
- [ ] Add `write_decision()` function to CBO
- [ ] Add `update_posture_log()` function to CBO (called from Station Pulse wrapper)
- [ ] Add `write_daily_summary()` function to CBO (time-triggered)

**Phase 4: Agent1 Memory Integration** (requires testing)
- [ ] Modify `agent_runner.py` to inject `session_context.md` into goal prompt
- [ ] Test with dry-run goal to verify context injection
- [ ] Validate memory reads don't slow down agent startup

**Phase 5: Validation** (30 minutes)
- [ ] Run Agent1 cycle with memory context
- [ ] Verify CBO writes decision after run
- [ ] Trigger posture change, verify log updated
- [ ] Manually verify `session_context.md` readable and accurate

---

## Part 2: Full Memory Architecture (Growth Path)

### 2.1 Three-Tier Memory Model

```
HOT MEMORY (Current Session)
↓ (compaction: daily or on overflow)
WARM MEMORY (Recent History, Append-Only)
↓ (compaction: weekly/monthly)
COLD MEMORY (Long-Term Archive, Compressed)
```

**Hot Memory**: Working context for current session (hours to 1 day)  
**Warm Memory**: Searchable recent history (1 day to 3 months)  
**Cold Memory**: Compressed archives (3+ months, rare access)

---

### 2.2 Cold Memory Layer (Future)

```
memory/
└── cold/
    ├── archive/
    │   ├── 2025-Q4.tar.gz         # Compressed quarterly archives
    │   └── 2026-Q1.tar.gz
    ├── summaries/
    │   ├── 2025-Q4-summary.md     # Quarterly narrative summaries
    │   └── 2026-Q1-summary.md
    └── index/
        └── decisions_index.json    # Keyword index for archived decisions
```

**Purpose**: Long-term preservation without polluting active context.

**Compaction Strategy**:
- **Quarterly**: Compress `warm/daily/` summaries older than 90 days → `cold/archive/YYYY-Qx.tar.gz`
- **Quarterly**: CBO writes high-level narrative summary → `cold/summaries/YYYY-Qx-summary.md`
- **Annual** (optional): Human Overseer reviews and curates "highlights" document

---

### 2.3 Agent Responsibility Boundaries

| Layer | Written By | Read By | Purpose |
|-------|-----------|---------|---------|
| **Hot Memory** | CBO (orchestrator) | Agents (context), CBO (reasoning), Human (oversight) | Current session state |
| **Warm Memory** | CBO (compaction) | CBO (reflection), Human (audit), CP6/CP7 (analysis) | Recent history |
| **Cold Memory** | CBO (archival) | Human (research), Rare agent queries | Long-term archive |

**Execution agents** (Agent1-4) **produce work artifacts**, not memory.  
**CBO curates, summarizes, and records** memory from work artifacts.  
**Human Overseer** retains **read/write/edit access** to all memory layers.

---

### 2.4 Compaction Strategy

**Daily Compaction** (triggered at 00:00 UTC or on first activity of new day):
1. CBO reads all `hot/recent_decisions.jsonl` entries
2. CBO appends to `warm/decisions/decisions.jsonl`
3. CBO reads all `hot/posture_log.jsonl` entries
4. CBO appends to `warm/posture_history.jsonl`
5. CBO writes `warm/daily/YYYY-MM-DD.md` summary
6. CBO truncates `hot/recent_decisions.jsonl` to last 10 entries
7. CBO truncates `hot/posture_log.jsonl` to last 20 entries
8. CBO updates `hot/session_context.md` with "new day" reset

**Weekly Compaction** (triggered Sunday 00:00 UTC or on demand):
1. CBO reviews `warm/daily/` summaries for past 7 days
2. CBO writes `warm/weekly/YYYY-Www-summary.md` (narrative synthesis)
3. CBO identifies recurring patterns/issues → surfaces to Human Overseer

**Quarterly Compaction** (manual trigger by Human Overseer):
1. CBO compresses `warm/daily/` older than 90 days → `cold/archive/YYYY-Qx.tar.gz`
2. CBO writes `cold/summaries/YYYY-Qx-summary.md` (high-level narrative)
3. CBO generates keyword index for archived decisions → `cold/index/`

---

### 2.5 Indexing Strategy

**Phase 1 (MVP)**: No indexing — sequential read of JSONL files (acceptable for <10k entries)

**Phase 2 (Warm Memory Scale)**: Keyword/tag-based indexing
- CBO maintains `warm/index/keyword_index.json`:
  ```json
  {
    "supervisor": ["2026-01-04", "2026-01-07"],
    "agent1": ["2026-01-03", "2026-01-04", "2026-01-05"],
    "distressed_posture": ["2026-01-03", "2026-01-04"]
  }
  ```
- Agents query index, then read specific daily summaries

**Phase 3 (Future, Optional)**: Local semantic search
- **If** embedding models are available (e.g., `sentence-transformers` via llama.cpp)
- **Then**: Generate embeddings for daily summaries → store in `memory/embeddings/`
- **Then**: Enable semantic queries ("What decisions involved infrastructure?")
- **Constraint**: Must remain local-only (no network calls)
- **Tradeoff**: Complexity vs. retrieval quality (defer until demonstrated need)

---

### 2.6 Memory Bloat Prevention

**Guardrails**:
1. **Hot memory size limits**:
   - `session_context.md`: Max 200 lines (enforced by CBO on write)
   - `recent_decisions.jsonl`: Max 10 entries (rolling buffer)
   - `posture_log.jsonl`: Max 20 entries (rolling buffer)

2. **Warm memory retention policy**:
   - `daily/` summaries: Keep last 90 days uncompressed
   - `decisions.jsonl`: No size limit (append-only, compresses well)
   - `posture_history.jsonl`: No size limit (high-frequency data, but small entries)

3. **Cold memory archival**:
   - Compress anything older than 90 days
   - Human Overseer can manually archive sooner if disk space constrained

4. **Noise filtering**:
   - CBO only writes decisions with **actionable outcomes** (no trivial status updates)
   - Posture log only records **transitions** (not every poll)
   - Daily summaries focus on **key events** (not exhaustive logs)

---

### 2.7 Memory vs. Hallucination Guardrails

**Risk**: Agents could confabulate continuity from incomplete memory.

**Mitigations**:
1. **Timestamps on all entries**: Agents can verify recency, detect gaps
2. **Explicit gap markers**: If daily summary missing, CBO writes stub: "No activity recorded for YYYY-MM-DD"
3. **Human-readable format**: Memory is **Overseer-auditable** — hallucinations detectable
4. **Append-only**: Historical entries never modified (prevents retroactive "rewriting history")
5. **Source attribution**: All decisions tagged with `decision_maker` (cbo, agent1, human)

**Agents must**:
- Prefer recent memory over old memory
- Surface uncertainty ("Last known context from 2026-01-03...")
- Never execute based on memory alone without current state validation

---

## Part 3: Integration with Autonomy Cadence

### 3.1 Observe → Act → Reflect → Record → Repeat

**Observe**:
- Agent1 reads `memory/hot/session_context.md` (current state)
- Agent1 reads Station Pulse (live posture)
- Agent1 scans `outgoing/*.lock` (agent heartbeats)

**Act (Bounded)**:
- Agent1 executes goal within constraints (no apply, no escalation)
- Agent1 writes `audit.json` to `outgoing/agent_run_<ts>/`

**Reflect**:
- CBO reads `audit.json`, evaluates outcomes
- CBO determines if decision was significant
- CBO assesses if session context needs update

**Record**:
- CBO appends to `memory/hot/recent_decisions.jsonl`
- CBO updates `memory/hot/session_context.md` (if major state change)
- CBO triggers daily summary if end-of-day

**Repeat**:
- Next Agent1 cycle reads updated `session_context.md`
- Cumulative learning via memory without autonomy escalation

---

### 3.2 Station Pulse + Memory Integration

**Current**: Station Pulse provides real-time snapshot (8/15 agents, Distressed posture, TES 55%)

**With Memory**:
- Station Pulse reads `memory/hot/posture_log.jsonl` → shows posture **trend** (last 5 transitions)
- CBO writes posture change → updates `posture_log.jsonl` → feeds back to Pulse
- Human Overseer sees: "Distressed for 2 hours (since 18:00 UTC), previously Calm for 3 days"

**Value**: Context depth without cluttering real-time UI.

---

### 3.3 Supervisor-Managed Continuity

**Current**: Supervisor restarts Monitoring/Service/Scheduler agents, no persistence

**With Memory**:
- Supervisor reads `memory/hot/session_context.md` on startup
- Supervisor writes "Supervisor started" event → CBO records decision
- If agents fail to start, CBO records failure → informs next restart attempt

**Value**: Supervisor gains "short-term memory" of recent restart attempts (avoid retry loops).

---

### 3.4 Memory MUST NOT Trigger Autonomy

**Critical Constraint**: Memory system is **observational only**.

**Forbidden**:
- ❌ Memory writing triggers agent execution
- ❌ Memory threshold (e.g., "10 decisions today") triggers escalation
- ❌ Historical pattern detection triggers apply gate changes

**Allowed**:
- ✅ Memory informs CBO reasoning about **recommendations** to Human Overseer
- ✅ Agents read memory to improve **context quality** of bounded work
- ✅ CBO surfaces memory-derived insights via Station Pulse or dialog

**Enforcement**:
- Memory writes are **side effects** of agent work, not triggers
- CBO never executes based on memory alone (always requires Human approval or explicit goal)

---

## Part 4: Implementation Proposal (No Execution)

### 4.1 Implementation Phases

**Phase 1: MVP Foundation** (Estimated: 2 hours, safe while live)
- Create directory structure (`memory/hot/`, `memory/warm/`)
- Seed `session_context.md` manually with current state
- Initialize empty JSONL files
- **No code changes**, pure file setup

**Phase 2: CBO Memory Functions** (Estimated: 4 hours, requires testing)
- Implement `read_session_context()` in `calyx/cbo/memory.py`
- Implement `write_decision()` in `calyx/cbo/memory.py`
- Implement `update_posture_log()` in `calyx/cbo/memory.py`
- Implement `write_daily_summary()` in `calyx/cbo/memory.py`
- Add config flag: `telemetry.memory.enabled: true` (default false for safety)

**Phase 3: Agent1 Memory Integration** (Estimated: 2 hours, requires testing)
- Modify `tools/agent_runner.py`:
  - Read `memory/hot/session_context.md` if exists
  - Inject as system context or prepend to goal prompt
  - Validate memory read doesn't crash on missing file
- Test with dry-run goal: "Review session context and summarize current focus"

**Phase 4: Station Pulse Memory Integration** (Estimated: 1 hour)
- Modify `tools/station_pulse.py`:
  - Read last 5 entries from `memory/hot/posture_log.jsonl`
  - Display posture trend in console/GUI mode
- Wrap posture calculation: call `cbo.memory.update_posture_log()` on change

**Phase 5: Daily Compaction** (Estimated: 2 hours)
- Implement `tools/memory_compactor.py`:
  - Runs daily via cron or Supervisor schedule
  - Executes compaction logic (hot→warm, write daily summary)
  - Logs compaction results to `logs/memory_compaction.log`
- Add to Supervisor optional services list

**Total Estimated Effort**: 11 hours (1.5 workdays)

---

### 4.2 Incremental Addition Strategy

**Safe to add while Station Calyx is live**:
- ✅ Phase 1 (directory structure, manual seed files)
- ✅ Phase 2 (CBO functions with `enabled: false` config flag)
- ✅ Phase 3 (Agent1 integration with graceful fallback on missing files)

**Requires maintenance window or isolated testing**:
- ⚠️ Phase 4 (Station Pulse modification — affects live UI)
- ⚠️ Phase 5 (Compaction automation — needs validation of file I/O patterns)

**Recommended rollout**:
1. Deploy Phase 1+2 while live (no user-facing changes)
2. Test Phase 3 in dry-run mode (Agent1 with `--dry-run` flag)
3. Schedule 30-minute maintenance window for Phase 4+5 deployment
4. Validate with 24-hour observation period before enabling compaction

---

### 4.3 Testing Plan

**Unit Tests** (before deployment):
- `test_read_session_context()` — verify graceful handling of missing/corrupt files
- `test_write_decision()` — verify JSONL append without corruption
- `test_update_posture_log()` — verify rolling buffer (max 20 entries)
- `test_daily_compaction()` — verify hot→warm transfer, summary generation

**Integration Tests** (dry-run mode):
- Run Agent1 with memory context injection, verify goal execution unchanged
- Trigger posture change (manual Station Pulse edit), verify log update
- Manually invoke `memory_compactor.py`, verify warm files created

**Validation Criteria**:
- ✅ Agent1 startup time <1s increase with memory read
- ✅ CBO decision write completes in <100ms
- ✅ Daily compaction completes in <5s
- ✅ No file corruption or lock contention observed
- ✅ Human Overseer can read/edit memory files without issues

---

### 4.4 Rollback Plan

**If memory system causes issues**:
1. Set config flag: `telemetry.memory.enabled: false`
2. Restart CBO/Agent1 to disable memory reads
3. Memory files remain on disk (no data loss)
4. Investigate issue, fix, re-enable

**If memory files corrupt**:
1. Move corrupted files to `memory/archive/corrupt_YYYY-MM-DD/`
2. Re-seed `session_context.md` manually
3. CBO regenerates missing files on next write

**No risk to core Station Calyx operation**: Memory is **additive only**, not replacing existing telemetry.

---

## Part 5: Risks, Trade-offs, and Guardrails

### 5.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Memory bloat** (disk usage) | Medium | Low | Size limits on hot memory, compaction to cold storage |
| **File I/O contention** | Low | Medium | Append-only writes, no concurrent edits to same file |
| **Agent hallucination** from stale memory | Medium | High | Timestamps on all entries, explicit gap markers, human auditability |
| **Memory becoming "junk drawer"** | High | Medium | Strict decision significance threshold, CBO curates actively |
| **Human Overseer losing trust** due to opaque memory | Low | High | Markdown-first format, human-editable, full audit trail |

---

### 5.2 Trade-offs

**Markdown vs. JSON for summaries**:
- **Pro Markdown**: Human-readable, editable, narrative continuity
- **Pro JSON**: Machine-parseable, structured queries, semantic indexing
- **Decision**: Use Markdown for summaries (`daily/*.md`), JSON/JSONL for structured logs

**Hot memory size limits**:
- **Tighter limits** (10 decisions, 20 posture entries): Less noise, more frequent compaction
- **Looser limits** (50 decisions, 100 posture entries): Better context depth, higher bloat risk
- **Decision**: Start conservative (10/20), adjust based on observed usage

**Compaction frequency**:
- **Daily**: Consistent, predictable, lower hot memory footprint
- **Weekly**: Less overhead, but hot memory grows larger
- **Decision**: Daily compaction with weekly summaries (two-tier cadence)

---

### 5.3 Guardrails

**Non-Negotiable**:
1. **Append-only for historical records** (`warm/decisions/`, `warm/posture_history/`)
2. **Human Overseer can edit any memory file** (no agent locks)
3. **Memory never triggers execution** (observation only)
4. **Graceful degradation**: Missing memory files don't crash agents
5. **Local-first**: No network calls for memory operations

**Strongly Recommended**:
6. **Timestamps on all entries** (verify recency, detect gaps)
7. **Source attribution** (cbo, agent1, human) on all decisions
8. **Size limits on hot memory** (prevent unbounded growth)
9. **Human review of daily summaries** (spot-check CBO curation quality)
10. **Quarterly archive review** (Overseer validates long-term narrative)

---

## Part 6: Success Metrics

**Memory MVP is successful if**:
1. **Context re-establishment time** after downtime reduced by 50% (measured by Overseer subjective assessment)
2. **Agent1 reasoning quality** improves (fewer "what were we doing?" questions in goals)
3. **CBO decision curation** maintains 90%+ relevance (Overseer audit of `recent_decisions.jsonl`)
4. **No memory-related crashes or slowdowns** observed in 30-day observation period
5. **Human Overseer actively uses** `session_context.md` and `daily/` summaries for situational awareness

**Full memory architecture is successful if**:
6. **Warm memory searchable** in <5s for keyword queries
7. **Cold archives accessible** without needing to expand into live workspace
8. **Narrative continuity preserved** across multi-month gaps (Overseer can reconstruct "story so far")
9. **Memory footprint** remains <500 MB uncompressed after 1 year of operation
10. **Agent autonomy improved** without autonomy escalation (bounded execution with better context)

---

## Part 7: Recommendation Timeline

**When to request execution approval**:

**✅ Now (Phase 1)**: Directory setup and manual seed files (zero risk, immediate value)

**⚠️ After 24-hour observation** (Phase 2-3): CBO/Agent1 memory integration (requires validation that infrastructure restoration is stable)

**⏸️ After 1 week of stable operation** (Phase 4-5): Station Pulse integration and daily compaction (wait for TES to stabilize, posture to reach Calm/Moderate)

**⏸️ After 1 month of MVP operation** (Full architecture): Cold storage, indexing, semantic search (defer until MVP proves value)

---

## Conclusion

This memory architecture provides Station Calyx with **local-first continuity** that:
- **Reduces cognitive load** for Human Overseer returning after downtime
- **Improves agent reasoning** with grounded historical context
- **Preserves narrative integrity** across temporal gaps
- **Maintains human primacy** through readable, editable, auditable storage
- **Serves autonomy without escalating it** (memory informs, never triggers)

**Immediate value** (MVP): Context for "What happened while I was away?"  
**Long-term value** (Full architecture): Cumulative learning loop enabling micro-improvements without external dependencies

**Next Step**: Await Human Overseer approval for Phase 1 deployment (directory setup + manual seed).

---

**Document Status**: Design complete, implementation pending approval  
**CBO Assessment**: Architecture is sound, aligns with Station Calyx principles, ready for review  
**Estimated Time to MVP**: 2 hours (Phase 1), 6 hours (Phase 2-3), total 8 hours to operational MVP
