# Calyx Bridge Overseer (CBO)

Purpose: turn Station Calyx on with minimal human input and keep it productive. CBO sets guardrails, boots core loops, handles agent onboarding, and writes a heartbeat with basic system telemetry.

What CBO manages (conservative set):
- **Agent Onboarding** (new): Automated agent registration, validation, and integration
- Adaptive Supervisor (Windows-first, WSL when ready) to ensure:
  - svf_probe (shared voice heartbeat)
  - triage_probe (triage heartbeat and periodic probe)
  - sys_integrator (systems checks)
  - traffic_navigator (contention-aware cadence; control mode only when safe)
  - agent_scheduler (optional, opt-in)
- metrics_cron (every 15 min by default)
- log housekeeping (archive older *.md reports)
- gates: defaults to Network=OFF, Local LLM=ON

Artifacts:
- Heartbeat: `outgoing/cbo.lock` (JSON snapshot)
- Gates: `outgoing/gates/{network.ok,llm.ok}`
 - Authority gate: `outgoing/gates/cbo.ok` (enables control decisions)
 - Policy: `outgoing/policies/cbo_permissions.json` (allowed actions and constraints)

Quick start (Windows PowerShell):

```powershell
# Status only
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status

# Start overseer loop (safe defaults)
powershell -File .\Scripts\Calyx-Overseer.ps1

# Include agent scheduler
powershell -File .\Scripts\Calyx-Overseer.ps1 -EnableScheduler

# Allow navigator control mode on Windows (advanced)
powershell -File .\Scripts\Calyx-Overseer.ps1 -NavigatorControlOnWindows
```

Scheduled at logon (optional):

```powershell
$py = (Resolve-Path '.\\.venv\\Scripts\\python.exe').Path
$action = New-ScheduledTaskAction -Execute $py -Argument '-u tools\\cbo_overseer.py'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Calyx CBO Overseer' -Action $action -Trigger $trigger -Settings $settings -Description 'Boot Calyx overseer at user logon'
```

Notes:
- Network remains OFF unless explicitly enabled (see `tools/net_gate.py`).
- If WSL is missing or its venv is not ready, CBO runs everything on Windows and will transparently switch to WSL once ready.
- All operations are best‑effort; failures are logged minimally and retried on the next loop.
- When policy grants full access, CBO enables the Agent Scheduler and starts it with auto-promotion; the scheduler enforces hardened thresholds tied to GPU/LLM readiness.

Authority and permissions
------------------------

- Grant authority to CBO (creates `gates/cbo.ok` and a default policy):

```powershell
powershell -File .\Scripts\Grant-CBOAuthority.ps1
```

- Run overseer without authority (monitor-only):

```powershell
python -u tools\cbo_overseer.py --no-authority --status
```

GPU telemetry (opt-in by readiness)
-----------------------------------

When `outgoing/llm_ready.lock` exists, the CBO heartbeat includes a `metrics.gpu` section based on available backends:

- `nvidia-smi` (preferred, no Python deps): memory, utilization, temperature.
- `torch.cuda` (fallback when installed): basic memory info.

This keeps GPU probing lightweight and only active when the system is ready for local LLM work.

GPU gate and acceleration
-------------------------

- Enable GPU for CBO-managed processes (safe opt-in):

```powershell
python -u .\tools\gpu_gate.py --enable
```

- Disable later:

```powershell
python -u .\tools\gpu_gate.py --disable
```

When the GPU gate is enabled and a GPU is detected, the adaptive supervisor propagates:

- CBO_GPU_ALLOWED=1
- FASTER_WHISPER_DEVICE=cuda
- FASTER_WHISPER_COMPUTE_TYPE=float16

to supervised processes (Windows and WSL). Tools that use faster-whisper or PyTorch can respect these hints to use the GPU.

Optimizer and teaching cycles
-----------------------------

The optional CBO Optimizer tunes supervisor intervals at runtime and can schedule lightweight teaching/self‑discipline cycles (CP6 Sociologist → CP7 Chronicler) when the system is cool:

- Starts/stops via Overseer flags

