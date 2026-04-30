# IDE Toolbox — Cursor & VS Code

Canonical IDE config for Station Calyx. Shared by Cursor and VS Code (Cursor is VS Code–based).

## Install

Copy configs to `.vscode/` (works for both IDEs):

```powershell
# From repo root
$src = "ide_toolbox"
$dst = ".vscode"
if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
Copy-Item "$src\tasks.json" "$dst\" -Force
Copy-Item "$src\launch.json" "$dst\" -Force
Copy-Item "$src\settings.json" "$dst\" -Force
Copy-Item "$src\extensions.json" "$dst\" -Force
Write-Host "IDE toolbox installed to .vscode/"
```

Or run the install script:

```powershell
.\ide_toolbox\install.ps1
```

## Contents

| File | Purpose |
|------|---------|
| `tasks.json` | Sunrise, Sunset, Navigator, Triage, health checks, smoke test |
| `launch.json` | CBO Core, Dev Harness, Discord Gateway, Telemetry Gateway, Avatar Web |
| `settings.json` | Python venv (.venv_cbohub311), file exclusions |
| `extensions.json` | Recommended extensions (Python, debugpy) |

## Tasks

- **Sunrise Station Calyx** — Full boot (core services, health loop, Discord Gateway)
- **Sunset Station Calyx** — Graceful shutdown
- **Check Calyx Core Services** — TCP probe (7777, 7778, 7780, 7781)
- **Update State Checks** — Refresh STATE.md from station_health.json
- **Navigator** — Cadence control (hot/cool/pause)
- **Triage Orchestrator** — Health probe, latency check
- **Station Health Check** — One-shot CPU/RAM/process check
- **Energy Churn Analyzer** — Trend analysis from station_health_history.jsonl
- **Smoke Test** — Lane 0 deployment validation

## Launch Configs

- **CBO Core** — 7778
- **Dev Harness** — 7777
- **Discord Gateway** — Discord → CBO relay
- **Telemetry Gateway** — 7781 (0.0.0.0)
- **Avatar Web** — 7780

## Note

`.vscode/` and `.cursor/` are gitignored. This toolbox is the canonical source; install copies to your local IDE config.
