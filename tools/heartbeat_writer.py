#!/usr/bin/env python3
"""
Lightweight heartbeat writer for Calyx Terminal.

Purpose:
- Append periodic heartbeat entries to logs/HEARTBEATS.md
- Keep content minimal and markdown-friendly; no external deps.

Behavior:
- On each tick, writes a single bullet with timestamp and key agents running.
- If file is missing, creates a simple header section.

Usage:
- python -u tools/heartbeat_writer.py --interval 300        # loop
- python -u tools/heartbeat_writer.py --once                 # one-shot

Notes:
- Designed to run inside WSL with the project cwd set to /mnt/c/Calyx_Terminal.
- Uses `pgrep` to detect known agents; degrades gracefully if unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time


AGENT_MATCH = "traffic_navigator.py|tes_monitor.py|agent_scheduler.py|agent_watcher.py|agent_console.py|svc_supervisor.py|metrics_cron.py"
HEARTBEATS_PATH = os.path.join("logs", "HEARTBEATS.md")
SUPERVISOR_STATE = os.path.join("logs", "svc_supervisor_state.json")
NAVIGATOR_CONTROL_LOCK = os.path.join("outgoing", "navigator_control.lock")


def _ts() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_header(path: str) -> None:
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Calyx Terminal — Heartbeats Index\n\n")
        f.write("This document lists notable heartbeat events recorded by the Calyx Terminal.\n\n")


def get_running_agents() -> list[str]:
    """Return a best-effort list of active Calyx agents.

    Preference order:
    1) WSL pgrep (when available)
    2) Windows/psutil fallback: scan python.exe command lines
    """
    # Try WSL/pgrep first
    try:
        cmd = ["bash", "-lc", f"pgrep -af '{AGENT_MATCH}' || true"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        lines = [ln.strip() for ln in (res.stdout or "").splitlines() if ln.strip()]
        agents = []
        for ln in lines:
            parts = ln.split(maxsplit=1)
            agents.append(parts[1] if len(parts) > 1 else ln)
        if agents:
            return agents
    except Exception:
        pass

    # Fallback: Windows/psutil process scan (no external deps beyond psutil if present)
    try:
        import psutil  # type: ignore
        patterns = [p.strip() for p in AGENT_MATCH.split("|")]
        found: list[str] = []
        for proc in psutil.process_iter(attrs=["name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name != "python.exe" and name != "python":
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd = " ".join(cmdline).lower()
                if any(p.lower() in cmd for p in patterns):
                    # Trim noisy prefixes; show from 'tools/' or 'Scripts/' onward when possible
                    display = cmd
                    for marker in ("tools\\", "tools/", "scripts\\", "scripts/"):
                        idx = cmd.find(marker)
                        if idx != -1:
                            display = cmd[idx:]
                            break
                    found.append(display)
            except Exception:
                continue
        return found
    except Exception:
        return []


def write_heartbeat(path: str) -> None:
    ensure_header(path)
    agents = get_running_agents()
    now = _ts()
    entry_lines = []
    entry_lines.append(f"\n## {now} — System Heartbeat\n")
    if agents:
        entry_lines.append("- Active agents:")
        for a in agents:
            entry_lines.append(f"  - {a}")
    else:
        entry_lines.append("- Active agents: none detected")

    # Hardware snapshot (Python-based; no external deps; WSL-friendly)
    try:
        # CPU count
        cpu = os.cpu_count() or 0
        # Load averages
        try:
            load1, load5, load15 = os.getloadavg()
        except Exception:
            # Fallback via /proc/loadavg
            load1 = load5 = load15 = 0.0
            try:
                with open('/proc/loadavg', 'r') as f:
                    parts = f.read().strip().split()
                    load1, load5, load15 = map(float, parts[:3])
            except Exception:
                pass
        # Memory
        mem_total_kib = 0
        mem_avail_kib = 0
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_total_kib = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        mem_avail_kib = int(line.split()[1])
        except Exception:
            pass
        mem_t_gb = f"{mem_total_kib/1048576:.2f}GiB" if mem_total_kib else "?"
        mem_a_gb = f"{mem_avail_kib/1048576:.2f}GiB" if mem_avail_kib else "?"
        # Uptime
        up_h = up_m = 0
        try:
            with open('/proc/uptime', 'r') as f:
                up_sec = float(f.read().split()[0])
                up_h = int(up_sec // 3600)
                up_m = int((up_sec % 3600) // 60)
        except Exception:
            pass
        # Disk (root filesystem)
        try:
            # Use current drive on Windows; '/' is fine for WSL
            root_path = os.path.splitdrive(os.getcwd())[0] + os.sep if os.name == 'nt' else '/'
            du = shutil.disk_usage(root_path)
            disk_total = du.total
            disk_free = du.free
            disk_total_gb = f"{disk_total/1073741824:.2f}GiB"
            disk_free_gb = f"{disk_free/1073741824:.2f}GiB"
            # Disk alert if below threshold
            threshold = float(os.getenv('HEARTBEAT_DISK_FREE_THRESHOLD', '0.15'))
            ratio = (disk_free / disk_total) if disk_total else 1.0
            disk_alert = ratio < threshold
            disk_threshold_pct = int(threshold * 100)
        except Exception:
            disk_total_gb = disk_free_gb = "?"
            disk_alert = False
            disk_threshold_pct = 0

        entry_lines.append(
            "- HW: "
            f"cpu={cpu}, load(1/5/15)={load1:.2f}/{load5:.2f}/{load15:.2f}, "
            f"mem_total={mem_t_gb}, mem_avail={mem_a_gb}, "
            f"disk_total={disk_total_gb}, disk_free={disk_free_gb}, "
            f"uptime={up_h}h{up_m:02d}m"
        )
        if disk_alert:
            pct_text = f"<{disk_threshold_pct}%" if disk_threshold_pct else "low"
            entry_lines.append(f"- Alert: low disk free space ({pct_text}); consider cleanup soon.")
    except Exception:
        entry_lines.append("- HW: unavailable")

    # Small context line to assist later correlation
    entry_lines.append("- Context: WSL venv active if present; local-only mode; scheduler and navigator should appear when running.")

    # Supervisor annotations: include backoff and recent restarts if any
    try:
        if os.path.exists(SUPERVISOR_STATE):
            with open(SUPERVISOR_STATE, 'r', encoding='utf-8') as f:
                state = json.load(f)
            now_ts = time.time()
            backoffs = []
            restarts = []
            for key, s in state.items():
                bo = float(s.get('backoff_until', 0) or 0)
                if now_ts < bo:
                    backoffs.append((key, int(bo - now_ts)))
                rts = [t for t in s.get('restart_times', []) if isinstance(t, (int, float)) and now_ts - t <= 600]
                if rts:
                    restarts.append((key, len(rts)))
            if backoffs:
                parts = [f"{k}({secs}s)" for k, secs in backoffs]
                entry_lines.append(f"- Supervisor: backoff active -> {'; '.join(parts)}")
            if restarts:
                parts = [f"{k}({n} in 10m)" for k, n in restarts]
                entry_lines.append(f"- Supervisor: recent restarts -> {'; '.join(parts)}")
    except Exception:
        # Silent failure; keep heartbeat robust
        pass

    # Navigator control summary: show current probe interval and any pause window
    try:
        if os.path.exists(NAVIGATOR_CONTROL_LOCK):
            with open(NAVIGATOR_CONTROL_LOCK, 'r', encoding='utf-8') as f:
                ctl = json.load(f)
            probe_iv = ctl.get('probe_interval_sec')
            pause_until = ctl.get('pause_until')
            ctl_bits = []
            if isinstance(probe_iv, (int, float)) and probe_iv > 0:
                ctl_bits.append(f"probe_interval={int(probe_iv)}s")
            if isinstance(pause_until, (int, float)) and pause_until > 0:
                try:
                    remain = int(max(0.0, float(pause_until) - time.time()))
                    if remain > 0:
                        ctl_bits.append(f"pause_remaining={remain}s")
                except Exception:
                    pass
            if ctl_bits:
                entry_lines.append(f"- Navigator control: {'; '.join(ctl_bits)}")
    except Exception:
        # Best-effort only
        pass

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines) + "\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=300.0, help="Seconds between heartbeats (ignored when --once)")
    ap.add_argument("--once", action="store_true", help="Write a single heartbeat and exit")
    args = ap.parse_args(argv)

    path = HEARTBEATS_PATH
    if args.once:
        write_heartbeat(path)
        return 0

    # Loop mode
    interval = max(30.0, float(args.interval))  # guard: min 30s
    try:
        while True:
            write_heartbeat(path)
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
