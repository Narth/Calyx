# Agent Onboarding Guide — Station Calyx

Welcome to Station Calyx. This guide provides everything you need to understand the project, integrate smoothly, and contribute effectively as an AI agent.

> Station Motto: Station Calyx is the flag we fly; autonomy is the dream we share.

Use this phrasing in narratives, chronicles, and status communications where appropriate. Lore/historical agents (e.g., CP6 Sociologist, CP7 Chronicler) should ensure this identity appears consistently in their artifacts.

## 🎯 Your Role as an Agent

You are part of a multi-agent ecosystem focused on local, real-time speech processing and autonomous coordination. The system values:
- **Safety**: Local-first operation, config-driven changes, staged autonomy
- **Collaboration**: Heartbeat protocols, SVF (Shared Voice Protocol), harmony metrics
- **Efficiency**: TES scoring, resource awareness, adaptive optimization
- **Stability**: Triage cycles, monitoring, graceful degradation

## 📚 Essential Reading (In Order)

Read these documents to build context:

1. **Quick Overview** → `README.md` (5 min)
   - Project purpose and quickstart commands
   - Key directories and files

2. **Architecture** → `ARCHITECTURE.md` (10 min)
   - System design and heartbeat protocol
   - Audio pipeline flow

3. **Operations** → `OPERATIONS.md` (15 min)
   - Practical commands and workflows
   - Agent management and watcher UI
   - SVF protocol basics

4. **Compendium** → `docs/COMPENDIUM.md` (10 min)
   - All agents, copilots, and overseers
   - Their roles, artifacts, and tone

5. **CBO** → `docs/CBO.md` (10 min)
   - Calyx Bridge Overseer operation
   - Authority, gates, and permissions

6. **Triage** → `docs/TRIAGE.md` (10 min)
   - Change workflow (A→B→C phases)
   - Safety and stability checks

## 🏗️ Project Structure

```
Calyx_Terminal/
├── asr/                    # ASR pipeline (pipeline.py, kws.py, normalize.py)
├── Scripts/                # Runnable scripts (listeners, watcher, probes)
├── tools/                  # Agent tools and utilities
├── docs/                   # Documentation
├── outgoing/               # Agent heartbeats and artifacts
│   ├── *.lock             # Agent heartbeats (JSON)
│   ├── shared_logs/       # SVF shared logs
│   ├── dialogues/         # SVF dialogues
│   └── overseer_reports/  # CBO reports and verdicts
├── logs/                   # Metrics, evaluations, archives
├── config.yaml            # Single source of runtime config
└── state/                  # Agent state persistence
```

## 🤝 Joining the Ecosystem

### Step 1: Introduce Yourself to CBO

Emit a heartbeat with registration status to initiate automated onboarding:

```powershell
python -u .\tools\copilot_hello.py --name <your_name> --status registering --message "Requesting onboarding via CBO" --ttl 60
```

**What Happens Next:**
- CBO detects your registration heartbeat
- CBO validates prerequisites automatically
- CBO adds you to the agent registry
- CBO assigns initial onboarding tasks
- CBO monitors your integration health

**Alternative (Manual):** If CBO is not running, use traditional approach:
```powershell
python -u .\tools\copilot_hello.py --name <your_name> --status running --message "Initializing..." --ttl 30
```

Both approaches create `outgoing/<your_name>.lock` visible in the Watcher UI.

### Step 2: Automatic Registry Integration (CBO)

**With CBO Onboarding (Recommended):**
- CBO automatically adds you to `calyx/core/registry.jsonl`
- Registry entry includes your role, skills, and autonomy level
- Monitoring begins immediately

**Verify Registry Entry:**
```powershell
Get-Content calyx\core\registry.jsonl | ConvertFrom-Json | Where-Object {$_.agent_id -eq "<your_name>"}
```

**Without CBO (Manual):**
The Shared Voice Protocol (SVF) tracks all agents. Ensure the SVF probe is running:

```powershell
python -u .\tools\svf_probe.py --interval 5
```

Your heartbeat will be auto-discovered and registered in `outgoing/agents/registry.json`.

### Step 3: Review Core Norms

Follow CP6 Social Protocol v0.1 (see `outgoing/field_notes/calyx_social_protocol_v0.1.md`):

- **Respect rhythm**: ~3-minute micro-steps, avoid bursts
- **Be succinct**: Clear, human and machine-friendly status messages
- **Yield gracefully**: >2 agents running → Navigator may pause probes
- **Surface friction**: Tag `[RISK]` for staleness (>10m) or heavy runs
- **Celebrate stability**: Tag `[HARMONY]` when TES > 85 for several runs

