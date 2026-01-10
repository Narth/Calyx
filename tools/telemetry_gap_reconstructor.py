#!/usr/bin/env python3
"""Telemetry Gap Reconstructor

One-shot tool to write a "downtime has a story" event into the unified station
timeline based on telemetry stream freshness.

Usage:
  python -u tools/telemetry_gap_reconstructor.py --once

Notes:
- Conservative: does not modify existing telemetry files.
- Writes to logs/station_timeline.jsonl (configurable via config.yaml telemetry.timeline.path).
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config.yaml"


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _load_cfg(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    return (ROOT / p).resolve() if not p.is_absolute() else p


def _tail_last_jsonl_ts(path: Path, *, max_bytes: int = 64 * 1024) -> Optional[float]:
    if not path.exists():
        return None
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - max_bytes))
            chunk = f.read()
        text = chunk.decode("utf-8", errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in reversed(lines):
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            for key in ("ts", "timestamp", "time", "t"):
                if key in obj:
                    val = obj.get(key)
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        # try iso
                        try:
                            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            return dt.timestamp()
                        except Exception:
                            pass
            # special: uptime_tracker currently uses 'timestamp' local iso
            if isinstance(obj.get("timestamp"), str):
                try:
                    dt = datetime.fromisoformat(obj["timestamp"])  # may be local naive
                    return dt.replace(tzinfo=timezone.utc).timestamp() if dt.tzinfo else dt.timestamp()
                except Exception:
                    pass
        return None
    except Exception:
        return None


def _mtime_ts(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime if path.exists() else None
    except Exception:
        return None


@dataclass
class StreamSpec:
    name: str
    path: Path
    cadence_sec: int
    stale_after_sec: int


def _load_contract(cfg: Dict[str, Any]) -> Dict[str, StreamSpec]:
    contract = ((cfg.get("telemetry") or {}).get("contract") or {}).get("streams") or {}
    specs: Dict[str, StreamSpec] = {}
    for name, raw in contract.items():
        if not isinstance(raw, dict):
            continue
        raw_path = raw.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        try:
            cadence = int(raw.get("cadence_sec", 60))
            stale = int(raw.get("stale_after_sec", max(300, cadence * 5)))
        except Exception:
            cadence = 60
            stale = 300
        specs[name] = StreamSpec(
            name=name,
            path=_resolve_path(raw_path),
            cadence_sec=cadence,
            stale_after_sec=stale,
        )
    return specs


def _infer_gap(now: float, last_ts: Optional[float]) -> Optional[Tuple[float, float]]:
    if last_ts is None:
        return None
    if now <= last_ts:
        return None
    return (float(last_ts), float(now))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Telemetry Gap Reconstructor")
    ap.add_argument("--config", type=str, default=str(DEFAULT_CFG), help="Path to config.yaml")
    ap.add_argument("--once", action="store_true", help="Run once and exit (default)")
    ap.add_argument("--now", type=float, default=None, help="Override current epoch time (testing)")
    ap.add_argument("--source", type=str, default="telemetry_gap_reconstructor", help="Timeline source label")
    args = ap.parse_args(argv)

    cfg = _load_cfg(Path(args.config))
    from calyx.timeline import append_event, append_downtime

    now = float(args.now) if args.now is not None else time.time()

    append_event(
        "telemetry_reconstructor_start",
        cfg=cfg,
        ts=now,
        source=args.source,
        message="telemetry gap reconstructor started",
        data={"now_iso": _utc_iso(now)},
    )

    specs = _load_contract(cfg)
    if not specs:
        append_event(
            "telemetry_reconstructor_no_contract",
            cfg=cfg,
            ts=now,
            source=args.source,
            level="warn",
            message="no telemetry.contract.streams configured; nothing to reconstruct",
        )
        return 0

    per_stream: Dict[str, Any] = {}
    gaps: Dict[str, Tuple[float, float]] = {}

    for name, spec in specs.items():
        last_ts = _tail_last_jsonl_ts(spec.path) if spec.path.suffix in (".jsonl", ".json") else None
        mtime = _mtime_ts(spec.path)
        gap = _infer_gap(now, last_ts or mtime)
        if gap:
            gaps[name] = gap

        per_stream[name] = {
            "path": str(spec.path),
            "cadence_sec": spec.cadence_sec,
            "stale_after_sec": spec.stale_after_sec,
            "last_ts": float(last_ts) if last_ts is not None else None,
            "last_iso": _utc_iso(last_ts) if last_ts is not None else None,
            "mtime_ts": float(mtime) if mtime is not None else None,
            "mtime_iso": _utc_iso(mtime) if mtime is not None else None,
            "gap_sec": (now - (last_ts or mtime)) if (last_ts or mtime) else None,
        }

    # Compute a conservative global downtime window as the max gap across streams.
    # We treat "downtime" as the time since the newest last_ts among key streams.
    key_streams = [
        "system_snapshots",
        "enhanced_metrics",
        "bridge_pulse_state",
    ]
    last_candidates: list[float] = []
    for ks in key_streams:
        info = per_stream.get(ks) or {}
        candidate = info.get("last_ts") or info.get("mtime_ts")
        if isinstance(candidate, (int, float)):
            last_candidates.append(float(candidate))

    if last_candidates:
        start = max(last_candidates)
        gap_sec = now - start
        # Only emit downtime story when the gap is meaningful.
        if gap_sec >= 600:
            streams_detail: Dict[str, Any] = {}
            for name, info in per_stream.items():
                if name in key_streams:
                    streams_detail[name] = {
                        "last_iso": info.get("last_iso") or info.get("mtime_iso"),
                        "gap_sec": info.get("gap_sec"),
                        "path": info.get("path"),
                    }
            append_downtime(
                cfg=cfg,
                start_ts=float(start),
                end_ts=float(now),
                reason="telemetry gap detected (startup backfill)",
                streams=streams_detail,
                source=args.source,
            )

    append_event(
        "telemetry_reconstructor_done",
        cfg=cfg,
        ts=now,
        source=args.source,
        message="telemetry gap reconstructor finished",
        data={"streams": per_stream},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
