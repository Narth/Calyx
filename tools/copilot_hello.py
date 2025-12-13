#!/usr/bin/env python3
"""
Copilot Hello: emit a watcher-compatible heartbeat for a new or existing Copilot.

Usage (PowerShell):
    python -u tools/copilot_hello.py --name cp7 --status running --message "Greetings, calibrating." --ttl 30

This writes outgoing/<name>.lock with {name, phase, status, ts, status_message}.
If --ttl>0, the script sleeps and refreshes until time is up, then writes a final 'done'.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"

# Optional station identity from config
try:
    from asr.config import load_config  # type: ignore
    _CFG = load_config().raw
    _STATION = _CFG.get("station", {}) if isinstance(_CFG, dict) else {}
    STATION_NAME = _STATION.get("name", "Station Calyx")
    STATION_MOTTO = _STATION.get(
        "motto",
        "Station Calyx is the flag we fly; autonomy is the dream we share.",
    )
except Exception:
    STATION_NAME = "Station Calyx"
    STATION_MOTTO = "Station Calyx is the flag we fly; autonomy is the dream we share."


def _write_hb(name: str, phase: str, status: str, message: Optional[str]) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": name,
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "station": {"name": STATION_NAME, "motto": STATION_MOTTO},
        }
        if message:
            payload["status_message"] = message
        f = OUT / f"{name}.lock"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Emit a watcher heartbeat for a Copilot")
    ap.add_argument("--name", required=True, help="Copilot name (e.g., cp7, planner, scribe)")
    ap.add_argument("--status", default="running", help="Status to report (running|done|warn|error|idle)")
    ap.add_argument("--message", default=None, help="Optional status_message text")
    ap.add_argument("--ttl", type=int, default=0, help="If >0, refresh every 2s for this many seconds, then write 'done'")
    args = ap.parse_args(argv)

    name = str(args.name).strip()
    if not name:
        print("--name is required", flush=True)
        return 2

    ttl = max(0, int(args.ttl))
    status = str(args.status).strip() or "running"
    msg = str(args.message) if args.message is not None else None

    start = time.time()
    _write_hb(name, phase=("probe" if status == "running" else "init"), status=status, message=msg)
    if ttl <= 0:
        return 0
    try:
        while True:
            time.sleep(2)
            now = time.time()
            if now - start >= ttl:
                break
            _write_hb(name, phase="probe", status="running", message=msg)
    except KeyboardInterrupt:
        pass
    # final
    _write_hb(name, phase="done", status="done", message=(msg or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
