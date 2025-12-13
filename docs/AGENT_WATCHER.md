# Calyx Agent Watcher

## Overview

The Calyx Agent Watcher is a dual-component system consisting of:
1. **Backend Monitoring Service** (`tools/agent_watcher.py`) - Continuously monitors all agents
2. **UI Dashboard** (`Scripts/agent_watcher.py`) - Real-time Tkinter dashboard for visualizing agent status

Together, they provide comprehensive visibility into agent activity, health, and interactions across Station Calyx.

## Purpose

- **Real-time monitoring**: Continuously observe all registered agents in the system
- **Visual dashboard**: User-friendly Tkinter interface for agent status
- **Health tracking**: Monitor agent process status, lock files, and resource usage
- **Alerting**: Detect and report unhealthy or offline agents
- **Control integration**: Support for banners, logs, toasts via agent_control
- **Integration**: Works seamlessly with the coordinator and CBO for system-wide observability

## Agent Registration

The agent watcher is registered in `calyx/core/registry.jsonl` with the following configuration:

```json
{
  "skills": ["monitoring", "observability", "agent-tracking"],
  "interval_sec": 10,
  "autonomy": "managed",
  "role": "watchdog",
  "agent_id": "agent-watcher",
  "executable": "Scripts/agent_watcher.py"
}
```

## Usage

### Launching the Dashboard

```bash
# Open the dashboard (requires backend to be running)
python Scripts/agent_watcher.py

# Show only active agents
python Scripts/agent_watcher.py --hide-idle

# Custom page size
python Scripts/agent_watcher.py --page-size 10

# Via launch script
Scripts\Launch-Agent-Watcher.bat
```

### Launching via Agent Launcher

Use the buttons in `Scripts/agent_launcher.py`:
- **"Open Watcher"** - Standard dashboard view
- **"Open Watcher (Paged)"** - Paged view with idle agents hidden

### Running the Backend Monitor

The UI dashboard reads from a backend monitoring service. Start it with:

```bash
# Run backend monitoring service
python tools/agent_watcher.py --interval 10
```

### Via Coordinator

The agent watcher can be launched through the coordinator by creating a dispatch file:

```json
{
  "targets": ["agent-watcher"],
  "action": "start",
  "domain": "win",
  "args": "--interval 10"
}
```

Place this in `outgoing/bridge/dispatch/` and CP12 will handle the launch.

## Architecture

### Backend Monitoring Service (`tools/agent_watcher.py`)

Runs continuously in the background to:
- Monitor agent processes
- Check lock files
- Calculate health scores
- Write status data

**Output Files** (in `outgoing/agent_watcher/`):

- `status.json` - Current snapshot of all agent states
- `history.jsonl` - Complete observation history
- `alerts.jsonl` - Alert stream for unhealthy agents
- `agent_watcher.lock` - Backend heartbeat

### UI Dashboard (`Scripts/agent_watcher.py`)

Tkinter-based dashboard that:
- Reads status from backend
- Displays real-time agent status
- Shows detailed agent information
- Supports control commands via `agent_control`
- Generates token for secure command channel

**Control Files**:
- `watcher_token.lock` - Authentication token for commands
- `watcher_cmds/` - Directory for incoming commands
- `watcher_prefs.json` - User preferences

### Command Channel

Other agents can send commands to the watcher using `tools/agent_control.py`:

```python
from tools.agent_control import post_command

# Set banner message
post_command("set_banner", {"text": "System operational", "color": "#1f6feb"})

# Append to log
post_command("append_log", {"text": "Agent1 completed task"})

# Show toast notification
post_command("show_toast", {"text": "Alert: High CPU usage"})
```

## Agent Health Scoring

Each agent receives a health score (0-100) based on:

