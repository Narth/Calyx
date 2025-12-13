#!/usr/bin/env python3
"""
GPU Recycle: Gracefully restart supervised services to pick up GPU env.

Targets (any python process whose command line contains one of):
- tools/svf_probe.py
- tools/triage_probe.py
- tools/sys_integrator.py
- tools/traffic_navigator.py
- tools/agent_scheduler.py
- tools/heartbeat_writer.py

Behavior:
- Attempts terminate(), waits up to 5s; escalates to kill() if still alive.
- Skips own process.
- Prints a compact summary of actions.

Usage:
  python -u tools/gpu_recycle.py
"""
from __future__ import annotations
import os
import sys
import time

TARGETS = [
    "tools/svf_probe.py",
    "tools\\svf_probe.py",
    "tools/triage_probe.py",
    "tools\\triage_probe.py",
    "tools/sys_integrator.py",
    "tools\\sys_integrator.py",
    "tools/traffic_navigator.py",
    "tools\\traffic_navigator.py",
    "tools/agent_scheduler.py",
    "tools\\agent_scheduler.py",
    "tools/heartbeat_writer.py",
    "tools\\heartbeat_writer.py",
]


def main() -> int:
    try:
        import psutil  # type: ignore
    except Exception:
        print("[gpu_recycle] psutil is required for process recycle", flush=True)
        return 1

    me = os.getpid()
    hits = []
    for p in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            pid = int(p.info.get("pid"))
            if pid == me:
                continue
            name = (p.info.get("name") or "").lower()
            if name not in ("python.exe", "python"):
                continue
            cmdline = p.info.get("cmdline") or []
            cmd = " ".join(str(x) for x in cmdline)
            if any(t in cmd for t in TARGETS):
                hits.append((pid, cmd))
        except Exception:
            continue

    if not hits:
        print("[gpu_recycle] No target processes found.", flush=True)
        return 0

    print(f"[gpu_recycle] Recycling {len(hits)} process(es)...", flush=True)
    killed = 0
    for pid, cmd in hits:
        try:
            proc = psutil.Process(pid)
            print(f" - terminate PID {pid}: {cmd}", flush=True)
            proc.terminate()
        except Exception:
            continue
    # wait and escalate
    deadline = time.time() + 5.0
    remaining = []
    for pid, cmd in hits:
        try:
            proc = psutil.Process(pid)
            while time.time() < deadline:
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    break
                time.sleep(0.1)
            if proc.is_running():
                print(f" ! kill PID {pid}", flush=True)
                proc.kill()
                killed += 1
            else:
                remaining.append(pid)
        except Exception:
            continue
    print(f"[gpu_recycle] Done. Terminated={len(remaining)} Killed={killed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
