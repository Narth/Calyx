#!/usr/bin/env python3
"""
Compute lightweight telemetry for Calyx Terminal agents.

- Scans outgoing/*.lock for per-agent ts/status.
- Computes drift between agent1 and scheduler (if both present).
- Maintains a rolling window of recent drift samples.
- Writes summary to outgoing/telemetry/state.json.

Usage (one-shot):
    python -u tools/compute_telemetry.py

Optional loop:
    python -u tools/compute_telemetry.py --interval 5
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outgoing")
TEL_DIR = os.path.join(OUT, "telemetry")
STATE = os.path.join(TEL_DIR, "state.json")


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


essential_keys = ("phase", "status", "ts", "run_dir")


def snapshot_agents() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for p in glob.glob(os.path.join(OUT, "*.lock")):
        name = os.path.splitext(os.path.basename(p))[0]
        data = _read_json(p) or {}
        if not data:
            continue
        out[name] = {k: data.get(k) for k in essential_keys}
    return out


def compute_drift(a_ts: Optional[float], b_ts: Optional[float]) -> Optional[float]:
    if a_ts is None or b_ts is None:
        return None
    try:
        return abs(float(a_ts) - float(b_ts))
    except Exception:
        return None


def update_state(now: float, agents: Dict[str, Dict[str, Any]], window: int = 20) -> Dict[str, Any]:
    prev = _read_json(STATE) or {}
    drift_key = "agent1_scheduler"
    latest = compute_drift(agents.get("agent1", {}).get("ts"), agents.get("scheduler", {}).get("ts"))
    drift_hist: List[Dict[str, Any]] = prev.get("drift_hist", {}).get(drift_key, []) if isinstance(prev.get("drift_hist"), dict) else []
    if latest is not None:
        drift_hist.append({"ts": now, "value": float(latest)})
        drift_hist = drift_hist[-max(1, int(window)) :]
    avg = sum(x["value"] for x in drift_hist) / len(drift_hist) if drift_hist else None
    # Status ratios across agents
    status_counts: Dict[str, int] = {"running": 0, "done": 0, "error": 0, "other": 0}
    for v in agents.values():
        st = str(v.get("status") or "").lower()
        if st in status_counts:
            status_counts[st] += 1
        else:
            status_counts["other"] += 1

    state = {
        "ts": now,
        "agents": agents,
        "active_count": len([1 for v in agents.values() if v.get("status") in ("running", "done", "error") and v.get("ts")]),
        "drift": {drift_key: {"latest": latest, "avg": avg, "samples": len(drift_hist)}},
        "drift_hist": {drift_key: drift_hist},
        "status_counts": status_counts,
    }
    _write_json(STATE, state)
    return state


def run_once() -> Dict[str, Any]:
    now = time.time()
    agents = snapshot_agents()
    return update_state(now, agents)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Compute telemetry for Calyx Terminal")
    ap.add_argument("--interval", type=float, default=0.0, help="If > 0, run in a loop with this interval in seconds")
    args = ap.parse_args(argv)
    if args.interval and args.interval > 0:
        while True:
            st = run_once()
            print("Telemetry:", {"active": st.get("active_count"), "drift": st.get("drift")})
            time.sleep(args.interval)
    else:
        st = run_once()
        print("Telemetry written:", STATE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
