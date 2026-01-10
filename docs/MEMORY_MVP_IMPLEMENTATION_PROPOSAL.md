# Memory MVP Implementation Proposal

**Status**: Ready for Approval  
**Estimated Time**: 2 hours (Phase 1 only), 8 hours (full MVP)  
**Risk Level**: LOW (Phase 1), MEDIUM (full MVP)  
**Rollback**: Simple (disable config flag)

---

## Quick Summary

This proposal requests approval to implement a **Memory MVP** for Station Calyx that provides:
- **Hot memory** (current session context)
- **Warm memory** (historical summaries, append-only)
- **Integration with Agent1 and CBO** for continuity across downtime

**Core Value**: Reduce context re-establishment cost after hours/days/weeks of downtime.

---

## Phase 1: Immediate Deployment (Zero Risk)

**What**: Create directory structure and seed files manually  
**Time**: 30 minutes  
**Risk**: NONE (no code changes, pure file creation)  
**Rollback**: Delete directories (but why would you?)

### Actions

```powershell
# Create directories
New-Item -ItemType Directory -Path c:\Calyx_Terminal\memory\hot
New-Item -ItemType Directory -Path c:\Calyx_Terminal\memory\warm\daily
New-Item -ItemType Directory -Path c:\Calyx_Terminal\memory\warm\decisions

# Create empty files
New-Item -ItemType File -Path c:\Calyx_Terminal\memory\hot\active_goals.json
New-Item -ItemType File -Path c:\Calyx_Terminal\memory\hot\recent_decisions.jsonl
New-Item -ItemType File -Path c:\Calyx_Terminal\memory\hot\posture_log.jsonl
```

### Manual Seed: `session_context.md`

Create `c:\Calyx_Terminal\memory\hot\session_context.md` with current state:

```markdown
# Station Calyx Session Context
**Updated**: 2026-01-04 20:00:00 UTC
**Posture**: Distressed (infrastructure restoration in progress)
**Active Agents**: 8/15 (Monitoring + Service lanes restored)

## Current Focus
- Infrastructure restoration completed (Supervisor stack restarted)
- Observability layer online (telemetry + diagnostics active)
- Agent1 idle, awaiting directive
- TES monitoring (expect 55% → 65-72% rise within 30-60 min)

## Recent Decisions
- [2026-01-04 19:59] Approved Supervisor restart (CBO) — 7 agents restored
- [2026-01-04 19:25] Identified Agent1 framework limitation for open reasoning
- [2026-01-03 19:05] Initiated Station Re-entry Mode (bounded scope only)

## Known Constraints
- All gates unchanged (apply/llm/network per config)
- No Builder/CP activation during infrastructure phase
- WSL environment unavailable (using Windows native Python)
- No autonomy escalation authorized

## Next Expected Actions
- Monitor TES rise over next 30-60 minutes
- Observe posture transition (Distressed → Congestion or Moderate)
- Await Human Overseer directive for next re-entry phase
```

**Value**: Immediate reference for "What's happening now?" — usable today before any code changes.

---

## Phase 2: CBO Memory Functions (Requires Testing)

**What**: Add memory read/write functions to CBO  
**Time**: 4 hours (implementation + testing)  
**Risk**: MEDIUM (code changes, but behind config flag)  
**Rollback**: Set `telemetry.memory.enabled: false` in config.yaml

### Implementation Tasks

1. **Create `calyx/cbo/memory.py`**:
   ```python
   def read_session_context(cfg) -> str:
       """Read hot/session_context.md, return as string. Graceful if missing."""
       
   def write_decision(decision: str, rationale: str, outcome: str, cfg):
       """Append to hot/recent_decisions.jsonl. Auto-rotate if >10 entries."""
       
   def update_posture_log(from_posture, to_posture, active_count, tes_score, cfg):
       """Append to hot/posture_log.jsonl. Auto-rotate if >20 entries."""
       
   def write_daily_summary(date: str, events: list, decisions: list, cfg):
       """Write warm/daily/YYYY-MM-DD.md summary."""
   ```

