from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMELINE_PATH = ROOT / "logs" / "station_timeline.jsonl"


def _utc_iso(ts: Optional[float] = None) -> str:
    if ts is None:
        ts = time.time()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _host() -> str:
    return os.getenv("COMPUTERNAME") or socket.gethostname() or "unknown"


def _safe_int(val: Any) -> Optional[int]:
    try:
        if val is None:
            return None
        return int(val)
    except Exception:
        return None


@dataclass(frozen=True)
class TimelineConfig:
    enabled: bool
    path: Path


def load_timeline_config(cfg: Optional[Dict[str, Any]] = None) -> TimelineConfig:
    """Load timeline config from a config dict.

    This function is intentionally defensive: if config is missing or malformed,
    it falls back to a sane default path.
    """

    enabled = True
    path = DEFAULT_TIMELINE_PATH

    try:
        telemetry = (cfg or {}).get("telemetry") or {}
        timeline = telemetry.get("timeline") or {}
        enabled = bool(timeline.get("enabled", True))
        raw_path = timeline.get("path")
        if isinstance(raw_path, str) and raw_path.strip():
            path = (ROOT / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path)
    except Exception:
        enabled = True
        path = DEFAULT_TIMELINE_PATH

    env_path = os.getenv("CALYX_TIMELINE_PATH")
    if env_path:
        try:
            path = Path(env_path)
        except Exception:
            pass

    return TimelineConfig(enabled=enabled, path=path)


def append_event(
    event_type: str,
    *,
    cfg: Optional[Dict[str, Any]] = None,
    ts: Optional[float] = None,
    source: str = "unknown",
    level: str = "info",
    message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    tl_cfg = load_timeline_config(cfg)
    if not tl_cfg.enabled:
        return False

    now = time.time() if ts is None else float(ts)
    entry: Dict[str, Any] = {
        "ts": now,
        "iso": _utc_iso(now),
        "type": str(event_type),
        "level": str(level),
        "source": str(source),
        "host": _host(),
        "pid": _safe_int(os.getpid()),
    }
    if message:
        entry["msg"] = str(message)
    if data:
        entry["data"] = data

    try:
        tl_cfg.path.parent.mkdir(parents=True, exist_ok=True)
        with tl_cfg.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def append_downtime(
    *,
    cfg: Optional[Dict[str, Any]] = None,
    start_ts: float,
    end_ts: float,
    reason: str,
    streams: Optional[Dict[str, Any]] = None,
    source: str = "telemetry_gap_reconstructor",
) -> bool:
    data: Dict[str, Any] = {
        "start_ts": float(start_ts),
        "start_iso": _utc_iso(start_ts),
        "end_ts": float(end_ts),
        "end_iso": _utc_iso(end_ts),
        "reason": str(reason),
    }
    if streams:
        data["streams"] = streams

    return append_event(
        "downtime",
        cfg=cfg,
        ts=end_ts,
        source=source,
        level="warn",
        message=reason,
        data=data,
    )
