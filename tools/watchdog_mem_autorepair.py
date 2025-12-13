#!/usr/bin/env python3
"""Watchdog: monitor memory headroom and enqueue safe log-rotation intents.

This script is safe by default (dry-run). It will add an intent via
Coordinator.add_intent(...) and call Coordinator.pulse() so the system
creates the usual reports and audits. Because the Coordinator only executes
autonomous intents when autonomy_mode is 'guide' or 'execute', running this
while the system is in 'research' (or other non-exec) mode is non-destructive.

Usage:
    python -u tools/watchdog_mem_autorepair.py [--threshold 0.2] [--force] [--apply]

Flags:
  --threshold FLOAT  Memory free fraction threshold (default: 0.20)
  --force            Enqueue intent regardless of headroom check
  --apply            Mark this run as an apply (writes a small audit); otherwise dry-run

Outputs:
  - outgoing/watchdog/dry_run_report.json
  - outgoing/watchdog/watchdog.log
  - outgoing/bridge/dialog.log (appends operator-facing lines)

"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watchdog: enqueue log-rotation when memory low")
    parser.add_argument("--threshold", type=float, default=0.20, help="memory free fraction threshold (0-1)")
    parser.add_argument("--force", action="store_true", help="enqueue even if headroom ok")
    parser.add_argument("--apply", action="store_true", help="mark as apply (non-dry-run audit flag)")
    parser.add_argument("--cooldown-secs", type=int, default=3600, help="Minimum seconds between enqueues to avoid flapping (default 3600)")
    parser.add_argument("--min-consecutive", type=int, default=1, help="Require this many consecutive low-headroom readings before enqueue (default 1)")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]

    # Ensure workspace root is on sys.path so package imports (calyx.*) resolve
    try:
        sys.path.insert(0, str(root))
    except Exception:
        pass

    # Import coordinator lazily so this file can be imported safely
    try:
        from calyx.cbo.coordinator.coordinator import Coordinator
    except Exception as e:
        print("ERROR: failed to import Coordinator:", e, file=sys.stderr)
        return 2

    co = Coordinator(root)

    # Ensure outgoing dirs
    out_watch = root / "outgoing" / "watchdog"
    out_bridge = root / "outgoing" / "bridge"
    out_watch.mkdir(parents=True, exist_ok=True)
    out_bridge.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat()

    headroom = {}
    try:
        headroom = co.state.get_resource_headroom() or {}
    except Exception as e:
        # If state query fails, still proceed to a safe enqueue when forced
        headroom = {}

    mem_free_frac = None
    if isinstance(headroom, dict):
        # try common keys
        mem_free_frac = headroom.get("mem_free_fraction") or headroom.get("mem_pct_free") or headroom.get("mem_free")
    # normalize
    try:
        if isinstance(mem_free_frac, (int, float)):
            mem_free_frac = float(mem_free_frac)
        else:
            mem_free_frac = None
    except Exception:
        mem_free_frac = None

    # Default: only enqueue when forced or when mem_free_frac is known and below threshold.
    should_enqueue = args.force
    reason = None
    # If headroom is unknown and not forced, avoid enqueuing to reduce spurious actions.
    if not should_enqueue:
        if mem_free_frac is None:
            reason = "unknown_mem_headroom"
            should_enqueue = False
        elif mem_free_frac < args.threshold:
            reason = f"mem_free_frac={mem_free_frac:.3f} < threshold={args.threshold:.3f}"
            should_enqueue = True

    # Implement cooldown and hysteresis to avoid frequent enqueue spikes. We persist state.
    last_enqueue_file = out_watch / "last_enqueue_ts.txt"
    state_file = out_watch / "state.json"
    try:
        now = datetime.now(timezone.utc)
    except Exception:
        # Fallback to a timezone-aware now; avoid deprecated datetime.utcnow()
        now = datetime.now(timezone.utc)

    # Load persisted state (consecutive lows, last_enqueue)
    state = {"consecutive_low": 0, "last_enqueue_iso": None}
    try:
        if state_file.exists():
            import json as _json
            state = _json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        state = {"consecutive_low": 0, "last_enqueue_iso": None}

    # Update consecutive_low based on current reading
    if mem_free_frac is None:
        # unknown reading does not advance low count; leave as-is
        pass
    else:
        if mem_free_frac < args.threshold:
            state["consecutive_low"] = int(state.get("consecutive_low", 0)) + 1
        else:
            state["consecutive_low"] = 0

    # Persist updated consecutive count early so repeated runs see it
    try:
        out_watch.mkdir(parents=True, exist_ok=True)
        state_file.write_text(__import__("json").dumps(state), encoding="utf-8")
    except Exception:
        pass

    # Decide based on consecutive requirement
    if not args.force:
        if state.get("consecutive_low", 0) < int(args.min_consecutive):
            reason = f"insufficient_consecutive_low ({state.get('consecutive_low',0)} < {args.min_consecutive})"
            should_enqueue = False

    # Cooldown check
    if should_enqueue and not args.force:
        try:
            last_iso = state.get("last_enqueue_iso") or (last_enqueue_file.read_text(encoding="utf-8").strip() if last_enqueue_file.exists() else None)
            last_ts = None
            if last_iso:
                try:
                    last_ts = datetime.fromisoformat(last_iso)
                except Exception:
                    last_ts = None
            if last_ts is not None:
                elapsed = (now - last_ts).total_seconds()
                if elapsed < float(args.cooldown_secs):
                    reason = f"cooldown_active; elapsed={int(elapsed)}s < cooldown={args.cooldown_secs}s"
                    should_enqueue = False
        except Exception:
            pass

    intent_id = None
    intent_desc = "Watchdog: rotate logs and prune old logs to reclaim memory/disk headroom"
    if should_enqueue:
        # Use a safe 'suggest' autonomy requirement so it will not execute unless the system is in guide/execute
        intent_id = co.add_intent(
            description=intent_desc,
            origin="watchdog",
            required_capabilities=["log_rotation"],
            desired_outcome="rotate and compact logs to free disk/memory and reduce memory pressure",
            priority_hint=85,
            autonomy_required="guide",
        )

        # Watchdog logfile
        watchdog_log = out_watch / "watchdog.log"
        with watchdog_log.open("a", encoding="utf-8") as wf:
            wf.write(f"{ts} WATCHDOG> enqueued_intent={intent_id} reason={reason or 'forced'} apply={args.apply}\n")

        # Append operator-facing line to outgoing/bridge/dialog.log
        dialog_path = out_bridge / "dialog.log"
        with dialog_path.open("a", encoding="utf-8") as dh:
            line = f"{ts} WATCHDOG> enqueued_intent={intent_id} desc=log_rotation reason={reason or 'forced'} apply={args.apply}"
            dh.write(line + "\n")

    # Always call a pulse to flush reports (dry-run safe if autonomy_mode != guide/execute)
    try:
        report = co.pulse()
    except Exception as e:
        print("ERROR: coordinator.pulse() failed:", e, file=sys.stderr)
        return 3

    # Prepare a dry-run report
    dry_report: Dict[str, Any] = {
        "ts": ts,
        "mem_free_frac": mem_free_frac,
        "threshold": args.threshold,
        "should_enqueue": should_enqueue,
        "intent_id": intent_id,
        "intent_description": intent_desc,
        "autonomy_mode": co.state.get_autonomy_mode(),
        "pulse_report": report,
    }

    dry_path = out_watch / "dry_run_report.json"
    dry_path.write_text(json.dumps(dry_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also write a compact human line
    with (out_watch / "watchdog_latest.txt").open("w", encoding="utf-8") as lf:
        lf.write(f"{ts} enqueued={intent_id} should_enqueue={should_enqueue} mem_free={mem_free_frac}\n")

        # Update last_enqueue timestamp so cooldown can be enforced next run
        try:
            last_enqueue_file.write_text(now.isoformat(), encoding="utf-8")
        except Exception:
            pass
    # Print concise summary for operator
    print("WATCHDOG SUMMARY:")
    print(f"  autonomy_mode: {dry_report['autonomy_mode']}")
    print(f"  mem_free_frac: {mem_free_frac}")
    print(f"  threshold: {args.threshold}")
    print(f"  should_enqueue: {should_enqueue}")
    print(f"  intent_id: {intent_id}")
    print(f"  pulse_report_written: { 'last_pulse_report.json' if (root / 'outgoing' / 'bridge' / 'last_pulse_report.json').exists() else 'missing' }")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
