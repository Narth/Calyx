# OpenClaw Skills Installation Report

Date: 2026-02-01

## Status
All high-priority skills are installed under `C:\Calyx\skills` using the ClawdHub CLI.

### Installed
- sysadmin-toolbox
- process-watch
- uptime-kuma
- pi-admin
- unraid
- proxmox
- skill-audit (configured as `skills-audit` in `config/skills.yaml`)
- skills-search
- clawdhub
- clawddocs
- mcporter
- guru-mcp
- model-usage
- codex-orchestration

### Notes
- ClawdHub required the `undici` package. Installed globally via `npm -g i undici`.
- All installs succeeded; re-runs reported "Already installed".
- If you need to refresh a skill, use `clawdhub install <skill> --force`.

## Validation
- `tests/test_skills_cli_mock.py` passed (mock invocation and list). 
- `tests/test_firecrawl_mock.py` passed (mock Firecrawl wrapper).

## Usage
List skills:
```
py -3 tools/skills_cli.py list
```

Mock run:
```
py -3 tools/skills_cli.py run sysadmin-toolbox --args --help --mock
```

Real run (requires gates + config enabled):
```
py -3 tools/skills_cli.py run process-watch --args --interval 5 --enable
```
