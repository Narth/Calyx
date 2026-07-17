#!/usr/bin/env python3
"""
CP7 Chronicler — observes health, drift, and agent responsiveness; writes diagnostics.
Reads: runtime/station_health.json, runtime/station_health_history.jsonl, outgoing/*.lock
Writes: outgoing/cp7.lock
Usage: python tools/cp7_chronicler.py [--interval SEC]
See: docs/AGENT_REPOSITORY.md, COMPENDIUM.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from runtime_truth import add_truth_metadata, load_json_if_fresh

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTGOING = REPO_ROOT / "outgoing"
RUNTIME = REPO_ROOT / "runtime"
HISTORY = RUNTIME / "station_health_history.jsonl"


def _read_history_tail(n: int = 12) -> list[dict]:
    """Last n lines of station_health_history.jsonl."""
    if not HISTORY.exists():
        return []
    lines = HISTORY.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    out = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def run_once() -> dict:
    health, _ = load_json_if_fresh(RUNTIME / "station_health.json", "station_health")
    nav, _ = load_json_if_fresh(OUTGOING / "navigator.lock", "navigator")
    triage, _ = load_json_if_fresh(OUTGOING / "triage.lock", "triage")
    samples = _read_history_tail(12)

    # Drift: compare recent cpu_pct to older
    drift = "unknown"
    drift_note = ""
    if len(samples) >= 6:
        recent = samples[-3:]
        older = samples[-6:-3]
        avg_recent = sum(s.get("cpu_pct") or 0 for s in recent) / len(recent)
        avg_older = sum(s.get("cpu_pct") or 0 for s in older) / len(older)
        delta = avg_recent - avg_older
        if abs(delta) < 5:
            drift = "stable"
            drift_note = f"CPU drift <5% over last 6 samples"
        elif delta > 10:
            drift = "rising"
            drift_note = f"CPU rising ~{int(delta)}% (recent vs older)"
        elif delta < -10:
            drift = "falling"
            drift_note = f"CPU falling ~{int(-delta)}% (recent vs older)"
        else:
            drift = "moderate"
            drift_note = f"CPU delta ~{int(delta)}%"

    # Health summary from current
    health_status = (health or {}).get("health") or "unknown"
    entropy_tier = ((health or {}).get("entropy") or {}).get("tier") or "unknown"
    cpu_target = ((health or {}).get("entropy") or {}).get("cpu_target") or "unknown"

    # Responsiveness: triage latency
    latency_ms = (triage or {}).get("latency_ms")
    responsiveness = "good" if (latency_ms is None or latency_ms < 200) else ("moderate" if latency_ms < 500 else "slow")

    diagnostics = {
        "health": health_status,
        "entropy_tier": entropy_tier,
        "cpu_target": cpu_target,
        "drift": drift,
        "drift_note": drift_note,
        "responsiveness": responsiveness,
        "cbo_latency_ms": latency_ms,
        "samples_analyzed": len(samples),
    }

    lock = {
        "tool": "cp7_chronicler",
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "diagnostics": diagnostics,
        "summary": f"health={health_status} entropy={entropy_tier} drift={drift} responsiveness={responsiveness}",
    }
    return add_truth_metadata(lock, "cp7")


def main() -> int:
    ap = argparse.ArgumentParser(description="CP7 Chronicler")
    ap.add_argument("--interval", type=int, default=0, help="Loop interval (0 = run once)")
    args = ap.parse_args()

    OUTGOING.mkdir(parents=True, exist_ok=True)
    lock_path = OUTGOING / "cp7.lock"

    if args.interval <= 0:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        return 0

    while True:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())