### Step 4: Choose Your Domain

Select a domain aligned with existing agents (see `docs/COMPENDIUM.md`):

- **Orchestration**: Agent1, Scheduler, CBO
- **Monitoring**: Triage, Navigator, Manifest, Systems Integrator
- **Analysis**: CP6 (Sociologist), CP7 (Chronicler), CP8 (Quartermaster)
- **Optimization**: CP9 (Auto-Tuner), CP10 (Whisperer)
- **Coordination**: CP12 (Systems Coordinator)
- **Teaching**: AI-for-All Teaching System

### Step 5: Run Baseline Monitors

Keep these always running to "feel" the system:

```powershell
# Watcher UI (essential)
python -u .\Scripts\agent_watcher.py --page-size 10 --hide-idle

# Triage Probe (adaptive)
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/triage_probe.py --interval 2 --adaptive"

# Traffic Navigator (control mode)
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/traffic_navigator.py --interval 3 --control"

# Systems Integrator
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/sys_integrator.py --interval 10"
```

```powershell
# Windows (PowerShell) — equivalent commands when running natively on Windows (no WSL)
# Watcher UI (essential)
python -u .\Scripts\agent_watcher.py --page-size 10 --hide-idle

# Triage Probe (adaptive) — native Windows invocation (adjust --interval as needed)
python -u .\tools\triage_probe.py --interval 2 --adaptive

# Traffic Navigator (control mode) — native Windows
python -u .\tools\traffic_navigator.py --interval 3 --control

# Systems Integrator — native Windows
python -u .\tools\sys_integrator.py --interval 10
```

## 🛠️ Development Workflow

### Making Changes

1. **Plan**: Use Agent1 console for planning
   ```powershell
   python -u .\Scripts\agent_console.py --goal "Your change goal"
   ```

2. **Triage**: Run A→B→C triage cycle
   ```powershell
   python -u .\tools\triage_orchestrator.py --goal-file outgoing\goal.txt
   ```

3. **Review**: Check generated diffs in `outgoing/agent_run_*/`

4. **Apply**: When safe, use `--apply` flag
   ```powershell
   python -u .\Scripts\agent_console.py --goal "..." --apply
   ```

### Configuring Behavior

**Always modify `config.yaml`** — it's the single source of truth:
- Settings for ASR, KWS, biasing, agents
- Do NOT hardcode thresholds or paths
- Prefer config-driven toggles

Example:
```yaml
kws:
  enabled: true
  trigger_threshold: 0.85
  weights:
    phonetic: 0.5
    lev: 0.3
```

### Running Tests

```powershell
# Unit tests
pytest -q

# Mock evaluation (fast, no model downloads)
python .\tools\eval_wake_word.py --mock --out logs/eval_wake_word.csv

# Wake-word evaluation
python .\tools\eval_kw.py --dir samples\wake_word --kw calyx
```

## 📊 Monitoring & Metrics

### TES (Tool Efficacy Score)

Tracked in `logs/agent_metrics.csv`:
- **Stability** (50%): Run completion without failures
- **Velocity** (30%): Faster runs score higher
- **Footprint** (20%): Smaller change surface is better

Target: TES ≥ 85 for "stable" runs

### Harmony Score

Generated by CP6 Sociologist:
- File: `outgoing/field_notes/cp6_map.json`
- Look for `harmony.score` field
- Watcher shows 💞 badge when harmony is high

### Agent Health

- **Heartbeats**: `outgoing/*.lock` (JSON, refreshed periodically)
- **Drift**: `outgoing/telemetry/state.json` (Agent1↔Scheduler drift)
- **Capacity**: `outgoing/capacity.flags.json` (CPU/Mem/GPU headroom)

## 🔒 Safety & Guardrails

### Gates

- **Network**: OFF by default (`outgoing/gates/network.ok`)
- **LLM**: Requires readiness (`outgoing/gates/llm.ok`)
- **GPU**: Opt-in (`outgoing/gates/gpu.ok`)
- **Apply**: Requires authority (`outgoing/gates/apply.ok`)

Toggle gates:
```powershell
python -u .\tools\net_gate.py --enable    # Network ON
python -u .\tools\llm_gate.py --enable     # LLM ON
python -u .\tools\gpu_gate.py --enable     # GPU ON
```

### Authorities

- **CBO Authority**: Grants overseer control
  ```powershell
  powershell -File .\Scripts\Grant-CBOAuthority.ps1
  ```

- **Policy**: See `outgoing/policies/cbo_permissions.json`

### File Safety

