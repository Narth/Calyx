"""
Simple file-based message bus for Calyx agents.

Messages live under outgoing/bus/*.json with a minimal schema:
{
  "producer": "agent1",
  "run_dir": "outgoing/agent_run_1699999999",
  "status": "done",
  "summary": { ... optional ... },
  "ts": 1699999999.0
}

Processed messages are moved to outgoing/bus/processed/.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
BUS = OUT / "bus"
BUS_PROCESSED = BUS / "processed"


def ensure_dirs() -> None:
    try:
        BUS.mkdir(parents=True, exist_ok=True)
        BUS_PROCESSED.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def publish_message(producer: str, run_dir_rel: str, status: str = "done", summary: Optional[Dict[str, Any]] = None) -> Path:
    ensure_dirs()
    ts = time.time()
    # Use a monotonic-ish filename to avoid collisions
    name = f"{int(ts)}_{producer}.json"
    path = BUS / name
    msg = {
        "producer": str(producer),
        "run_dir": str(run_dir_rel),
        "status": str(status),
        "summary": summary or {},
        "ts": ts,
    }
    try:
        path.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return path


def list_messages() -> list[Path]:
    ensure_dirs()
    try:
        return sorted([p for p in BUS.glob("*.json") if p.is_file()], key=lambda p: p.stat().st_mtime)
    except Exception:
        return []


def mark_processed(p: Path) -> None:
    ensure_dirs()
    try:
        dest = BUS_PROCESSED / p.name
        p.replace(dest)
    except Exception:
        try:
            p.unlink(missing_ok=True)  # type: ignore[call-arg]
        except Exception:
            pass
