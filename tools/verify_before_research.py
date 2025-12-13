#!/usr/bin/env python3
"""Run verification checks before flipping to research mode.

This script runs the full pytest suite (fail-fast) and then runs a one-shot
autonomy monitor pulse. It captures stdout/stderr and writes logs to
`outgoing/pytest_capture.log`, `outgoing/monitor_capture.log`, and a
`outgoing/verify_summary.json` with rc/status info.

Usage: python tools/verify_before_research.py
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
OUT.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd, timeout=300):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "rc": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired as e:
        return {"rc": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}

def main():
    ts = datetime.now(timezone.utc).isoformat()
    summary = {"timestamp": ts, "tests": None, "monitor": None}

    # 1) Run pytest (full suite, fail-fast)
    pytest_log = OUT / "pytest_capture.log"
    cmd = [sys.executable, "-u", "-m", "pytest", "-q", "--maxfail=1"]
    res = run_cmd(cmd, timeout=600)
    pytest_log.write_text(res.get("stdout", "") + "\n" + res.get("stderr", ""), encoding="utf-8")
    summary["tests"] = {"rc": res.get("rc"), "log": str(pytest_log)}

    # 2) Run monitor once
    monitor_log = OUT / "monitor_capture.log"
    cmd = [sys.executable, "-u", "tools/autonomy_monitor.py", "--once"]
    res = run_cmd(cmd, timeout=120)
    monitor_log.write_text(res.get("stdout", "") + "\n" + res.get("stderr", ""), encoding="utf-8")
    summary["monitor"] = {"rc": res.get("rc"), "log": str(monitor_log)}

    # 3) Write JSON summary
    summary_path = OUT / "verify_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
