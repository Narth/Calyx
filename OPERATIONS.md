# OPERATIONS.md

Overseer quick start
--------------------

For a one-command bring-up with guardrails, use the Calyx Bridge Overseer:

```powershell
powershell -File .\Scripts\Calyx-Overseer.ps1
```

Status only:

```powershell
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status
```

See `docs/CBO.md` for options and scheduled start at logon.

Station Pulse — Traffic Flow Dashboard
---------------------------------------

View Station Calyx as a living traffic network with 10-second orientation:

```powershell
python -u .\tools\station_pulse.py
```

Console snapshot mode:

```powershell
python -u .\tools\station_pulse.py --console
```

Export current state:

```powershell
python -u .\tools\station_pulse.py --export-snapshot reports/pulse_snapshot.json
```

The dashboard shows agents grouped by lane (Builder, Oversight, Service, Scheduler, Monitoring), system posture (Calm/Moderate/Congestion/Distressed), CBO dispatch status, and gate states. It complements Agent Watcher (detailed multi-agent coordination) and CBO Indicator (bridge status overlay) by providing a human-aligned traffic flow perspective.

Activate virtualenv (PowerShell):

```powershell
.
Scripts\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution due to ExecutionPolicy, you can run a temporary process-scoped bypass to activate the venv and run a listener. Two helpful one-liners:

- Open an elevated PowerShell once and allow the current process to run scripts (temporary, process-scoped):

```powershell
Light task scheduler (auto-promote optional)
-------------------------------------------

Keep small progress going with a tiny micro-goal every 3 minutes. Use VS Code tasks:

- Agent1: Light Task Loop (3 min) — conservative mode
- Agent1: Light Task Loop (auto-promote) — gradually increases autonomy after stable runs
- Agent1: Light Task Once (dry-run) — quick validation without invoking the agent

CLI:

```powershell
python -u .\tools\agent_scheduler.py --interval 180
# with auto-promotion
python -u .\tools\agent_scheduler.py --interval 180 --auto-promote --promote-after 5 --cooldown-mins 30
```

Auto-promotion rules:

- Modes: safe → tests → apply_tests (one level at a time)
- Promote when there are N (default 5) consecutive stable runs in the current mode with TES≥85 and velocity≥0.5
- Cooldown: 30 minutes between promotions (configurable)
- State is tracked in `logs/agent_scheduler_state.json`

CBO integration:

- When CBO policy grants full access and GPU/LLM are ready, CBO starts the Agent Scheduler with `--auto-promote` and the hardened thresholds apply automatically.

Hardened promotion (GPU-ready):

- When the CBO has full access and GPU is enabled (gates: `outgoing/policies/cbo_permissions.json` with `granted=true` and `full_access=true`, and `outgoing/gates/gpu.ok` exists), the scheduler tightens promotion criteria by default.
- Defaults: require 7 consecutive OK runs with TES≥90, velocity≥0.65, duration≤240s, and total LLM time≤15s per run. Also requires `outgoing/llm_ready.lock` to be present and OK.
- You can override via `config.yaml` → `settings.scheduler.hardening`:
	- `enable`: true|false
	- `tes_min`: number (default 90)
	- `velocity_min`: number (default 0.65)
	- `max_duration_s`: number (default 240)
	- `max_llm_time_s`: number (default 15)
	- `consecutive`: integer (default 7)
	- `require_gpu`: true|false (default true)
	- `require_llm_ready`: true|false (default true)

powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\Scripts\.venv\Scripts\Activate.ps1; python -u .\Scripts\listener_wake.py }"
```

- Alternatively, start a new PowerShell process with a temporary ExecutionPolicy for the session, then activate the venv interactively:

```powershell
powershell -ExecutionPolicy Bypass
# then in the new shell:
.\Scripts\.venv\Scripts\Activate.ps1
```

Mic and runtime quick commands

- List audio devices (find mic index):

```powershell
python .\Scripts\list_mics.py
```

- Mic sanity (VU & quick check):

```powershell
python .\Scripts\quick_check.py
```

- Run wake listener (real-time):

```powershell
python -u .\Scripts\listener_wake.py
```

- Run the "plus" real-time example (uses tighter decoding config):

```powershell
python -u .\Scripts\listener_plus.py
```

- Evaluation (mock mode — fast, no model downloads):

```powershell
python .\tools\eval_wake_word.py --mock --out logs/eval_wake_word.csv
```

Wake-word evaluation (fast)
---------------------------

Quick sweep over `samples/wake_word/{positive,negative}` with PASS/FAIL summary.

Mock mode (default, no model needed; uses sidecar transcripts when available):

```powershell
python .\tools\eval_kw.py --dir samples\wake_word --kw calyx
```

Enable the soft phonetic heuristic and re-run:

```powershell
# Edit config.yaml first:
#   settings.kws.phonetic.allow: true
#   settings.kws.weights.phonetic_soft: 0.15

python .\tools\eval_kw.py --dir samples\wake_word --kw calyx
```

Real mode (uses faster-whisper if installed):

```powershell
python .\tools\eval_kw.py --dir samples\wake_word --kw calyx --real
```

The tool prints FRR, FAR, F1, and avg latency at the configured trigger threshold and writes a CSV to `logs/`.

Export/packaging

```powershell
powershell -File .\Scripts\Calyx-Export.ps1 -Label "checkpoint"
```

Milestones and heartbeats

- Milestones & Accolades: see `MILESTONES.md`.
- Heartbeats index (chronological): see `logs/HEARTBEATS.md`.

Triage (A/B/C)

- Overview and commands: see `docs/TRIAGE.md` (covers proposer/validator, reviewer, and stability phases plus domain coverage checklist).

Tasks dashboard

- Generate the dashboard (JSON + Markdown):

```powershell
python -u .\tools\generate_task_dashboard.py
```

- View a live console board (3s refresh, auto-regen):

```powershell
python -u .\Scripts\tasks_board.py --watch 3 --regen
```

Telemetry (drift and activity)

- Compute telemetry once (writes `outgoing/telemetry/state.json`):

```powershell
python -u .\tools\compute_telemetry.py
```

- Or run in a loop (e.g., every 5s):

```powershell
python -u .\tools\compute_telemetry.py --interval 5
```


Agent watcher GUI

Keep a tiny status window open to see when the local agent/triage are working. It reads heartbeats from `outgoing/agent1.lock` and `outgoing/triage.lock` written by the agent and orchestrator.

```powershell
python -u .\Scripts\agent_watcher.py
```

BitNet LLM Integration
----------------------

Run local 1.58-bit LLM inference via WSL2 BitNet bridge:

```powershell
# Basic inference
python -u .\Scripts\agent_bitnet.py --prompt "Your question here"

# Custom parameters
python -u .\Scripts\agent_bitnet.py `
  --prompt "Explain Station Calyx" `
  --n-predict 100 `
  --temperature 0.5 `
  --threads 4

