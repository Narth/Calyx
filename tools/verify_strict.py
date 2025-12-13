#!/usr/bin/env python3
"""Robust verifier: programmatic pytest + monitor run with reliable file writes.

This script runs pytest programmatically (capturing stdout/stderr via
redirected streams) and then runs the monitor once via subprocess. It writes
absolute-path logs under the workspace `outgoing/` directory and a JSON
summary `outgoing/verify_strict_summary.json`.

Use this when simpler subprocess captures produce empty files in the environment.
"""
from __future__ import annotations
import io
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from contextlib import redirect_stdout, redirect_stderr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
OUT.mkdir(parents=True, exist_ok=True)

def run_pytest_programmatic(timeout: int = 600) -> dict:
    import pytest

    buf_out = io.StringIO()
    buf_err = io.StringIO()
    # Run pytest.main within redirected stdout/stderr
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = pytest.main(["-q", "--maxfail=1"])  # programmatic invocation
    except Exception as e:
        # Capture exception text
        buf_err.write(f"EXCEPTION_WHILE_RUNNING_PYTEST: {e}\n")
        rc = 2

    out = buf_out.getvalue()
    err = buf_err.getvalue()
    # Write to absolute log
    pytest_log = OUT / "pytest_strict_capture.log"
    pytest_log.write_text(out + "\n" + err, encoding="utf-8")
    return {"rc": rc, "stdout": out, "stderr": err, "log": str(pytest_log)}

def run_monitor_subprocess(timeout: int = 120) -> dict:
    cmd = [sys.executable, "-u", str(ROOT / "tools" / "autonomy_monitor.py"), "--once"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = proc.stdout or ""
        err = proc.stderr or ""
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        out = ""
        err = f"TIMEOUT after {timeout}s"
        rc = 124

    monitor_log = OUT / "monitor_strict_capture.log"
    monitor_log.write_text(out + "\n" + err, encoding="utf-8")
    return {"rc": rc, "stdout": out, "stderr": err, "log": str(monitor_log)}

def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    summary = {"timestamp": ts, "pytest": None, "monitor": None}

    summary["pytest"] = run_pytest_programmatic()
    summary["monitor"] = run_monitor_subprocess()

    summary_path = OUT / "verify_strict_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
