#!/usr/bin/env python3
"""
Service Supervisor for essential Calyx agents (WSL).

Keeps the following running with minimal interference:
 - agent_scheduler.py --interval 180 --auto-promote --promote-after 5 --cooldown-mins 30
 - traffic_navigator.py --interval 3 --control --pause-sec 90 --hot-interval 120 --cool-interval 30
 - tes_monitor.py --interval 10 --tail 5
 - heartbeat_writer.py --interval 300

Runs in a loop (default every 60s). If a process isn't found via pgrep, it starts it detached.
No external dependencies. Intended to be conservative and idempotent.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time


PROJECT_ROOT = "/mnt/c/Calyx_Terminal"
STATE_PATH = os.path.join("logs", "svc_supervisor_state.json")


def _run(cmd: str) -> str:
    res = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return (res.stdout or "") + (res.stderr or "")


def _pgrep(pattern: str) -> bool:
    out = _run(f"pgrep -af '{pattern}' || true")
    return any(line.strip() for line in out.splitlines())


def _start_detached(py: str) -> None:
    """Start a python tool detached under WSL with venv activation and safe env.

    This function is defensive: it activates ~/.calyx-venv before invoking python to
    avoid failures when the caller forgot to source the venv. Logs are redirected
    to logs/supervisor_<script>.log.
    """
    _run(
        " ".join([
            # Ensure repo and venv
            f"cd {PROJECT_ROOT}",
            "&&",
            "source ~/.calyx-venv/bin/activate || true",
            "&&",
            "nohup",
            "env",
            "SVF_APPROVAL_MODE=auto",
            "SVF_LOCAL_ONLY=1",
            "SVF_GOVERNANCE_GATE=local",
            "HEARTBEAT_DISK_FREE_THRESHOLD=0.15",
            f"python -u {py}",
            ">",
            f"logs/supervisor_{os.path.basename(py)}.log",
            "2>&1",
            "&",
            "disown",
        ])
    )


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def _pr(msg: str) -> None:
    # Print for log capture
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def _ensure_with_backoff(state: dict, key: str, pattern: str, cmd: str,
                         window_sec: int = 600, max_restarts: int = 3, backoff_sec: int = 300) -> None:
    now = time.time()
    s = state.get(key, {})
    backoff_until = s.get("backoff_until", 0)
    if _pgrep(pattern):
        return
    if now < backoff_until:
        _pr(f"{key}: missing but in backoff for {int(backoff_until - now)}s")
        return
    # restart
    _pr(f"{key}: not running, starting: {cmd}")
    _start_detached(cmd)
    # update state
    times = [t for t in s.get("restart_times", []) if now - t <= window_sec]
    times.append(now)
    s["restart_times"] = times
    if len(times) >= max_restarts:
        s["backoff_until"] = now + backoff_sec
        _pr(f"{key}: restart threshold reached ({len(times)}/{max_restarts}), backing off {backoff_sec}s")
    state[key] = s


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def ensure_processes(state: dict):
    _ensure_with_backoff(state, "scheduler",
                         pattern="agent_scheduler.py.*auto-promote",
                         cmd="tools/agent_scheduler.py --interval 180 --auto-promote --promote-after 5 --cooldown-mins 30")

    # Traffic Navigator (control)
    # We only ensure the control variant exists; no auto-kill of non-control here.
    pause = _env_int("NAVIGATOR_PAUSE_SEC", 90)
    hot = _env_int("NAVIGATOR_HOT_INTERVAL", 90)
    cool = _env_int("NAVIGATOR_COOL_INTERVAL", 20)
    _ensure_with_backoff(state, "traffic_control",
                         pattern="traffic_navigator.py.*--control",
                         cmd=f"tools/traffic_navigator.py --interval 3 --control --pause-sec {pause} --hot-interval {hot} --cool-interval {cool}")

    _ensure_with_backoff(state, "tes_monitor",
                         pattern="tes_monitor.py",
                         cmd="tools/tes_monitor.py --interval 10 --tail 5")

    _ensure_with_backoff(state, "heartbeat",
                         pattern="heartbeat_writer.py",
                         cmd="tools/heartbeat_writer.py --interval 300")

    # Triage Probe — keep triage lock fresh and consume navigator control locks
    _ensure_with_backoff(state, "triage_probe",
                         pattern="triage_probe.py",
                         cmd="tools/triage_probe.py --interval 2 --probe-every 15")

    # SVF Probe — keep SVF channel alive for shared voice governance
    _ensure_with_backoff(state, "svf_probe",
                         pattern="svf_probe.py",
                         cmd="tools/svf_probe.py --interval 5")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=60.0, help="Seconds between checks (min 15s)")
    args = ap.parse_args()
    interval = max(15.0, float(args.interval))
    while True:
        state = _load_state()
        ensure_processes(state)
        _save_state(state)
        time.sleep(interval)


if __name__ == "__main__":
    main()