# Configuration validation
python -u .\Scripts\agent_bitnet.py --prompt "test" --dry-run
```

**Requirements:**
- WSL2 Ubuntu with BitNet compiled at `~/bitnet_build/BitNet/`
- Gate authorization: `outgoing/gates/bitnet.ok` with `enabled: true`
- Config section: `config.yaml` → `bitnet`

**See**: `docs/BITNET_INTEGRATION.md` for full documentation

Network gates and local-first operation
--------------------------------------

Teaching dashboard
------------------

Monitor teaching/training cycles at a glance (policy, activity, TES, overrides):

```powershell
python -u .\Scripts\teaching_dashboard.py --top
```

- One-shot console summary:

```powershell
python -u .\Scripts\teaching_dashboard.py --once
```

Enable cycles via Overseer flags or policy:

```powershell
# Start overseer with optimizer and teaching enabled
python -u .\tools\cbo_overseer.py --enable-optimizer --enable-teaching --teach-interval-mins 30
```

Or set in policy (`outgoing/policies/cbo_permissions.json`):

```json
{
	"features": {
		"teaching_cycles": { "enabled": true, "max_parallel": 1, "interval_minutes_default": 30 }
	}
}
```

Quick test of a teaching cycle (one-shot):

```powershell
python -u .\tools\cbo_optimizer.py --once --force-teach
```

- Network OFF (recommended default):
	- Outbound network is blocked by `sitecustomize.py` unless the gate file exists at `outgoing/gates/network.ok`.
	- Toggle via helper: `python -u tools\\net_gate.py --disable` (OFF) / `--enable` (ON)

- LLM gate:
	- Local LLM readiness is tracked by `outgoing/llm_ready.lock` and the gate by `outgoing/gates/llm.ok`.
	- Toggle via helper: `python -u tools\\llm_gate.py --enable` (recommended; uses local LLM, not Copilot).

- Timed network burst:
	- Allow a short, controlled egress window, then auto-disable:
		- `python -u tools\\net_burst.py --minutes 3`
	- Useful when primarily offline but needing brief syncs.

Shared Voice Protocol (SVF v1.0)
---------------------------------

SVF is ACTIVE effective 2025-10-22. All agents and copilots must structure shared outputs with attribution and a context token.

- Canonical document: `Codex/COMM_PROTOCOL_SHARED_VOICE.md`
- Policy signal: `outgoing/policies/shared_voice.json` (status, version, required tokens)
- Registry record: `outgoing/overseer_reports/protocol_registry/SHARED_VOICE_PROTOCOL_v1.json`
- Evolution entry: `outgoing/evolution/LOG_2025-10-22_SHARED_VOICE_PROTOCOL_V1.txt`

Quick adoption (minimum):

1) Prefix lines with attribution and tone:
	- `[Agent1 • Operational]: "..."`
	- `[Triage • Diagnostic]: "..."`
	- `[CP6 • Sociologist]: "..."`
	- `[CP7 • Chronicler]: "..."`
	- `[CBO • Overseer]: "..."`
	- `[CGPT • Chronicler]: "..."`

2) Start each shared log with an SVF context token, e.g. `[C:REPORT]` or `[C:CONV]`.

3) Archive outputs under:
	- `outgoing/shared_logs/` (reports)
	- `outgoing/dialogues/` (conversations)
	- `outgoing/overseer_reports/` (verdicts/decrees)

Template excerpt:

```
[C:REPORT] — Project: <Name>
[Agent1 • Operational]: "Initialized cycle..."
[Triage • Diagnostic]: "Minor latency detected..."
[CP6 • Sociologist]: "Cooperative exchange rising..."
[CP7 • Chronicler]: "Logged under /outgoing/chronicles/..."
[CBO • Overseer]: "Approved."
[CGPT • Chronicler]: "Consolidated."
```

SVF Probe (keep comms active)
-----------------------------

Run the SVF probe continuously to publish an SVF heartbeat and sync dialogues when participants change.

Windows PowerShell (continuous):

```powershell
python -u .\tools\svf_probe.py --interval 5
# or via the wrapper
python -u .\Scripts\agent_svf.py --interval 5
```

Short test (5 iterations, emit a sample report):

```powershell
python -u .\tools\svf_probe.py --interval 1 --max-iters 5 --emit-sample
```

Artifacts:

- Heartbeat: `outgoing/svf.lock` (status, participants, policy version)
- Dialogues on participant change: `outgoing/dialogues/svf_sync_<ts>.md` (uses `[C:SYNC]`)
- Optional sample report: `outgoing/shared_logs/svf_probe_report_<ts>.md` (uses `[C:REPORT]`)

Watcher: With auto-discovery enabled, a new `svf` row appears when the heartbeat exists.

Auto-ensure in maintenance routines:

- The following tools/scripts automatically start SVF if its heartbeat is missing/stale:
	- `tools/triage_probe.py`
	- `tools/cp7_chronicler.py`
	- `tools/agent_runner.py`
	- `Scripts/agent_console.py`
	- `Scripts/agent_watcher.py` (best-effort; UI may auto-start SVF to avoid an idle badge)

	Agent Watcher — SVF bridge
	--------------------------

	The Agent Watcher now surfaces SVF activity and pressing events:

	- SVF badge in the top strip shows live status; it turns amber when a recent tie decree exists.
	- SVF Alerts panel lists the latest ballot, decree (tie highlighted), and efficiency report with quick-open buttons.
	- You can broadcast a pressing note to the SVF dialogues using the Broadcast box; it writes a `[C:CONV]` message to `outgoing/dialogues/svf_broadcast_<ts>.md`.

	Tip: start the 90s efficiency cycle to generate ballots and potential decrees:

	```powershell
	python -u .\tools\cycle_efficiency.py --interval 90
	```

	SVF efficiency cycle monitor
	----------------------------

	Periodically runs the SVF efficiency analysis, opens a vote, tallies results, and stops automatically if a top-vote tie occurs (emits a tie decree).

	- Quick test (one cycle, ~0.5s):

	```powershell
	python -u .\tools\cycle_efficiency.py --interval 0.5 --max-cycles 1
	```

	- Continuous run (every 90s, until tie):

	```powershell
	python -u .\tools\cycle_efficiency.py --interval 90
	```

	Artifacts:
	- Reports: `outgoing/shared_logs/svf_efficiency_<ts>.md`
	- Ballots: `outgoing/dialogues/svf_vote_<ts>.md`
	- Cycle status: `outgoing/shared_logs/svf_cycle_status_<ts>.md`
	- Tie decree (on tie): `outgoing/overseer_reports/verdicts/DECREE_<date>_SVF_TIE.md`

Tone learning (SVF)
------------------

The probe learns tone signatures by scanning recent shared outputs for lines like `[Entity • Tone]: "..."` and stores the latest per-entity tones in:

- `state/comm_context.json` (last_tone)
- `outgoing/shared_voice/persona.json` (aggregate snapshot)
- `outgoing/shared_voice/persona_history.json` (rolling history with per-entity event lists, counts, first/last seen)

This keeps agentic “personality” signals discoverable without heavy overhead.

Agents registry (robust recollection)
-------------------------------------

The SVF probe keeps a lightweight registry of agents/copilots it sees via `outgoing/*.lock` and SVF participants:

- File: `outgoing/agents/registry.json`
- Per entry: name, kind (agent/copilot/system), role (best-effort), first_seen, last_seen, seen_count, last_tone, status/phase/pid (from the latest heartbeat)
- Updated continuously while the probe runs

This serves as a compact roll‑up of “who’s been here” with timing and persona cues.

Honor Roll (legacy copilots)
----------------------------

To honor early contributions where artifacts are scarce, the probe writes a small honor roll:

- File: `outgoing/agents/honor_roll.json`
- Entries: `cp1`..`cp5` as "Honorary Copilot" with a brief note.
- This file is informational; it does not imply current activity.

Backfill registry/persona (one-time or periodic)
-----------------------------------------------

Reconstruct SVF persona and the agents registry from existing artifacts:

```powershell
python -u .\tools\svf_backfill.py --max-files 200
```

Outputs:
- `outgoing/shared_voice/persona_history.json`
- `outgoing/shared_voice/persona.json`
- `state/comm_context.json` (last_tone)
- `outgoing/agents/registry.json`

Tip: run after migrating or after large batches of shared logs/dialogues.

Nightly sanitizer (canonicalize and dedupe)
------------------------------------------

Keep records clean while we iterate toward more robust resources. The sanitizer canonicalizes entity names (trims whitespace and trailing punctuation), deduplicates across registry/persona, and enforces history caps.

- Script: `tools/sanitize_records.py`
- What it does:
	- Canonicalizes keys in `outgoing/agents/registry.json`, `outgoing/shared_voice/persona.json`, and `outgoing/shared_voice/persona_history.json`
	- Deduplicates near-duplicate entities (e.g., `watcher_token` vs `watcher_token.`)
	- Fills known kind/role for standard entities (cp6–cp10, navigator, triage, etc.)
	- Trims persona history per-entity to a safe cap (default 100)
	- Writes a diagnostics report to `outgoing/chronicles/diagnostics/sanitize_report_<ts>.json`
	- Creates timestamped backups under `_diag/sanitize_backup_<ts>/` before modifying files

Run it ad hoc:

```powershell
C:/Calyx_Terminal/.venv/Scripts/python.exe -u tools/sanitize_records.py
# Dry-run (no writes):
C:/Calyx_Terminal/.venv/Scripts/python.exe -u tools/sanitize_records.py --dry-run
```

Schedule nightly on Windows (Task Scheduler):

```powershell
$Action = New-ScheduledTaskAction -Execute "C:\\Calyx_Terminal\\.venv\\Scripts\\python.exe" -Argument "-u tools\\sanitize_records.py"
$Trigger = New-ScheduledTaskTrigger -Daily -At 3:15am
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "Calyx Nightly Sanitizer" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Canonicalize & dedupe SVF records nightly"
```

Or use the helper scripts (easiest):

```powershell
# Register to run daily at 03:15 (default)
powershell -File .\Scripts\Register-NightlySanitizer.ps1

# Custom time
powershell -File .\Scripts\Register-NightlySanitizer.ps1 -Time "02:00"

# Unregister when no longer needed
powershell -File .\Scripts\Unregister-NightlySanitizer.ps1
```

Notes:
- The sanitizer is conservative and stdlib-only; it won't reach out to network resources.
- Writers (`tools/svf_probe.py`, `tools/svf_backfill.py`) already canonicalize and dedupe on write to prevent reintroduction of bad keys.


CP7 — The Chronicler
---------------------

Observe and record system health, drift, and agent responsiveness. CP7 writes:

- Human chronicles: `outgoing/chronicles/chronicle_<timestamp>.md`
- Diagnostics (JSON): `outgoing/chronicles/diagnostics/diag_report_<timestamp>.json`
- Weekly digest: `outgoing/chronicles/CP7_WEEKLY_SUMMARY.md`
- Heartbeat: `outgoing/cp7.lock`

Run (Windows PowerShell):

```powershell
python -u .\tools\cp7_chronicler.py --interval 5
# or via the script launcher
python -u .\Scripts\agent_cp7.py --interval 5
```

Smoke test (3 iterations):

```powershell
python -u .\tools\cp7_chronicler.py --interval 0.5 --max-iters 3
```

Alerts & tags used by CP7: `[HEALTH]`, `[TREND]`, `[HEALING]`, `[ALERT]`, `[STABILITY]` and escalation tags
`[SOCIAL_IMPACT]` (CP6), `[HEARTBEAT_UNSTABLE]` (Agent1), `[TECHNICAL_FAULT]` (SysInt).

CP8 — The Quartermaster
------------------------

Turn Systems Integrator and environment observations into actionable upgrade cards.

Outputs:
- Cards: `outgoing/quartermaster/cards/*.json`
- Report: `outgoing/quartermaster/report.md`
- Heartbeat: `outgoing/cp8.lock`

Run:

```powershell
python -u .\tools\cp8_quartermaster.py --interval 10
# or via launcher
python -u .\Scripts\agent_cp8.py --interval 10
```

CP9 — The Auto-Tuner
---------------------

Analyze recent metrics and propose tuning for triage cadence, navigator control, and scheduler promotions.

Outputs:
- JSON/MD: `outgoing/tuning/recommendations.{json,md}`
- Heartbeat: `outgoing/cp9.lock`

Run:

```powershell
python -u .\tools\cp9_auto_tuner.py --interval 15
# or via launcher
python -u .\Scripts\agent_cp9.py --interval 15
```

CP10 — The Whisperer
---------------------

Suggest small, safe ASR bias and KWS weight deltas based on evaluation data (or prompt you to run a mock eval).

Outputs:
- JSON/MD: `outgoing/whisperer/recommendations.{json,md}`
- Heartbeat: `outgoing/cp10.lock`

Run:

```powershell
python -u .\tools\cp10_whisperer.py --interval 20
# or via launcher
python -u .\Scripts\agent_cp10.py --interval 20
```

LLM Readiness Beacon
--------------------

Publish a global LLM readiness signal for CP6/CP7/Navigator and the Watcher. This does not load a model by default.

Outputs:
- `outgoing/llm_ready.lock` with status_message and fields: module_ok, manifest_ok, model_id, path_ok

Run:

```powershell
python -u .\tools\llm_ready.py --interval 60
# single check
python -u .\tools\llm_ready.py --once
```

Tip: run it in WSL for accurate path checks if triage runs in WSL.

Readiness Auditor (prompt)
--------------------------

A focused system prompt to evaluate whether Agent1 is ready to start the AI‑for‑All Project.

Location:
- `docs/prompts/AI4All_readiness_auditor.md`

Use it with a local or remote Copilot: paste the prompt and provide the listed inputs from this repo (locks, chronicles, metrics, CP8/9/10 outputs, and the model manifest). Expect a PASS/FAIL verdict plus a compact Markdown summary and a JSON report. Run WSL probes first for accurate LLM signals:

```powershell
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/llm_ready.py --once --probe"; \
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/triage_probe.py --interval 1 --probe-every 5 --max-iters 5"
```

Agent Launcher
--------------

One window to run the most common Calyx Agent actions: open the watcher, start/stop triage probe (WSL), probe-once (Windows), open the Agent console, and kick off one-shot runs.

- VS Code task:

```powershell
# Command Palette: Run Task → Agent1: Open Launcher
```

- Direct (Windows PowerShell):

```powershell
python -u .\Scripts\agent_launcher.py
# or use the convenience batch:
.\Scripts\Calyx-Agent-Launcher.bat
```

Options:

- Change poll interval (ms):

```powershell
python -u .\Scripts\agent_watcher.py --interval 250
```

- Hide the event log area:

```powershell
python -u .\Scripts\agent_watcher.py --quiet
```

Role icons (customize)

Each agent row can show a role-aligned emoji/icon. Defaults are baked in (e.g., agent1 🤖, triage 🧪, navigator 🧭). To override, create `outgoing/watcher_icons.json` with a simple mapping:

```json
{
	"agent1": "🤖",
	"triage": "🧪",
	"navigator": "🧭",
	"scheduler": "⏱️",
	"manifest": "📦",
	"sysint": "🛠️",
	"watcher_toke": "👁️"
}
```

The watcher reloads this file periodically; you can update it while the GUI is open.

Legend (icon/color mappings)

- In the Watcher window, click the “❓ Legend” button in the control strip to view the current role → icon → color mapping.
- This reflects live values, including any overrides from `outgoing/watcher_icons.json` and `outgoing/watcher_colors.json` (hot‑reloaded).

Drift badge (telemetry)

When `outgoing/telemetry/state.json` exists, the Watcher shows a small drift badge in the control strip:

- Gray: drift < 2s (normal)
- Amber: ≥ 2s (warn)
- Red: ≥ 5s (critical)

The badge is informational and does not affect control.

- Auto-discover more agents and scroll:

```powershell
python -u .\Scripts\agent_watcher.py               # auto-discovers *.lock under outgoing/
python -u .\Scripts\agent_watcher.py --page-size 10 # paginate rows (Prev/Next controls)
python -u .\Scripts\agent_watcher.py --hide-idle    # hide idle rows (agent1/triage always shown)
python -u .\Scripts\agent_watcher.py --stale-sec 90 # mark running rows 'stale' after 90s inactivity
```

Traffic Navigator (resource routing)

Lightweight monitor that emits `outgoing/navigator.lock` so the watcher shows a "navigator" row.

- Confirms routes between Agent1 and Triage, detects staleness/contention, and warns on low disk/CPU/RAM.
- Read-only: it reports but does not control processes.

Run (WSL, continuous):

```bash
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/traffic_navigator.py --interval 3"
```

Run (Windows, short test):

```powershell
python -u .\tools\traffic_navigator.py --interval 1 --max-iters 5
```

Control mode (optional)

Enable the navigator to actively shape traffic (pausing triage briefly on contention and adjusting probe cadence based on resource heat). Controls are written to `outgoing/navigator_control.lock` and consumed live by `tools/triage_probe.py`.

- Start (WSL, continuous):

```bash
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/traffic_navigator.py --interval 3 --control --pause-sec 90 --hot-interval 120 --cool-interval 30"
```

- Start (Windows, short test):

```powershell
python -u .\tools\traffic_navigator.py --interval 0.5 --control --max-iters 5
```

Artifacts:

- `outgoing/navigator_control.lock` — current control directives:
	- `pause_until` (epoch seconds) to temporarily pause triage probes
	- `probe_interval_sec` override for probe cadence
- `outgoing/navigator_filters.json` — learned filters and policy hints (for audit and future tuning)

Notes:

- The Watcher must be unlocked for UI-side commands (banner/logs) to show, but control locks take effect regardless of the Watcher.
- `tools/triage_probe.py` now respects `pause_until` and `probe_interval_sec` at runtime and annotates its heartbeat with the applied control state.

Systems Integrator (upgrade suggestions)
---------------------------------------

Continuously audits non-agent data (deps/logs/config/docs) and surfaces actionable, safe local upgrades and change requests. When suggestions exist, the watcher will show a warning lamp for the `sysint` row and enable a quick “Open” to review the most relevant file (e.g., `requirements.txt`).

Run (WSL, continuous):

```bash
wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/sys_integrator.py --interval 10"
```

Run (Windows, short test):

```powershell
python -u .\tools\sys_integrator.py --interval 1 --max-iters 5
```

Artifacts:

- `outgoing/sysint.lock` — status_message, upgrade_ready, suggestions[], open_path

Notes:

- No network calls are used; all checks are local and conservative.
- Typical suggestions: install optional packages (psutil, metaphone), rotate large logs, add wake-word samples for evaluation, enable navigator control mode.

Control channel (first test)

The watcher exposes a local, user-gated control channel. When the watcher starts, it writes `outgoing/watcher_token.lock` and shows a "Control: Locked" button. Tokens are regenerated when you re-lock control; unlock before sending commands.

- To allow Agent1 control, click the lock button to switch to "Control: Unlocked".
- Send a test command from PowerShell (in the same repo):

```powershell
python -u .\tools\test_watcher_control.py
```

You should see the banner update and a toast. All commands are file-based and require the token from `watcher_token.lock`. Safe commands implemented:

- set_banner(text, color?)
- append_log(text)
- show_toast(text)
- open_path(path under repo only)

Agent1 console (interactive prompts)

Talk to the local Agent1 running under WSL. Each prompt creates an `outgoing/agent_run_*/` bundle with plan, diffs, and audit. A small heartbeat file is written to `outgoing/agent1.lock` so the watcher GUI can reflect status.

Interactive mode:

```powershell
python -u .\Scripts\agent_console.py
```

One-shot goal:

```powershell
python -u .\Scripts\agent_console.py --goal "Add a Try it section to README with the listener command"
```

Useful flags:

- Apply proposed changes (whitelisted files only):

```powershell
python -u .\Scripts\agent_console.py --goal "..." --apply
```

- Limit plan steps (default 3):

```powershell
python -u .\Scripts\agent_console.py --goal "..." --steps 1
```

- Skip compile/tests after each run:

```powershell
python -u .\Scripts\agent_console.py --goal "..." --no-tests
```

Notes
- The console invokes WSL and activates `~/.calyx-venv` automatically (same wiring as `tools/triage_orchestrator.py`).
- To see live status while a goal is running, keep the Agent watcher open.
- Artifacts from the most recent run are printed at the end and can be opened from the watcher UI.

Notes
- PTT: Hold Space to talk. Press `T` to toggle armed mode if you flip `USE_PTT_HOLD=False` in the script.
- Wake: Say "Aurora" or "Calyx" to arm for ~8 seconds; release speech with a brief pause.
- Voice command: Saying "Activate Calyx Terminal" (via PTT or wake listener) triggers `begin_session`, opens Codex, and logs a session note under `Codex/Journal/Sessions`.


Light task scheduler (every 3 minutes)
-------------------------------------

For continuous, low-cost progression, a lightweight scheduler triggers Agent1 with a tiny micro-task:

- Start background loop (WSL): VS Code task “Agent1: Light Task Loop (3 min)”
- One-shot validation (dry-run): VS Code task “Agent1: Light Task Once (dry-run)”

Or run directly:

```powershell
python -u .\tools\agent_scheduler.py --interval 180
```

Flags:

- `--interval SECS` (default 180)
- `--goal "..."` custom micro-goal
- `--agent-args "..."` extra args for `tools/agent_runner.py` (defaults to `--skip-patches`)
- `--run-once` and `--dry-run` for testing

The scheduler skips a tick when it detects an active run via `outgoing/agent1.lock`.


Metrics: Tool Efficacy Score (TES)
----------------------------------

Each Agent1 run logs a Tool Efficacy Score to `logs/agent_metrics.csv`. This helps compare conservative vs. more autonomous modes.

Scoring (0..100):

- Stability (50%): full credit when final status is `done` and no failures
- Velocity (30%): favors faster runs (1.0 at ≤90s; 0.0 at ≥900s; linear in-between)
- Footprint (20%): smaller change surface is better (1.0 at ≤1 file; 0.0 at ≥10 files)

CSV columns:

`iso_ts, tes, stability, velocity, footprint, duration_s, status, applied, changed_files, run_tests, autonomy_mode, model_id, run_dir, hint`

Innovation hint:

When runs are stable and reasonably fast, a gentle hint is recorded (e.g., “Consider enabling --run-tests” or “--apply --run-tests”). This invites innovation only after stability is demonstrated.

Report:

- Generate a summary by mode: VS Code task “Agent1: Metrics Report”

or CLI:

```powershell
python -u .\tools\agent_metrics_report.py
```

Adaptive supervisor (Windows-first)
-----------------------------------

If WSL tasks keep exiting early (exit code 1) or you want a resilient local loop,
run the adaptive supervisor from Windows. It keeps the essential probes alive and
switches to WSL automatically when it's ready.

Windows PowerShell:

```powershell
python -u .\tools\svc_supervisor_adaptive.py --interval 60
```

VS Code:

- Task: "Run Adaptive Supervisor (Win)" (runs in background)

It ensures (best-effort):
- SVF Probe → `outgoing/svf.lock`
- Triage Probe → `outgoing/triage.lock`
- Systems Integrator → `outgoing/sysint.lock`
- Traffic Navigator (read-only on Windows) → `outgoing/navigator.lock`

Notes:
- When WSL becomes available with `~/.calyx-venv`, the supervisor switches to starting loops in WSL.
- For full orchestration (scheduler, control-mode navigator, TES), prefer the WSL supervisor
	once your WSL venv is stable: `python -u tools/svc_supervisor.py` (from WSL).

SVF Receipts & Housekeeping
---------------------------

Track Sent/Delivered/Read acknowledgements for SVF messages without creating many files.

- Receipts log (CSV): `logs/svf_receipts.csv` (append-only; centralized)
- Utility:

```powershell
python -m tools.svf_receipts write --message-id "<MID>" --type delivered --agent <YourAgent> --artifact "<path>"
python -m tools.svf_receipts write --message-id "<MID>" --type read --agent <YourAgent> --artifact "<path>"
# optional: force archive rollup
python -m tools.svf_receipts rollup
```

- Auto-archive: when CSV grows (≥5 MiB), it rolls into `logs/receipts_archive/svf_receipts_YYYY-MM.csv.gz`.

Reduce file count over time by archiving older shared logs and reports:

```powershell
python -m tools.log_housekeeper run --keep-days 14
```

Behavior:
- Packs `outgoing/shared_logs/*.md`, `outgoing/overseer_reports/*.md`, and `outgoing/reports/*.md` older than N days into `logs/archive/YYYY-MM/<category>_YYYY-MM.tar.gz`.
- Keeps the last N days (default 14) of files in place.
