# OpenClaw Skill Integration (Station Calyx)

This document describes the initial high-priority OpenClaw skill integrations and how they are wrapped by Station Calyx governance.

## High-priority skills (wrapped)
- `sysadmin-toolbox`
- `process-watch`
- `uptime-kuma`
- `pi-admin`
- `unraid`
- `proxmox`
- `skills-audit`
- `skills-search`
- `clawdhub`
- `clawddocs`
- `mcporter`
- `guru-mcp`
- `model-usage`
- `codex-orchestration`

## Governance Rules
- Network and LLM actions require gates: `outgoing/gates/network.ok` and `outgoing/gates/llm.ok`.
- Mutating skills require `outgoing/gates/apply.ok`.
- Station SLEEP mode restricts skill execution to the allowlist in `config/skills.yaml`.
- All skills are opt-in; set `enabled: true` in `config/skills.yaml` or pass `--enable` for one-off runs.

## Usage
List configured skills:

```powershell
py -3 tools/skills_cli.py list
```

Run a skill (example, mocked):

```powershell
py -3 tools/skills_cli.py run sysadmin-toolbox --args "--help" --mock
```

Run a skill (real call):

```powershell
py -3 tools/skills_cli.py run process-watch --args "--interval 5" --enable
```

## Notes
- These wrappers only execute local CLIs present in PATH. Install the skill CLI first (e.g., via ClawdHub CLI or manual installation).
- Wrap any new skill using `tools/skills_cli.py` or extend `config/skills.yaml` and follow the same gating pattern.
