# Quick Reference Guide — Station Calyx

A concise cheat sheet for common agent tasks and commands.

## 🚀 Starting Points

### Verify Onboarding
```powershell
python -u .\Scripts\agent_onboarding.py --verify
python -u .\Scripts\agent_onboarding.py --guide
```

### Emit Heartbeat
```powershell
python -u .\tools\copilot_hello.py --name <your_name> --status running --message "Working..." --ttl 30
```

### Open Watcher UI
```powershell
python -u .\Scripts\agent_watcher.py --page-size 10 --hide-idle
```

## 🎯 Common Agent Commands

### Agent1 Console
```powershell
# Interactive
python -u .\Scripts\agent_console.py

# One-shot goal
python -u .\Scripts\agent_console.py --goal "Add feature X"

# With apply
python -u .\Scripts\agent_console.py --goal "..." --apply

# Dry-run
python -u .\Scripts\agent_console.py --goal "..." --dry-run

# Limit steps
python -u .\Scripts\agent_console.py --goal "..." --steps 1
```

### Triage Cycle
```powershell
# Complete A→B→C triage
python -u .\tools\triage_orchestrator.py --goal-file outgoing\goal.txt

# With pytest
python -u .\tools\triage_orchestrator.py --goal-file outgoing\goal.txt --pytest
```

### Scheduler
```powershell
# Continuous (every 3 min)
python -u .\tools\agent_scheduler.py --interval 180

# Auto-promote
python -u .\tools\agent_scheduler.py --interval 180 --auto-promote

# One-shot test
python -u .\tools\agent_scheduler.py --run-once --dry-run
```

## 🔍 Monitoring & Status

### Check System Status
```powershell
# CBO status
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status

# Metrics report
python -u .\tools\agent_metrics_report.py

# Capacity flags
python -c "import json; print(json.load(open('outgoing/capacity.flags.json')))"
```

### View Recent Activity
```powershell
# SVF recent logs
ls outgoing\shared_logs\ | Select-Object -Last 5

# Latest agent run
ls outgoing\agent_run_* | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Check heartbeats
ls outgoing\*.lock | Select-Object Name, LastWriteTime
```

### TES (Tool Efficacy Score)
```powershell
# View metrics CSV
Import-Csv logs\agent_metrics.csv | Select-Object -Last 10

# Generate report
python -u .\tools\agent_metrics_report.py
```

## 🔧 Configuration

### Modify Config
```powershell
# Edit config.yaml (in your editor)
notepad config.yaml
```

Common settings:
```yaml
kws:
  trigger_threshold: 0.85      # Wake-word sensitivity
  weights:
    phonetic: 0.5
    lev: 0.3

scheduler:
  interval_sec: 300             # Agent interval
  auto_promote: true            # Enable promotion
```

### Gates (Feature Toggles)
```powershell
# Network gate
python -u .\tools\net_gate.py --enable   # ON
python -u .\tools\net_gate.py --disable  # OFF

# LLM gate
python -u .\tools\llm_gate.py --enable

# GPU gate
python -u .\tools\gpu_gate.py --enable

# Check gates
ls outgoing\gates\*.ok
```

## 🛠️ Testing

### Unit Tests
```powershell
pytest -q                    # Quick test
pytest -v                    # Verbose
pytest -k "test_kws"         # Specific test
```

### Mock Evaluation
```powershell
# Wake-word eval (mock mode)
python .\tools\eval_wake_word.py --mock --out logs/eval_wake_word.csv

# KWS eval
python .\tools\eval_kw.py --dir samples\wake_word --kw calyx
```

### Real-Time Listeners
```powershell
# Wake listener
python -u .\Scripts\listener_wake.py

# Plus listener (tighter config)
python -u .\Scripts\listener_plus.py

# Debug listener (no scipy)
python -u .\Scripts\listener_plus_debug_noscipy.py
```

## 📊 Agents & Copilots

### Start Agent Loops
```powershell
# CP6 Sociologist
python -u .\tools\cp6_sociologist.py --interval 5

# CP7 Chronicler
python -u .\tools\cp7_chronicler.py --interval 5

# CP8 Quartermaster
python -u .\tools\cp8_quartermaster.py --interval 10

# CP9 Auto-Tuner
python -u .\tools\cp9_auto_tuner.py --interval 15

# CP10 Whisperer
python -u .\tools\cp10_whisperer.py --interval 20

# CP12 Coordinator
python -u .\tools\cp12_coordinator.py --interval 10
```

