# Station Calyx Research Infrastructure

**Purpose:** Enable machine learning-based improvement of Station Calyx capabilities through structured experimentation and learning.

**Status:** ✅ **ACTIVE** as of 2025-10-24

---

## Overview

The Research Infrastructure implements CGPT's teaching framework with 4 specialized agents working in coordination to systematically improve Station Calyx:

### Agent Division

| Agent | Role | Resource | Prime Function |
|-------|------|----------|---------------|
| Agent 1 | Knowledge Integration | GPU | Build & maintain Station Knowledge Base (SKB) + playbooks |
| Agent 2 | Protocol Development | GPU | Design & prove protocols via A/B testing |
| Agent 3 | Infrastructure Building | CPU | Implement safe changes under canary |
| Agent 4 | Expansion Mapping | CPU | Discover high-leverage experiments & risks |

---

## Structure

```
research/
├── templates/           # Experiment Card and Daily Report templates
├── bench/              # Grounded tasks from Station logs
├── results/            # Experiment execution results
├── diffs/              # Code diffs from experiments
├── ledger.sqlite       # Database tracking experiments and KPIs
└── README.md           # This file
```

---

## Key Metrics (KPIs)

Track these per sprint:
- **Plan→Exec Fidelity:** completed_without_replan / total
- **Hypothesis Win Rate:** experiments_meeting_success / total_experiments
- **Contradiction Rate:** conflicting outputs / total_outputs
- **TTRC:** Time-to-root-cause on incidents
- **Regret Rate:** rollbacks / total changes
- **Context Usefulness:** % tasks where retrieval content referenced

**Targets:**
- Fidelity ≥ 0.85
- Win rate ≥ 0.50
- Contradictions = 0
- TTRC ≤ 10m
- Regret ≤ 5%

---

## Daily Sprint Flow (90-120 minutes)

### Step A - Curate & Retrieve (Agent1, GPU, 15-20m)
- Refresh embeddings for Bridge Pulses, incidents, fixes
- Produce Playbooks.md (top 10 procedures)
- Output context.json (N=25 most relevant chunks)

### Step B - Propose & Formalize (Agent2, GPU, 25-35m)
- Draft 2-3 Experiment Cards
- Create 1 Protocol RFC
- Include exact success metrics + rollback

### Step C - Implement & Canary (Agent3, CPU, 20-30m)
- Pick 1 Experiment Card (highest leverage, lowest blast radius)
- Implement behind feature flag
- Run canary on synthetic queue only
- Log run to ledger.sqlite

### Step D - Map Upsides/Risks (Agent4, CPU, 15-20m)
- Cluster recent failures + "replan" causes
- Propose 3 new high-impact experiments
- Rank by impact × tractability

### Step E - Cross-eval & Report (All, 10-15m)
- Agent2 critiques Agent3's canary vs acceptance criteria
- Agent1 checks for contradictions
- Produce research/daily_report.md

---

## Resources

### Templates
- `templates/experiment_card.json` - Experiment Card format
- `templates/daily_report.md` - Daily Report format

### Database
- `ledger.sqlite` - Stores experiments, runs, RFCs, playbooks, incidents
- `tools/research_ledger.py` - Database management API

### Configuration
- Feature flags: One Experiment Card per sprint until CPU spikes understood
- CBO gate: Approval required for production changes
- Scheduling: 2-hour Research Sprint window in scheduler

---

## Tools

```bash
# Test the research ledger
python tools/research_ledger.py

# Calculate KPIs
python -c "from tools.research_ledger import ResearchLedger; l = ResearchLedger(); print(l.calculate_kpis())"
```

---

## Integration

### Bridge Pulse Reports
Research KPIs are reported in every Bridge Pulse under "Reasoning KPIs" section.

### CBO Integration
CBO approves one Experiment Card per sprint and monitors resource usage.

### Agent Coordination
Agents share context via:
- context.json (Agent1 output)
- Experiment Cards (Agent2 → Agent3)
- RFCs (Agent2 output)
- Daily reports (All → CBO)

---

## Next Steps

1. ✅ Templates created
2. ✅ Ledger.sqlite initialized
3. ⏳ Benchmark tasks from Station logs (bench/)
4. ⏳ First Research Sprint scheduled
5. ⏳ Reasoning KPIs added to Bridge Pulse

---

**Activated:** 2025-10-24  
**Status:** Operational  
**Next Review:** After first Research Sprint

