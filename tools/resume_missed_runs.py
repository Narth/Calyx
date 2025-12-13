"""Resume missed/skipped scheduler runs when memory is back under threshold.

Usage:
    python tools/resume_missed_runs.py --min-clear-mins 5 --dry-run

Behavior:
- Scans outgoing/scheduler*.lock files for entries with phase == 'skipped'
- For each skipped entry older than min_clear_mins and if system memory < (soft_limit - hysteresis), attempts to relaunch via agent_scheduler._run_agent
- By default runs in dry-run; set --execute to actually launch.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"


def _system_mem_percent():
    try:
        import psutil
        return float(psutil.virtual_memory().percent)
    except Exception:
        return 100.0


def find_skipped_scheduler_locks(min_age_s: int):
    now = time.time()
    found = []
    for p in OUT.glob("scheduler*.lock"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            phase = data.get("phase")
            ts = data.get("ts") or p.stat().st_mtime
            if phase == "skipped" and (now - float(ts) >= min_age_s):
                found.append((p, data))
        except Exception:
            continue
    return found


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-clear-mins", type=int, default=5, help="Minimum minutes since skip to consider resuming")
    parser.add_argument("--hysteresis", type=float, default=5.0, help="Percent hysteresis below soft limit to require before resuming")
    parser.add_argument("--execute", action="store_true", help="Actually launch resumed runs; otherwise dry-run")
    args = parser.parse_args(argv)

    # Load config soft limit
    cfg = {}
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        cfg = {}
    soft = 70.0
    try:
        rm = cfg.get("resource_management", {}) or {}
        thr = (rm.get("adaptive_thresholds", {}) or {}).get("memory_soft_limit", soft)
        if isinstance(thr, str) and thr.endswith("%"):
            thr = thr.rstrip("%")
        soft = float(thr)
    except Exception:
        soft = 70.0

    min_age = int(args.min_clear_mins) * 60
    skipped = find_skipped_scheduler_locks(min_age)
    if not skipped:
        print("No skipped scheduler locks older than min age found.")
        return

    cur_mem = _system_mem_percent()
    print(f"Current system memory: {cur_mem:.1f}%; soft limit {soft}%; hysteresis {args.hysteresis}%")
    threshold_to_resume = float(soft) - float(args.hysteresis)
    if cur_mem > threshold_to_resume:
        print(f"Memory {cur_mem:.1f}% > resume threshold {threshold_to_resume}%. Will not resume any runs.")
        return

    # Safe to attempt resume
    try:
        import tools.agent_scheduler as sched
    except Exception as exc:
        print(f"Failed to import scheduler module: {exc}")
        return

    for p, data in skipped:
        print(f"Considering resume for lock: {p} (skipped data: {data})")
        if args.execute:
            try:
                rc = sched._run_agent(sched.DEFAULT_GOAL, None, False, 1)
                print(f"Launched resume with rc={rc}")
            except Exception as e:
                print(f"Failed to launch resumed run: {e}")
        else:
            print("Dry-run: would launch agent now (use --execute to actually run)")


if __name__ == "__main__":
    main()
