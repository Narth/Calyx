"""
Station Calyx Onboarding
========================

First-run onboarding flow for new users.

INVARIANTS:
- NO_HIDDEN_CHANNELS: Explicit scope communication
- HUMAN_PRIMACY: Clear explanation of advisory-only nature

Role: core/onboarding
Scope: First-run user guidance and scope communication
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_config
from .evidence import append_event, create_event

COMPONENT_ROLE = "onboarding"
COMPONENT_SCOPE = "first-run user guidance"


ONBOARDING_CONTENT = '''# Welcome to Station Calyx

Station Calyx is now installed on your system. This document explains what it does, what it does not do, and how to control it.

---

## What Station Calyx Does

Station Calyx is a **local, advisory-only system monitoring tool**. It:

- **Collects system snapshots** - CPU, memory, disk usage, running processes
- **Generates reflections** - Analyzes events to identify patterns and anomalies
- **Produces advisories** - Context-aware observations based on your declared intent
- **Detects trends** - Tracks metric changes over time
- **Stores evidence locally** - All data stays on your machine in `data/evidence.jsonl`

All outputs are informational. Station Calyx presents data for your review.

---

## What Station Calyx Does NOT Do

Station Calyx has explicit constraints that cannot be bypassed:

- ? **Does not execute commands** - Cannot run scripts, programs, or shell commands
- ? **Does not modify files** - Cannot edit, delete, or create system files
- ? **Does not send data externally** - All data remains local (no network calls)
- ? **Does not auto-start** - Only runs when you explicitly start it
- ? **Does not run in background by default** - Foreground operation is the default
- ? **Does not make decisions** - Presents information; you decide what to do

These constraints are enforced in code and cannot be overridden by configuration.

---

## How Data is Handled

**All data is local-only:**

- Evidence log: `station_calyx/data/evidence.jsonl`
- Summaries: `station_calyx/data/summaries/`
- Configuration: `station_calyx/data/intent.json`

**No data leaves your machine.** Station Calyx does not:
- Connect to external servers
- Send telemetry
- Phone home
- Sync to cloud services

---

## How to Control Station Calyx

### Start the service
```bash
python -m station_calyx.ui.cli start
```

### Stop the service
```bash
python -m station_calyx.ui.cli stop
```

### Check service health
```bash
python -m station_calyx.ui.cli doctor
```

### View current status
```bash
python -m station_calyx.ui.cli status --human
```

---

## Quick Commands

| Command | Description |
|---------|-------------|
| `calyx start` | Start the API service |
| `calyx stop` | Stop the API service |
| `calyx status` | Show technical status |
| `calyx status --human` | Show human-readable status |
| `calyx snapshot` | Capture system state |
| `calyx advise` | Generate advisory |
| `calyx doctor` | Check system health |

---

## Safety Summary

| Constraint | Enforced |
|------------|----------|
| Advisory-only output | ? Yes |
| No command execution | ? Yes |
| No file modification | ? Yes |
| Local data only | ? Yes |
| User-controlled lifecycle | ? Yes |

---

## Need Help?

- Run `calyx doctor` to check for issues
- View API docs at http://127.0.0.1:8420/docs (when running)
- Check `data/evidence.jsonl` for event history

---

*Station Calyx: Advisory-only. Does not execute. Does not initiate actions.*

*Generated: {timestamp}*
'''


def get_onboarding_path() -> Path:
    """Get path to onboarding file."""
    config = get_config()
    return config.data_dir / "onboarding.md"


def is_first_run() -> bool:
    """Check if this is the first run."""
    return not get_onboarding_path().exists()


def generate_onboarding() -> str:
    """Generate onboarding content."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return ONBOARDING_CONTENT.format(timestamp=timestamp)


def present_onboarding(force: bool = False) -> Optional[str]:
    """
    Present onboarding to user if first run.
    
    Returns onboarding content if presented, None otherwise.
    """
    onboarding_path = get_onboarding_path()
    
    if not force and onboarding_path.exists():
        return None
    
    # Generate and save onboarding
    content = generate_onboarding()
    onboarding_path.parent.mkdir(parents=True, exist_ok=True)
    onboarding_path.write_text(content, encoding="utf-8")
    
    # Log event
    event = create_event(
        event_type="ONBOARDING_PRESENTED",
        node_role=COMPONENT_ROLE,
        summary="Onboarding document generated for new user",
        payload={
            "path": str(onboarding_path),
            "first_run": not force,
        },
        tags=["onboarding", "lifecycle"],
    )
    append_event(event)
    
    return content


def load_onboarding() -> Optional[str]:
    """Load existing onboarding content."""
    path = get_onboarding_path()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print(f"First run: {is_first_run()}")
