#!/usr/bin/env python3
"""Telemetry Sentinel

Lightweight freshness monitor that:
- checks expected telemetry streams (from config.yaml telemetry.contract.streams)
- writes a heartbeat lock in outgoing/telemetry_sentinel.lock
- emits timeline events when streams go stale

Usage:
  python -u tools/telemetry_sentinel.py --interval 60
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"
LOCK_PATH = OUTGOING / "telemetry_sentinel.lock"
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


def _file_age_sec(path: Path, now: float) -> Optional[float]:
    try:
        if not path.exists():
            return None
        return now - path.stat().st_mtime
    except Exception:
        return None


def _contract_streams(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    contract = ((cfg.get("telemetry") or {}).get("contract") or {}).get("streams") or {}
    return contract if isinstance(contract, dict) else {}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Telemetry Sentinel")
    ap.add_argument("--config", type=str, default=str(DEFAULT_CFG), help="Path to config.yaml")
    ap.add_argument("--interval", type=float, default=60.0, help="Check interval seconds")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0=forever)")
    ap.add_argument("--stale-mult", type=float, default=1.0, help="Multiply stale_after_sec thresholds")
    args = ap.parse_args(argv)

    cfg = _load_cfg(Path(args.config))
    from calyx.timeline import append_event

    OUTGOING.mkdir(parents=True, exist_ok=True)

    streams = _contract_streams(cfg)
    append_event(
        "telemetry_sentinel_start",
        cfg=cfg,
        source="telemetry_sentinel",
        message="telemetry sentinel started",
        data={"interval": args.interval},
    )

    last_reported: Dict[str, float] = {}
    iters = 0

    while True:
        now = time.time()
        stale: Dict[str, Any] = {}
        for name, spec in streams.items():
            if not isinstance(spec, dict):
                continue
            raw_path = spec.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            path = _resolve_path(raw_path)
            stale_after = float(spec.get("stale_after_sec") or 0)
            stale_after = max(60.0, stale_after) * float(args.stale_mult)

            age = _file_age_sec(path, now)
            if age is None:
                # missing file counts as stale
                stale[name] = {"path": str(path), "missing": True, "stale_after_sec": stale_after}
                continue
            if age > stale_after:
                stale[name] = {
                    "path": str(path),
                    "age_sec": round(age, 2),
                    "stale_after_sec": stale_after,
                }

        hb = {
            "ts": now,
            "iso": _utc_iso(now),
            "pid": int(__import__("os").getpid()),
            "stale": stale,
            "ok": len(stale) == 0,
        }
        try:
            LOCK_PATH.write_text(json.dumps(hb, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        # Emit one timeline event per stale stream, rate-limited (once per 10 minutes per stream)
        for stream_name, info in stale.items():
            last = last_reported.get(stream_name, 0.0)
            if (now - last) >= 600:
                append_event(
                    "telemetry_stream_stale",
                    cfg=cfg,
                    ts=now,
                    source="telemetry_sentinel",
                    level="warn",
                    message=f"stream stale: {stream_name}",
                    data={"stream": stream_name, **info},
                )
                last_reported[stream_name] = now

        iters += 1
        if args.max_iters and iters >= args.max_iters:
            break
        time.sleep(max(1.0, float(args.interval)))

    append_event(
        "telemetry_sentinel_stop",
        cfg=cfg,
        source="telemetry_sentinel",
        message="telemetry sentinel stopped",
        data={"iters": iters},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
