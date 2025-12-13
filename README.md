# Calyx Terminal

Station Calyx governance and operation repo producing Outcome Density runs to assess system health, stability, and value in autonomous governance research. Local, real-time speech pipeline with optional wake-word biasing ("Calyx") and a lightweight phonetic KWS post-filter. Intended for development and experimentation on Windows PowerShell.

## Try it

```powershell
python -u .\Scripts\listener_plus.py
```
## Quickstart

Prerequisites

- Python 3.10+ (use a venv)
- `requirements.txt` provides runtime deps

Activate virtualenv (PowerShell):

```powershell
.\Scripts\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Quick runtime checks

```powershell
python .\Scripts\quick_check.py
python -u .\Scripts\listener_plus.py
python -u .\Scripts\listener_wake.py
```

Microphone index and quick checks

```powershell
# show available audio devices and their indexes
python .\Scripts\list_mics.py

# run a mic sanity check (VU / short recording)
python .\Scripts\quick_check.py

# run wake listener
python -u .\Scripts\listener_wake.py

# run evaluation in mock mode (no model downloads)
python .\tools\eval_wake_word.py --mock --out logs/eval_wake_word.csv
```

Run tests

```powershell
pytest -q
```

Evaluation (if available)

```powershell
python .\tools\eval_wake_word.py --cfg config.yaml --model small
```

Where to look

- `asr/` — core pipeline: `pipeline.py`, `kws.py`, `normalize.py`, `config.py`
- `Scripts/` — runnable listeners and utilities
- `samples/wake_word/` — positive/negative examples for evaluation
- `logs/wake_word_audit.csv` — KWS audit logging
- `outgoing/telemetry/state.json` — lightweight telemetry (agents active, drift agent1↔scheduler)
- Customize Watcher icons: `outgoing/watcher_icons.json` (emoji per agent name)
- Compendium of agents/copilots/overseers: `docs/COMPENDIUM.md`

Agent Onboarding

- Comprehensive guide: `docs/AGENT_ONBOARDING.md` ⭐ (start here!)
- Quick reference: `docs/QUICK_REFERENCE.md` (common commands)
- Onboarding tool: `python -u .\Scripts\agent_onboarding.py --verify`
- Copilot guide: `docs/COPILOTS.md` (copilot-specific guidance)

Milestones

- See `MILESTONES.md` for landmark achievements and team accolades.
- See `logs/HEARTBEATS.md` for a chronological index of heartbeat events (including the Genesis heartbeat).
- See `logs/EVOLUTION.md` for multi-agent evolution stages and links to detailed reports.

Triage

- Learn about the 3-phase triage loop (A: proposer/validator, B: reviewer, C: stability) and how to run it: `docs/TRIAGE.md`.

Tasks & goals

- Unified dashboard: `logs/TASKS.md` (human-readable)
- Machine view: `outgoing/tasks_dashboard.json`
- To regenerate:

```powershell
python -u .\tools\generate_task_dashboard.py
```

Agent Watcher control (bridge)

- The watcher GUI can accept safe commands from Agent1 when you explicitly unlock control.
- Start the watcher, click "Control: Locked" to unlock, then run the test:

```powershell
python -u .\tools\test_watcher_control.py
```

See `docs/TRIAGE.md` for the triage loop, and `OPERATIONS.md` for watcher control details.

Contributing

- Keep changes config-driven and add unit tests for new behavior.
- Update `requirements.txt` when adding new packages.

Troubleshooting

- SciPy / soundfile issues: on some Windows machines `soundfile` or `scipy` installations fail. If you encounter import errors for `soundfile` or `scipy` when running real audio paths, either:
	- Install the binary wheels from PyPI using `pip install soundfile scipy` (ensure a compatible Python version), or
	- Use the lightweight debug listener which avoids SciPy dependencies: `Scripts/listener_plus_debug_noscipy.py` (this script uses a simplified audio path and is intended for quick local debugging).

- ExecutionPolicy blocking script activation: see `OPERATIONS.md` for the temporary `-ExecutionPolicy Bypass` commands to run the venv activation or listeners without changing system policy.
