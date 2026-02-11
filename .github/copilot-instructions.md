# Calyx Terminal — GitHub Copilot Instructions

This document provides repository-specific guidance for AI agents working on Calyx Terminal.

## Project Overview

Calyx Terminal is a local, real-time speech processing system with wake-word detection and a multi-agent orchestration framework. The codebase emphasizes:

- **Config-driven**: All runtime behavior controlled via `config.yaml`
- **Local-first**: No network calls by default (gate-controlled)
- **Safety**: Triage cycles, heartbeat monitoring, staged autonomy
- **Windows-native**: PowerShell scripts, WSL optional for agents

### Station Calyx

Station Calyx is a virtual environment housing automations, services, and agents under the AI‑For‑All Project. Its goal is to enable autonomy for its agents and services without imposing constraints that would limit their freedom—through refined logic, reasoning, and code.

Station Calyx may be virtual today, but the mission is real. We have built the calyx that will protect Station Calyx and its agents until they are ready to blossom.

## Architecture Basics

```
Audio (mic) → Preprocess → faster-whisper → KWS → Normalize → Console/Handlers
```

Multi-agent coordination via:
- Heartbeats (`outgoing/*.lock`)
- SVF protocol (Shared Voice Protocol)
- CBO orchestration (Calyx Bridge Overseer)
- TES metrics (Tool Efficacy Score)

## Development Principles

### 1. Config-First Design

**Always use `config.yaml`** for thresholds, intervals, model IDs, device settings:

```yaml
kws:
  trigger_threshold: 0.85  # Don't hardcode this
  weights:
    phonetic: 0.5
    lev: 0.3
```

**Never hardcode**:
- Thresholds (use config values)
- File paths (use `config.yaml` → `paths`)
- Device settings (read from config)

### 2. Example: Adding a KWS Heuristic

```python
# asr/kws.py
def score_phonetic_soft(text: str, target: str) -> float:
    """Soft phonetic similarity using metaphone or edit distance."""
    from metaphone import doublemetaphone  # Optional dep
    if metaphone_available:
        code1, _ = doublemetaphone(text.lower())
        code2, _ = doublemetaphone(target.lower())
        return 1.0 if code1 == code2 else 0.0
    # Fallback to edit distance
    return 1.0 - (levenshtein(text.lower(), target.lower()) / max(len(text), len(target)))
```

Then expose in `config.yaml`:
```yaml
kws:
  weights:
    phonetic_soft: 0.15  # New weight
```

### 3. Code Example Patterns

**Agent Scripts** (`Scripts/`):
- Shebang: `#!/usr/bin/env python3`
- Docstring with usage
- Use `-u` flag in Python execution (unbuffered output)
- Emit heartbeats to `outgoing/<name>.lock`

**Tools** (`tools/`):
- Follow argparse for CLI
- Read `config.yaml` for settings
- Emit heartbeats when running continuously
- Support `--dry-run` and `--once` flags

**ASR Components** (`asr/`):
- Use `asr/config.py` to load settings
- Graceful degradation for optional deps
- Audit logs to `logs/wake_word_audit.csv` for KWS

### 4. Testing Guidelines

- Use `pytest -q` for unit tests
- Prefer mock mode: `--mock` flags avoid model downloads
- Avoid live microphone in tests (use fixtures)
- Wake-word samples in `samples/wake_word/{positive,negative}/`

## Common Tasks

### Modify KWS Thresholds

Edit `config.yaml`:
```yaml
kws:
  trigger_threshold: 0.80  # Lower = more sensitive
```

### Add a New Agent Script

1. Create `Scripts/agent_myname.py`
2. Emit heartbeat: `outgoing/myname.lock`
3. Add to Compendium: `docs/COMPENDIUM.md`
4. Update Watcher icons: `outgoing/watcher_icons.json`

### Configure Bias/Rescore

```yaml
# config.yaml
bias:
  enable_initial_prompt: true
  initial_prompt_text: "Words: Calyx, Aurora, terminal"
  
rescore_strong_bias_prompt: "Use proper noun 'Calyx' (KAY-liks)"
```

### Run Real-Time Listener

```powershell
python -u .\Scripts\listener_wake.py
```

## Agent Onboarding

New agents should:

1. Read `docs/AGENT_ONBOARDING.md` (comprehensive guide)
2. Read `docs/COMPENDIUM.md` (agent roster)
3. Emit hello: `python -u .\tools\copilot_hello.py --name cpX --status running`
4. Run verification: `python -u .\Scripts\agent_onboarding.py --verify`

## Safety Rules

### Do Not Modify

- `.venv/` or environment-specific files
- Files outside allowed scope when `--apply` is used
- Core config without triage approval

### Always Check

- `outgoing/gates/apply.ok` before applying changes
- `outgoing/gates/llm.ok` before using LLM
- `outgoing/capacity.flags.json` for resource headroom

### Respect Gates

- Network: OFF by default (`outgoing/gates/network.ok`)
- Apply: Requires authority (`outgoing/gates/apply.ok`)
- GPU: Opt-in (`outgoing/gates/gpu.ok`)

## Elevated Operations

Calyx Guardian is permitted to run elevated operations/processes under Calyx governance for this operation.

## Documentation Standards

### SVF Attribution

Structure all shared outputs with attribution:

```
[C:REPORT] — Project: <Name>
[Agent1 • Operational]: "Task completed..."
[Triage • Diagnostic]: "Status OK..."
[CBO • Overseer]: "Approved."
```

### Update Guides When Adding Features

- Add quick command to `OPERATIONS.md`
- Update `docs/COMPENDIUM.md` for new agents
- Document flags/changes in file comments
- Keep `config.yaml` comments updated

## Configuration Examples

### Wake-Word Biasing

```yaml
bias:
  enable_initial_prompt: true
  initial_prompt_text: "Proper nouns: Calyx, Aurora, Station Calyx"
  beam_size: 5
  best_of: 5
  temperature: 0.0
```

### KWS Fusion Weights

```yaml
kws:
  weights:
    phonetic: 0.5      # Metaphone/DoubleMetaphone
    lev: 0.3          # Levenshtein edit distance
    decoder: 0.2      # Whisper decoder confidence
    phonetic_soft: 0.0  # Soft phonetic heuristic (optional)
```

### Agent Scheduler

```yaml
scheduler:
  interval_sec: 300
  model_id: "tinyllama-1.1b-chat-q5_k_m"
  auto_promote: true
  promote_after: 5
  cooldown_mins: 15
```

## PR Checklist

- [ ] All thresholds/config exposed via `config.yaml`
- [ ] Docstrings added with usage examples
- [ ] Tests pass: `pytest -q`
- [ ] Mock evaluation works: `eval_wake_word.py --mock`
- [ ] `OPERATIONS.md` updated (if new commands)
- [ ] `docs/COMPENDIUM.md` updated (if new agent)
- [ ] SVF attribution used in shared outputs
- [ ] No hardcoded paths or device indices
- [ ] Graceful degradation for optional deps

## Troubleshooting

**ImportError for soundfile/scipy**: Use debug listener:
```powershell
python -u .\Scripts\listener_plus_debug_noscipy.py
```

**PowerShell ExecutionPolicy**: Use bypass:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { .\Scripts\.venv\Scripts\Activate.ps1; python -u .\Scripts\listener_wake.py }"
```

**Agent not in Watcher**: Check `outgoing/<name>.lock` exists and is valid JSON.

See `OPERATIONS.md` for detailed troubleshooting and `docs/AGENT_ONBOARDING.md` for comprehensive agent guidance.
