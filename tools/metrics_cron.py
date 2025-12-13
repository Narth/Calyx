#!/usr/bin/env python3
"""
Periodic metrics runner for Calyx Terminal.

Runs tools/agent_metrics_report.py every N seconds (default 900s) and appends
timestamped output to logs/metrics_cron.log.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "logs" / "metrics_cron.log"
STATE_PATH = PROJECT_ROOT / "logs" / "metrics_cron_state.json"
AGENT_METRICS = PROJECT_ROOT / "tools" / "agent_metrics_report.py"
AREI_MONITOR = PROJECT_ROOT / "tools" / "agent_resilience_monitor.py"


def _build_command(executable: Path, env_override: str) -> list[str]:
    """Select an execution strategy that works on both Windows and POSIX hosts."""
    override = os.environ.get(env_override)
    if override:
        return shlex.split(override)

    if os.name == "nt":
        return [sys.executable, str(executable)]

    python_bin = shutil.which("python3") or shutil.which("python")
    if shutil.which("bash") and python_bin:
        rel_script = executable.relative_to(PROJECT_ROOT).as_posix()
        python_cmd = Path(python_bin).name
        return ["bash", "-lc", f"cd {PROJECT_ROOT.as_posix()} && {python_cmd} {rel_script}"]

    if python_bin:
        return [python_bin, str(executable)]

    # Fall back to python3 and let the subprocess surface the error.
    return ["python3", str(executable)]


def _read_snapshot():
    # Gather lightweight CPU/mem snapshot from /proc
    load1 = load5 = load15 = 0.0
    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        try:
            with open('/proc/loadavg', 'r') as f:
                parts = f.read().strip().split()[:3]
                load1, load5, load15 = map(float, parts)
        except Exception:
            pass
    mem_avail_kib = 0
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    mem_avail_kib = int(line.split()[1])
                    break
    except Exception:
        pass
    return {
        "load1": float(load1),
        "load5": float(load5),
        "load15": float(load15),
        "mem_avail_gib": float(mem_avail_kib) / 1048576.0 if mem_avail_kib else 0.0,
        "ts": time.time(),
    }


def run_once():
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snap = _read_snapshot()
    # Load last state to compute deltas
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        prev = {}

    d_load1 = snap["load1"] - float(prev.get("load1", 0.0))
    d_mem = snap["mem_avail_gib"] - float(prev.get("mem_avail_gib", 0.0))

    jobs = [
        ("agent_metrics_report", _build_command(AGENT_METRICS, "CALYX_METRICS_CMD")),
        ("agent_resilience_monitor", _build_command(AREI_MONITOR, "CALYX_AREI_CMD")),
    ]

    logs: list[str] = []
    for label, cmd in jobs:
        start_ts = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_ts
        logs.append(
            f"[{label}] exit={res.returncode} duration={duration:.2f}s "
            f"cmd={' '.join(shlex.quote(part) for part in cmd)}"
        )
        if res.stdout:
            logs.append(res.stdout.rstrip())
        if res.stderr:
            logs.append("[stderr]")
            logs.append(res.stderr.rstrip())

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n=== {ts} metrics_cron ===\n")
        f.write(
            "snapshot: "
            f"load1={snap['load1']:.2f}, mem_avail={snap['mem_avail_gib']:.2f}GiB; "
            f"deltas: d_load1={d_load1:+.2f}, d_mem={d_mem:+.2f}GiB\n"
        )
        if logs:
            f.write("\n".join(logs))
            f.write("\n")

    # Save current snapshot
    tmp = STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f)
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=900.0, help="Seconds between metrics runs (min 120s)")
    ap.add_argument("--once", action="store_true", help="Run a single metrics collection and exit")
    args = ap.parse_args()
    if args.once:
        run_once()
        return
    interval = max(120.0, float(args.interval))
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