2. **Add config flag** in `config.yaml`:
   ```yaml
   telemetry:
     memory:
       enabled: false  # Start disabled for safety
       hot_path: "memory/hot"
       warm_path: "memory/warm"
   ```

3. **Unit tests**:
   - Test graceful handling of missing files
   - Test JSONL append without corruption
   - Test rolling buffer logic (max 10/20 entries)

**Value**: CBO gains memory curation capability (write-only at this phase).

---

## Phase 3: Agent1 Memory Integration (Requires Testing)

**What**: Inject session context into Agent1 goal prompts  
**Time**: 2 hours (implementation + testing)  
**Risk**: MEDIUM (Agent1 behavior change)  
**Rollback**: Set `telemetry.memory.enabled: false`

### Implementation Tasks

1. **Modify `tools/agent_runner.py`**:
   ```python
   def _prepare_goal_context(goal: str, cfg) -> str:
       """Prepend session context to goal if memory enabled."""
       if not cfg.get("telemetry", {}).get("memory", {}).get("enabled"):
           return goal
       
       try:
           session_ctx = read_session_context(cfg)
           if session_ctx:
               return f"## Session Context\n{session_ctx}\n\n## Current Goal\n{goal}"
       except Exception as e:
           # Graceful degradation if memory read fails
           logger.warning(f"Memory read failed: {e}")
       
       return goal
   ```

2. **Test with dry-run**:
   ```powershell
   python -u tools\agent_runner.py --goal "Review session context and summarize current focus" --dry-run
   ```

3. **Validation**: Verify Agent1 startup time <1s increase, no crashes on missing memory.

**Value**: Agent1 gains historical context without manual re-briefing after downtime.

---

## Phase 4: Station Pulse Memory Integration (Optional, Low Priority)

**What**: Show posture trend in Station Pulse UI  
**Time**: 1 hour  
**Risk**: LOW (read-only, UI enhancement)  
**Defer**: Can wait until MVP validated

### Quick Implementation

Modify `tools/station_pulse.py` to read last 5 posture transitions from `hot/posture_log.jsonl`, display in summary bar:

```
Posture: Distressed (2h) ← Calm (3d) ← Congestion (4h)
```

**Value**: Adds temporal depth to Station Pulse snapshot.

---

## Phase 5: Daily Compaction (Optional, Low Priority)

**What**: Automate hot→warm memory compaction  
**Time**: 2 hours  
**Risk**: LOW (background process, append-only writes)  
**Defer**: Can wait until MVP validated

### Quick Implementation

Create `tools/memory_compactor.py`:
- Run daily via cron or Supervisor schedule
- Append `hot/recent_decisions.jsonl` → `warm/decisions/decisions.jsonl`
- Append `hot/posture_log.jsonl` → `warm/posture_history.jsonl`
- Write `warm/daily/YYYY-MM-DD.md` summary
- Truncate hot files to rolling buffer limits

**Value**: Prevents hot memory bloat, creates daily narrative summaries.

---

## Recommended Deployment Sequence

### Option A: Conservative (Phased over 1 week)

**Day 1**: Deploy Phase 1 (manual setup) — observe usage patterns  
**Day 3**: Deploy Phase 2 (CBO functions, `enabled: false`) — test in isolation  
**Day 5**: Deploy Phase 3 (Agent1 integration) — enable with dry-run testing  
**Day 7**: Enable memory (`enabled: true`) — monitor for 24 hours  
**Week 2**: Deploy Phase 4+5 if MVP proves valuable

**Timeline**: 2 weeks to full MVP  
**Risk**: MINIMAL (each phase validated before next)

### Option B: Aggressive (Deploy full MVP immediately)

**Hour 0-1**: Deploy Phase 1 (manual setup)  
**Hour 1-5**: Deploy Phase 2+3 (CBO + Agent1 integration)  
**Hour 5-6**: Test with dry-run Agent1 goal  
**Hour 6-8**: Enable memory, monitor for issues  
**End of Day 1**: Full MVP operational