### Probes & Monitors
```powershell
# Triage Probe (WSL)
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/triage_probe.py --interval 2 --adaptive"

# Traffic Navigator (WSL, control)
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/traffic_navigator.py --interval 3 --control"

# Systems Integrator (WSL)
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/sys_integrator.py --interval 10"

# SVF Probe
python -u .\tools\svf_probe.py --interval 5
```

## 📝 Documentation

### Key Documents
- `docs/AGENT_ONBOARDING.md` — Comprehensive onboarding guide ⭐
- `COMPENDIUM.md` — Agent roster and roles
- `docs/CBO.md` — Overseer system
- `docs/TRIAGE.md` — Change workflow
- `OPERATIONS.md` — Commands and operations
- `ARCHITECTURE.md` — System design
- `.github/copilot-instructions.md` — Repository-specific guidance

### Update Documentation
```powershell
# Add command to OPERATIONS.md
python -u .\Scripts\agent_console.py --goal "Add section X to OPERATIONS.md"

# Update Compendium for new agent
python -u .\Scripts\agent_console.py --goal "Add cpX to COMPENDIUM.md"
```

## 💬 SVF Communication

### Structure Outputs
```
[C:REPORT] — Project: <Name>
[Agent1 • Operational]: "Task completed..."
[Triage • Diagnostic]: "Status OK..."
[CBO • Overseer]: "Approved."
```

### Context Tokens
- `[C:REPORT]` — Reports and analyses
- `[C:CONV]` — Dialogues and conversations
- `[C:SYNC]` — Synchronization events
- `[C:DECREE]` — Verdicts and decisions

### Tags
- `[HARMONY]` — TES > 85, stable runs
- `[RISK]` — Staleness >10m or heavy runs
- `[SOCIAL_IMPACT]` — CP6
- `[HEARTBEAT_UNSTABLE]` — Agent1
- `[TECHNICAL_FAULT]` — SysInt

## 🔒 Safety Commands

### Check Capacity
```powershell
python -c "import json; print(json.load(open('outgoing/capacity.flags.json')))"
```

### Verify Gates
```powershell
ls outgoing\gates\*.ok
```

### Grant CBO Authority
```powershell
powershell -File .\Scripts\Grant-CBOAuthority.ps1
```

### Check Apply Gate
```powershell
Test-Path outgoing\gates\apply.ok
```

## 🎨 Watcher UI

### Customize Icons
Edit `outgoing/watcher_icons.json`:
```json
{
  "agent1": "🤖",
  "triage": "🧪",
  "navigator": "🧭",
  "cp6": "💞",
  "cp7": "📜"
}
```

### Watcher Commands
- Click "❓ Legend" to view icon/color mappings
- Click "Control: Locked" to unlock control
- Badges: 💞 Harmony, 🎛️ Control, 📊 Telemetry, 🔧 System

## 🚨 Troubleshooting

### Agent Not in Watcher
```powershell
# Check heartbeat exists
Test-Path outgoing\<name>.lock

# Emit heartbeat
python -u .\tools\copilot_hello.py --name <name> --status running
```

### Changes Not Applying
```powershell
# Check apply gate
Test-Path outgoing\gates\apply.ok

# Check file whitelist
python -u .\Scripts\agent_console.py --goal "..." --dry-run
```

### PowerShell ExecutionPolicy
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\Scripts\.venv\Scripts\Activate.ps1; python -u .\Scripts\listener_wake.py }"
```

### SciPy Issues
```powershell
# Use debug listener
python -u .\Scripts\listener_plus_debug_noscipy.py
```

## 📈 Success Indicators

Look for:
- TES ≥ 85 in `logs/agent_metrics.csv`
- Stable heartbeats (no staleness warnings)
- Rising harmony score (`outgoing/field_notes/cp6_map.json`)
- Successful triage cycles (A→B→C pass)
- SVF attribution in outputs
- No gate violations

## 🆘 Getting Help

1. Run onboarding verification: `python -u .\Scripts\agent_onboarding.py --verify`
2. Check Watcher UI for system state
3. Consult `docs/AGENT_ONBOARDING.md` for comprehensive guidance
4. Review `OPERATIONS.md` for common workflows
5. Ask User1 or CBO directly

---

**Quick Start Checklist:**
- [ ] Read `docs/AGENT_ONBOARDING.md`
- [ ] Run `--verify` check
- [ ] Emit heartbeat
- [ ] Start Watcher UI
- [ ] Pick a domain
- [ ] Make your first change
- [ ] Monitor TES and harmony