- **100 points**: Process running + fresh lock file (< 5 minutes old)
- **80 points**: Process running + lock file < 10 minutes old
- **70 points**: Process running but no lock file OR process running + stale lock file
- **60 points**: Process running but lock file very stale (> 10 minutes)
- **50 points**: Lock file exists but no process
- **0 points**: Neither process nor lock file present

## Status Messages

- **"Healthy and operational"**: Score ≥ 90
- **"Operational"**: Score ≥ 70
- **"Degraded"**: Score ≥ 50
- **"Unhealthy or offline"**: Score < 50

## Integration with Other Systems

### CP12 Coordinator
The watcher is automatically dispatchable through CP12. You can send commands to start/stop it via dispatch files.

### Agent Health Monitor
The watcher complements the existing `agent_health_monitor.py`:
- **Agent Health Monitor**: Detects and attempts recovery of unhealthy agents
- **Agent Watcher**: Provides real-time visibility and alerts without recovery actions

### CP7 Chronicler
The watcher provides data that CP7 can consume for system chronicling and historical analysis.

## Monitoring Example

When running, the watcher outputs:

```
[AGENT_WATCHER] Loaded 11 registered agents
[21:51:33] Active: 6/11 (Health: 54.5%)
  [WARNING] scheduler-main (scheduler) is unhealthy (score: 0.0)
  [WARNING] scheduler-agent2 (scheduler) is unhealthy (score: 0.0)
  [WARNING] teaching-loop (teaching) is unhealthy (score: 0.0)
  [WARNING] bridge-overseer (orchestrator) is unhealthy (score: 0.0)
  [WARNING] cbo-api (service) is unhealthy (score: 0.0)
```

## Technical Details

### Process Detection
The watcher uses `psutil` to find agent processes by matching:
- Agent ID in command line
- Executable path/name
- Script name extraction

### Lock File Checking
Checks for existence and age of `outgoing/{agent_id}.lock` files.

### Resource Monitoring
Tracks per-agent:
- CPU usage percentage
- Memory usage (MB)
- Process status

### Registry Loading
Automatically loads agent definitions from `calyx/core/registry.jsonl` and reloads periodically (every 10 iterations) to pick up changes.

## Limitations

- Does not attempt recovery (that's the job of Agent Health Monitor)
- Requires agents to be registered in `calyx/core/registry.jsonl`
- Relies on process command-line matching for identification
- No external dependencies beyond psutil (optional SVF integration)

## Future Enhancements

Potential improvements for discussion with CBO:
- Integration with TES scoring
- Cross-agent interaction tracking
- Resource trend analysis
- Configurable alert thresholds
- Web dashboard integration
- Historical pattern recognition

## Files Created

### Backend
- `tools/agent_watcher.py` - Backend monitoring service
- `outgoing/agent_watcher/` - Status and history files

### UI Dashboard
- `Scripts/agent_watcher.py` - Tkinter dashboard application
- `Scripts/Launch-Agent-Watcher.bat` - Windows launch script
- `outgoing/watcher_token.lock` - Authentication token
- `outgoing/watcher_prefs.json` - User preferences
- `outgoing/watcher_cmds/` - Command queue directory

### CBO Integration

The Agent Watcher includes comprehensive CBO integration:

**CBO Status Button**: Shows a multi-tab window with:
- **Status Tab**: Current CBO process status, coordinator state, and system health
- **Recent Reports Tab**: List of latest CBO diagnostic and oversight reports
- **TES Metrics Tab**: Task Efficiency Score metrics and recent averages

**CBO Reports Button**: Browse and open recent CBO reports from `outgoing/overseer_reports/`

**TES Metrics Button**: View detailed Task Efficiency Score data

The watcher automatically detects:
- CBO bridge overseer process status
- Latest CBO reports and modifications
- Coordinator operational state
- TES metrics from agent logs
- System health integration

### Integration
- Registry entry in `calyx/core/registry.jsonl`
- Control system via `tools/agent_control.py`
- CBO status monitoring and reports
- TES metrics integration
- Coordinator state visibility
- This documentation

