"""Watch system memory and trigger probes during heavy runs.

Usage:
    python tools/run_memory_watch.py --threshold 75 --interval 15

This script:
- watches outgoing/ for recent agent_run_* directories
- if system memory percent exceeds threshold (or a run is active), it runs tools/memory_probe.py
- writes snapshots to outgoing/memory_watch_snapshots/

It is intentionally conservative and best-effort (won't kill processes).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"
SNAP_DIR = OUTGOING / "memory_watch_snapshots"
PROBE_SCRIPT = ROOT / "tools" / "memory_probe.py"


def _system_mem_percent() -> float:
    try:
        import psutil
        return float(psutil.virtual_memory().percent)
    except Exception:
        # Fallback to Windows: use "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value"
        if sys.platform.startswith("win"):
            try:
                out = subprocess.check_output(["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/Value"], stderr=subprocess.DEVNULL)
                text = out.decode("utf-8", errors="ignore")
                parts = {}
                for line in text.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        parts[k.strip()] = v.strip()
                free_kb = int(parts.get("FreePhysicalMemory", "0"))
                total_kb = int(parts.get("TotalVisibleMemorySize", "1"))
                used = total_kb - free_kb
                return round((used / total_kb) * 100.0, 2)
            except Exception:
                return 0.0
        return 0.0


def run_probe(snapshot_tag: str) -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out_file = SNAP_DIR / f"snapshot_{snapshot_tag}.json"
    try:
        cmd = [sys.executable, str(PROBE_SCRIPT), "--out", str(out_file)]
        subprocess.run(cmd, check=False)
    except Exception:
        try:
            # fallback: call memory probe inline
            import tools.memory_probe as mp
            mp.main(["--out", str(out_file)])
        except Exception:
            pass


def find_active_runs() -> list[Path]:
    now = time.time()
    runs = []
    for p in OUTGOING.glob("agent_run_*"):
        try:
            m = p.stat().st_mtime
            # consider active if modified in last 10 minutes
            if now - m < 600:
                runs.append(p)
        except Exception:
            pass
    return runs


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=75.0, help="System memory percent threshold to trigger probes")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    args = parser.parse_args(argv)

    while True:
        mem = _system_mem_percent()
        runs = find_active_runs()
        tag = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        if mem >= args.threshold or runs:
            run_probe(f"{tag}_mem{int(mem)}_runs{len(runs)}")
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
