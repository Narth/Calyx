"""
Correlation activity log — lightweight append for correlating events with CPU/utilization.
Records when key activities occur. Correlation does not imply causation.
See docs/CORRELATION_LOGGING.md.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _log_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    if not (root / "cbo_hub").exists():
        root = Path.cwd()
    return root / "runtime" / "correlation_activity.jsonl"


def log(component: str, event: str, duration_ms: int | None = None) -> None:
    """Append one line to correlation_activity.jsonl. Never raises."""
    if os.environ.get("CALYX_CORRELATION_LOG_DISABLED", "").strip() in ("1", "true", "yes"):
        return
    path = _log_path()
    disable_file = path.parent / "correlation_log.disabled"
    if disable_file.exists():
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        obj: dict[str, Any] = {
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "component": str(component)[:32],
            "event": str(event)[:64],
        }
        if duration_ms is not None:
            obj["duration_ms"] = int(duration_ms)
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
