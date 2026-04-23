#!/usr/bin/env python3
"""
CP6 Sociologist — harmony assessor; computes cohesion signals from locks and health.
Reads: outgoing/navigator.lock, outgoing/triage.lock, runtime/station_health.json
Writes: outgoing/cp6.lock
Usage: python tools/cp6_sociologist.py [--interval SEC]
See: docs/AGENT_REPOSITORY.md, docs/CP6.md, COMPENDIUM.md
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


def run_once() -> dict:
    nav, _ = load_json_if_fresh(OUTGOING / "navigator.lock", "navigator")
    triage, _ = load_json_if_fresh(OUTGOING / "triage.lock", "triage")
    health, _ = load_json_if_fresh(RUNTIME / "station_health.json", "station_health")

    entropy_tier = (health or {}).get("entropy") or {}
    tier = (entropy_tier.get("tier") or (nav or {}).get("entropy_tier") or "unknown").lower()
    cpu_target = (entropy_tier.get("cpu_target") or (nav or {}).get("cpu_target") or "unknown").lower()
    interval_status = (nav or {}).get("interval_status") or "unknown"
    triage_status = (triage or {}).get("status") or "unknown"

    rhythm = 70 if tier == "pass" else (40 if tier == "high" else 10)
    stability = 80 if cpu_target == "safe_travels" else (60 if cpu_target == "under" else (30 if cpu_target == "over" else 50))
    load_balance = 80 if interval_status == "hot" else (50 if interval_status == "cool" else 20)
    staleness = 90 if triage_status == "pass" else (50 if triage_status == "warn" else 20)

    harmony = int(0.35 * rhythm + 0.40 * stability + 0.15 * load_balance + 0.10 * staleness)
    harmony = min(100, max(0, harmony))
    status = "harmonious" if harmony >= 70 else ("moderate" if harmony >= 45 else "discordant")

    payload = {
        "tool": "cp6_sociologist",
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "harmony": {"score": harmony, "status": status},
        "components": {"rhythm": rhythm, "stability": stability, "load_balance": load_balance, "staleness": staleness},
        "signals": {"entropy_tier": tier, "cpu_target": cpu_target, "interval_status": interval_status, "triage_status": triage_status},
    }
    return add_truth_metadata(payload, "cp6")


def main() -> int:
    ap = argparse.ArgumentParser(description="CP6 Sociologist")
    ap.add_argument("--interval", type=int, default=0, help="Loop interval (0 = run once)")
    ap.add_argument("--max-iters", type=int, default=0, help="Max iterations (0 = infinite)")
    args = ap.parse_args()

    OUTGOING.mkdir(parents=True, exist_ok=True)
    lock_path = OUTGOING / "cp6.lock"

    if args.interval <= 0:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        return 0

    iters = 0
    while True:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        iters += 1
        if args.max_iters > 0 and iters >= args.max_iters:
            break
        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())
