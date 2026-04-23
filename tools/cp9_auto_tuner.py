#!/usr/bin/env python3
"""
CP9 Auto-Tuner — proposes tuning from triage/navigator locks and energy churn.
Reads: outgoing/navigator.lock, outgoing/triage.lock, runtime/deployment/energy_churn_report.json
Writes: outgoing/cp9.lock
Usage: python tools/cp9_auto_tuner.py [--interval SEC]
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
DEPLOY = RUNTIME / "deployment"


def run_once() -> dict:
    nav, _ = load_json_if_fresh(OUTGOING / "navigator.lock", "navigator")
    triage, _ = load_json_if_fresh(OUTGOING / "triage.lock", "triage")
    churn = None
    if (DEPLOY / "energy_churn_report.json").exists():
        try:
            churn = json.loads((DEPLOY / "energy_churn_report.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            churn = None

    recommendations: list[str] = []
    tuning: dict = {}

    # Navigator signals
    interval_status = (nav or {}).get("interval_status") or "unknown"
    cadence_70 = (nav or {}).get("cadence_70")
    entropy_tier = (nav or {}).get("entropy_tier") or "unknown"

    if interval_status == "pause":
        recommendations.append("Navigator pause: increase navigator_triage interval or defer heavy work.")
    elif interval_status == "cool":
        recommendations.append("Navigator cool: proceed with caution; avoid bulk runs.")
    if cadence_70 is not None and cadence_70 > 8:
        recommendations.append(f"Cadence_70={cadence_70}: consider longer cooldown between heavy runs.")
    if entropy_tier in ("unacceptable", "high"):
        recommendations.append(f"Entropy {entropy_tier}: reduce concurrent load or throttle ingestion.")

    # Triage signals
    triage_status = (triage or {}).get("status") or "unknown"
    latency_ms = (triage or {}).get("latency_ms")
    triage_recs = (triage or {}).get("recommendations") or []

    if triage_status == "fail":
        recommendations.append("Triage fail: resolve health before adding load.")
    elif triage_status == "warn":
        recommendations.append("Triage warn: proceed with caution.")
    if latency_ms is not None and latency_ms > 500:
        recommendations.append(f"CBO latency {latency_ms}ms: consider reducing request rate.")
    for r in triage_recs:
        if r and r not in recommendations:
            recommendations.append(r)

    # Energy churn signals
    if churn:
        metrics = churn.get("metrics") or {}
        cooldown_needed = metrics.get("cooldown_needed")
        patterns = churn.get("patterns") or []
        if cooldown_needed:
            recommendations.append("Energy churn: cooldown needed; defer heavy work.")
        for p in patterns:
            msg = (p.get("message") or "").strip()
            if msg and msg not in recommendations:
                recommendations.append(msg)
        tuning["energy_churn"] = {
            "samples_analyzed": churn.get("samples_analyzed", 0),
            "cooldown_needed": cooldown_needed,
            "pattern_count": len(patterns),
        }

    if not recommendations:
        recommendations.append("Station tuned; no adjustments recommended.")

    lock = {
        "tool": "cp9_auto_tuner",
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interval_status": interval_status,
        "triage_status": triage_status,
        "recommendations": recommendations,
        "tuning": tuning,
    }
    return add_truth_metadata(lock, "cp9")


def main() -> int:
    ap = argparse.ArgumentParser(description="CP9 Auto-Tuner")
    ap.add_argument("--interval", type=int, default=0, help="Loop interval (0 = run once)")
    args = ap.parse_args()

    OUTGOING.mkdir(parents=True, exist_ok=True)
    lock_path = OUTGOING / "cp9.lock"

    if args.interval <= 0:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        return 0

    while True:
        lock = run_once()
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