```powershell
# Enable optimizer with teaching cycles
python -u tools\cbo_overseer.py --enable-optimizer --optimizer-interval 120 --enable-teaching --teach-interval-mins 30

# Status only (shows optimizer plan in dry-run)
python -u tools\cbo_overseer.py --dry-run --enable-optimizer --enable-teaching
```

What it does:
- Reads `outgoing/cbo.lock` and recent `logs/agent_metrics.csv` (TES) to infer load and momentum.
- Writes `outgoing/tuning/supervisor_overrides.json` with conservative bounds:
  - `navigator.interval`, `navigator.hot_interval`, `navigator.cool_interval`, `navigator.pause_sec`
  - `scheduler.interval`, `scheduler.include`
- Supervisor picks up changes and restarts affected loops to apply the new settings.
- When allowed and safe (LLM ready, system cool), it spawns short CP6/CP7 cycles to reinforce reflection and chronology.

Testing teaching cycles:

- Trigger a one-shot test cycle (ignores policy and cool/TES conditions; requires LLM ready; respects max_parallel):

```powershell
python -u tools\cbo_optimizer.py --once --force-teach
```

Notes:
- Teaching cycles require authority and respect readiness gates; they default to disabled unless explicitly enabled or policy grants.
- Overrides are bounded and policy‑aware; on Windows, navigator control remains gated by policy.

Policy control for teaching cycles
----------------------------------

The CBO policy can centrally enable/disable and shape teaching cycles, preparing for future multi‑agent training:

`outgoing/policies/cbo_permissions.json` (excerpt)

```json
{
  "features": {
    "teaching_cycles": {
      "enabled": true,
      "max_parallel": 1,
      "interval_minutes_default": 30,
      "allowed_agents": []
    }
  }
}
```

- enabled: master switch for CP6/CP7 cycles initiated by the optimizer/overseer
- max_parallel: cap concurrent cycles (the optimizer enforces a simple lock‑based limit)
- interval_minutes_default: default spacing between cycles when overseer flags don’t override
- allowed_agents: reserved for future multi‑agent targeting and per‑agent control

Capacity flags and headroom
---------------------------

CBO computes a conservative headroom snapshot each heartbeat and writes:
- Inline in `outgoing/cbo.lock` → `capacity`
- Mirror file: `outgoing/capacity.flags.json`

Fields:
- `cpu_ok` (CPU ≤ 50%), `mem_ok` (Mem ≤ 80%), `gpu_ok` (GPU util ≤ 40% or absent)
- `super_cool`: CPU ≤ 35%, Mem ≤ 70%, GPU util ≤ 30% (or no GPU)
- `verified`: `super_cool` and `outgoing/llm_ready.lock` exists
- `score`: simple headroom score in [0,1] (higher means more spare capacity)

These flags are intended for post‑verification inspection and can inform whether to allocate more training cycles or tighten cadences.

Scheduler promotion hardening
-----------------------------

When CBO has authority and policy grants full access, and the GPU gate is enabled, the Agent Scheduler adopts stricter promotion thresholds to keep autonomy increases safe under load:

- Requires GPU present (from CBO heartbeat) and `outgoing/llm_ready.lock` OK.
- Tightened defaults: 7 consecutive OK runs with TES≥90, velocity≥0.65, duration≤240s, and total LLM time≤15s.
- Tunable via `config.yaml` → `settings.scheduler.hardening` (see OPERATIONS.md for keys).

## Agent Onboarding Integration

**New Capability (2025-10-24):** CBO now handles agent onboarding automatically as an immediate extension of its orchestration capabilities.

**How It Works:**
1. New agents emit heartbeat with `status: registering`
2. CBO detects registration and validates prerequisites
3. CBO adds agent to `calyx/core/registry.jsonl`
4. CBO assigns initial onboarding tasks
5. CBO monitors integration health

**For New Agents:**
```powershell
# Register with CBO
python -u .\tools\copilot_hello.py --name <agent_name> --status registering

# Monitor onboarding status
python -c "import json; print(json.load(open('outgoing/cbo.lock'))['onboarding'])"
```

**For Administrators:**
```powershell
# Check onboarding status
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status

# Review registry
Get-Content calyx\core\registry.jsonl | ConvertFrom-Json
```

See `docs/CBO_AGENT_ONBOARDING.md` for comprehensive onboarding documentation.