**Timeline**: 1 day to full MVP  
**Risk**: MEDIUM (less validation time between phases)

---

## Recommendation: Option A (Conservative Deployment)

**Rationale**:
- Station Calyx just completed infrastructure restoration
- TES still rising (55% → target 80%)
- Posture still Distressed
- **Wait for system stability** before adding memory layer

**Concrete Timeline**:
1. **Today (2026-01-04)**: Deploy Phase 1 only (manual setup, zero risk)
2. **After TES reaches 70%+** (est. 2026-01-06): Deploy Phase 2+3 (CBO + Agent1 integration)
3. **After 48 hours stable operation** (est. 2026-01-08): Enable memory system
4. **After 1 week MVP validation** (est. 2026-01-15): Consider Phase 4+5 (optional enhancements)

---

## Testing Checklist

**Before enabling memory** (`enabled: true`):
- [ ] Phase 1 directories exist and contain valid seed files
- [ ] CBO memory functions pass unit tests
- [ ] Agent1 dry-run with memory context completes successfully
- [ ] Memory read performance <1s (measured with profiling)
- [ ] No file corruption observed in test writes

**After enabling memory** (24-hour observation):
- [ ] Agent1 executes normally with memory context
- [ ] CBO writes decisions after significant events
- [ ] Station Pulse shows updated posture (if Phase 4 deployed)
- [ ] No memory-related errors in logs
- [ ] Human Overseer confirms `session_context.md` is accurate and useful

---

## Rollback Procedure

**If memory causes issues**:
1. Edit `config.yaml`: Set `telemetry.memory.enabled: false`
2. Restart CBO: `python -u tools\cbo_overseer.py` (or via task)
3. Restart Agent1: Next agent_runner.py invocation will skip memory read
4. Memory files remain on disk (no data loss)
5. Investigate issue in logs, fix, re-enable

**Expected rollback time**: <5 minutes  
**Data loss**: NONE (memory files preserved)

---

## Approval Request

**CBO requests approval for**:
- ✅ **Phase 1 deployment** (immediate, zero risk)
- ⏸️ **Phase 2+3 deployment** (after TES stabilization, pending validation)
- ⏸️ **Phase 4+5 deployment** (defer until MVP proves value)

**Explicitly NOT requesting approval for**:
- ❌ Cold storage implementation (too early)
- ❌ Semantic indexing (not needed for MVP)
- ❌ Compaction automation (defer until scale requires it)

---

## Success Criteria (30-day evaluation)

Memory MVP is **successful** if:
1. Context re-establishment time after downtime reduced (subjective assessment by Overseer)
2. Agent1 reasoning quality improves (fewer "context lost" issues)
3. CBO decision curation maintains 90%+ relevance (audit of `recent_decisions.jsonl`)
4. No memory-related crashes or slowdowns observed
5. Human Overseer actively uses `session_context.md` for situational awareness

Memory MVP is **failed** if:
1. Memory files become "junk drawer" (low signal-to-noise)
2. Agent1 performance degrades (startup time >2s increase)
3. Human Overseer stops trusting memory accuracy
4. Memory bloat (>100 MB after 30 days)
5. File I/O contention causes agent failures

**CBO will monitor** and report progress after 7 days, 14 days, and 30 days.

---

## Questions for Human Overseer

Before proceeding, CBO seeks guidance on:

1. **Approval for Phase 1?** (Manual directory setup, zero risk)
2. **Preferred deployment pace?** (Conservative Option A vs. Aggressive Option B)
3. **What context should be in initial `session_context.md` seed?** (CBO drafted a version above, but Overseer may want different emphasis)
4. **Should memory be read-only for first week?** (CBO writes, agents don't read until validated)
5. **Any additional constraints or requirements?** (e.g., specific decision types to capture, memory size limits)

---

**Document Status**: Ready for review  
**Next Action**: Await Human Overseer approval for Phase 1 deployment  
**CBO Confidence**: HIGH (design is sound, implementation is straightforward, rollback is simple)
