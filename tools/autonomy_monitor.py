#!/usr/bin/env python3
"""Autonomy Monitor

Runs coordinator pulses (or other autonomy entrypoints) and detects any runtime
errors/traces. Logs errors to `outgoing/autonomy_errors.log` and writes a
heartbeat to `outgoing/autonomy_monitor.lock` so operators can be alerted the
moment an error occurs.

Usage:
  python tools/autonomy_monitor.py --once
  python tools/autonomy_monitor.py --interval 30
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "autonomy_monitor.lock"
ERRLOG = OUT / "autonomy_errors.log"


def _write_lock(status: str, extra: Dict[str, Any] | None = None) -> None:
    payload = {
        "name": "autonomy_monitor",
        "pid": os.getpid(),
        "ts": time.time(),
    "iso": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    if extra:
        payload.update(extra)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _append_error(entry: Dict[str, Any]) -> None:
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        with ERRLOG.open("a", encoding="utf-8") as fh:
            ts = datetime.now(timezone.utc).isoformat()
            fh.write(f"[{ts}] ")
            fh.write(json.dumps(entry, ensure_ascii=False))
            fh.write("\n")
    except Exception:
        pass


def _create_alert(entry: Dict[str, Any]) -> None:
    """Create an alert JSON in outgoing/alerts and update latest_alert.json

    The alert is machine-readable and small so external overseers (CBO) can
    quickly inspect and decide whether to retain artifacts for auditing.
    """
    try:
        alerts_dir = OUT / "alerts"
        alerts_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ts = now.isoformat().replace(":", "-")
        alert = {
            "ts": now.isoformat(),
            "source": "autonomy_monitor",
            "entry": entry,
            "error_log": str(ERRLOG.relative_to(Path.cwd())) if ERRLOG.exists() else None,
        }
        alert_path = alerts_dir / f"alert_{ts}.json"
        alert_path.write_text(json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8")

        # update latest pointer
        latest = alerts_dir / "latest_alert.json"
        latest.write_text(json.dumps({"latest": str(alert_path.name), "ts": alert["ts"]}, ensure_ascii=False, indent=2), encoding="utf-8")

        # Append a short operator-facing line to outgoing/bridge/dialog.log if available
        try:
            bridge_dialog = OUT / "bridge" / "dialog.log"
            bridge_dialog.parent.mkdir(parents=True, exist_ok=True)
            with bridge_dialog.open("a", encoding="utf-8") as fh:
                fh.write(f"{alert['ts']} ALERT> autonomy_monitor created alert file={alert_path.relative_to(Path.cwd())}\n")
        except Exception:
            pass

        # Try to show a Windows notification via the helper (non-blocking)
        try:
            import subprocess, sys
            subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1] / "tools" / "notify_toast.py"), "--title", "Calyx Alert", "--msg", f"{alert['ts']}: monitor detected an error"], close_fds=True)
        except Exception:
            pass
    except Exception:
        pass


def run_pulse_once(timeout: float = 30.0) -> int:
    """Run one coordinator pulse and detect errors in output/returncode."""
    _write_lock("running")
    cmd = [sys.executable, "-u", "tools/coordinatorctl.py", "pulse"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        rc = proc.returncode
    except subprocess.TimeoutExpired as e:
        entry = {"error": "timeout", "timeout": timeout, "cmd": cmd}
        _append_error(entry)
        _write_lock("error", {"reason": "timeout"})
        return 2

    combined = out + "\n" + err
    # Simple heuristics: non-zero rc or presence of 'Traceback' indicates a runtime error
    if rc != 0 or "Traceback (most recent call last)" in combined or "Traceback" in combined:
        entry = {"rc": rc, "stdout": out, "stderr": err}
        _append_error(entry)
        _write_lock("error", {"last_error_rc": rc})
        # Create an alert file for operator and CBO inspection
        try:
            _create_alert({"rc": rc, "stdout": out, "stderr": err})
        except Exception:
            pass
        return rc or 1

    _write_lock("ok", {"last_ok": time.time()})
    return 0


def loop(interval: float) -> int:
    try:
        while True:
            run_pulse_once(timeout=30.0)
            time.sleep(max(1.0, float(interval)))
    except KeyboardInterrupt:
        _write_lock("stopped")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="autonomy_monitor")
    ap.add_argument("--interval", type=float, default=0.0, help="Poll interval seconds (0 = run once)")
    ap.add_argument("--once", action="store_true", help="Run one pulse and exit")
    args = ap.parse_args(argv)

    if args.once or args.interval <= 0.0:
        return run_pulse_once(timeout=30.0)
    return loop(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