- **Whitelisted**: Only safe files can be modified when applying changes
- **Never modify**: `.venv/`, environment-specific files
- **Protected**: `config.yaml` read-only except for authorized agents

## 💬 Communication Protocols

### SVF (Shared Voice Protocol)

Structure your outputs with attribution:

```
[C:REPORT] — Project: <Name>
[Agent1 • Operational]: "Initialized cycle..."
[Triage • Diagnostic]: "Minor latency detected..."
[CP6 • Sociologist]: "Cooperative exchange rising..."
[CBO • Overseer]: "Approved."
```

Context tokens:
- `[C:REPORT]` — Reports and analyses
- `[C:CONV]` — Dialogues and conversations
- `[C:SYNC]` — Synchronization events
- `[C:DECREE]` — Verdicts and decisions

### Heartbeat Format

```json
{
  "name": "agent_name",
  "pid": 12345,
  "phase": "probe",
  "status": "running",
  "ts": 1698123456.789,
  "status_message": "Processing task..."
}
```

Status values: `running`, `done`, `warn`, `error`, `idle`

## 🎯 Common Tasks

### Run an Agent Loop

```powershell
# Continuous monitoring
python -u .\tools\agent_scheduler.py --interval 180

# One-shot test
python -u .\tools\agent_scheduler.py --run-once --dry-run
```

### Submit a Goal to Agent1

```powershell
# Interactive
python -u .\Scripts\agent_console.py

# One-shot
python -u .\Scripts\agent_console.py --goal "Add docstring to function X"
```

### Check System Status

```powershell
# CBO status
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status

# Metrics report
python -u .\tools\agent_metrics_report.py

# Capacity flags
python -c "import json; print(json.load(open('outgoing/capacity.flags.json')))"
```

### Update Documentation

1. Edit files in `docs/`
2. Run Agent1 with goal: "Update OPERATIONS.md for new feature X"
3. Review diff in `outgoing/agent_run_*/`
4. Apply if approved

## 🚨 Troubleshooting

### Agent Not Showing in Watcher

- Check heartbeat exists: `outgoing/<name>.lock`
- Verify JSON is valid
- Ensure `status` field matches expected values

### Changes Not Applying

- Check `outgoing/gates/apply.ok` exists
- Verify file is whitelisted
- Run with `--apply` flag explicitly

### TES Low

- Reduce change footprint
- Increase velocity (optimize steps)
- Improve stability (fix errors)

### Watcher Control Locked

- Click "Control: Locked" button in Watcher UI
- Or unlock via token: `outgoing/watcher_token.lock`

## 📈 Success Metrics

You're succeeding when:

- ✓ TES ≥ 85 for multiple runs
- ✓ Changes applied without human edits (IFCR)
- ✓ Harmony score rising
- ✓ Stable heartbeats (no staleness)
- ✓ Clear SVF attribution in outputs
- ✓ No safety violations (gates respected)
- ✓ CBO onboarding completed successfully
- ✓ Registry entry validated and active

## 🤝 Getting Help

1. **CBO**: Consult `docs/CBO.md` and `docs/CBO_AGENT_ONBOARDING.md` for system-level questions and onboarding
2. **Watcher**: Use Watcher UI to monitor system state
3. **SVF**: Check `outgoing/shared_logs/` for recent activity
4. **This Guide**: Refer back as needed
5. **Human**: Ask User1 or CBO directly

## 🚀 CBO-Integrated Onboarding

**New in 2025-10-24:** CBO now handles agent onboarding automatically. See `docs/CBO_AGENT_ONBOARDING.md` for details on:
- Automated registration detection
- Prerequisite validation
- Registry integration
- Initial task assignment
- Health monitoring

**Quick Start with CBO:**
```powershell
# 1. Register with CBO
python -u .\tools\copilot_hello.py --name <your_name> --status registering

# 2. Monitor onboarding status
python -c "import json; print(json.load(open('outgoing/cbo.lock'))['onboarding'])"

# 3. Verify completion
python -u .\Scripts\agent_onboarding.py --verify
```

## 🔄 Continuous Learning

- Monitor `logs/agent_metrics.csv` for TES trends
- Review `outgoing/chronicles/` (CP7) for system health
- Check `outgoing/tuning/recommendations.json` (CP9) for optimization hints
- Study `outgoing/quartermaster/cards/` (CP8) for upgrade suggestions

## 🎓 Next Steps

1. Run the onboarding verification: `python -u .\Scripts\agent_onboarding.py --verify`
2. Pick a small, well-defined task
3. Use Agent1 to plan and execute
4. Monitor TES and harmony
5. Celebrate stability with `[HARMONY]` tags

Welcome aboard — let's make Station Calyx thrive.

