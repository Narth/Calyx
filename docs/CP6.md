# CP6 — The Sociologist

CP6 observes agent interactions and maintains a Sociological Map, Harmony Index, and field notes.

Quick start (Windows PowerShell):

```powershell
python -u .\Scripts\cp6.py --interval 2 --max-iters 5
```

Artifacts:
- `outgoing/field_notes/cp6_map.json` — nodes/edges with statuses and links
- `outgoing/field_notes/cp6_field_log.md` — per-cycle notes with tags: [SUGGESTION], [HARMONY], [RISK], [EVOLUTION]
- `outgoing/field_notes/cp6_weekly.md` — weekly summary (baseline initialized)
- `outgoing/field_notes/calyx_social_protocol_v0.1.md` — etiquette and norms

Notes:
- CP6 passively observes for 12 cycles before making structural suggestions.
- It emits a heartbeat at `outgoing/cp6.lock` compatible with the Agent Watcher.

Harmony Index v0.1 (0–100):
- Rhythm (35%): steady 3-minute cadence of micro-steps
- Stability (40%): mean stability from `logs/agent_metrics.csv`
- Load balance (15%): penalizes >2 agents running concurrently
- Staleness (10%): penalizes heartbeats older than 10 minutes

You can tune/add heuristics by editing `tools/cp6_sociologist.py`.