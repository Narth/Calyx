#!/usr/bin/env python3
"""Stewardship Health Monitor Launcher v0.1 (Stabilization)

Read-only dashboard with two explicit actions:
- Start Stewardship Supervisor
- Run Health Check (export)

No other writes or hidden automation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Optional

from tools.stewardship_healthcheck import collect_health_snapshot, write_healthcheck


ROOT = Path(__file__).resolve().parents[1]

RUNS_LOG = ROOT / "logs" / "stewardship" / "healthcheck_runs.jsonl"

SUPERVISOR_SCRIPT = ROOT / "tools" / "svc_supervisor_adaptive.py"

SUPERVISOR_ARGS = [
    "-u",
    str(SUPERVISOR_SCRIPT),
    "--interval",
    "60",
    "--include-uptime-tracker",
    "--uptime-interval",
    "60",
    "--include-enhanced-metrics",
    "--enhanced-metrics-interval",
    "60",
    "--include-bridge-pulse-scheduler",
    "--bridge-pulse-heartbeat-only",
    "--include-telemetry-sentinel",
    "--telemetry-sentinel-interval",
    "60",
]


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_event(event: dict[str, Any]) -> None:
    # Stabilization: keep all governance events in the single append-only log.
    RUNS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _windows_find_processes_cmd_contains(needle: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and ($_.CommandLine -like '*" + needle + "*') -and ($_.CommandLine -notlike '*Get-CimInstance Win32_Process*') } | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode != 0:
            return []
        raw = (proc.stdout or "").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []

        matches: list[dict[str, Any]] = []
        for d in data:
            if not isinstance(d, dict):
                continue
            cmd = d.get("CommandLine")
            pid = d.get("ProcessId")
            if pid is None:
                continue
            matches.append({"pid": int(pid), "name": d.get("Name"), "cmdline": [cmd] if isinstance(cmd, str) else []})
        return matches
    except Exception:
        return []


def _detect_running_supervisor() -> dict[str, Any]:
    """Best-effort detection using psutil if available."""
    matches: list[dict[str, Any]] = []
    detected = False
    running: Optional[bool] = None

    try:
        import psutil  # type: ignore

        detected = True
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                joined = " ".join(cmdline)
                if "svc_supervisor_adaptive.py" in joined.replace("/", "\\"):
                    matches.append({
                        "pid": int(proc.info["pid"]),
                        "name": proc.info.get("name"),
                        "cmdline": cmdline,
                    })
            except Exception:
                continue
    except Exception:
        pass

    cim_matches = _windows_find_processes_cmd_contains("svc_supervisor_adaptive.py")
    if cim_matches:
        detected = True
        existing_pids = {m.get("pid") for m in matches}
        for m in cim_matches:
            if m.get("pid") not in existing_pids:
                matches.append(m)

    if detected:
        running = len(matches) > 0

    return {"detected": detected, "running": running, "processes": matches}


def _start_supervisor() -> dict[str, Any]:
    now = time.time()
    cmd = [sys.executable] + SUPERVISOR_ARGS

    status = _detect_running_supervisor()

    # If any adaptive supervisor is already running, do not start a second.
    if status.get("running"):
        event = {
            "ts": now,
            "iso": _utc_iso(now),
            "event": "start_stewardship_supervisor",
            "outcome": "already_running",
            "cmd": cmd,
            "details": {"detected": status},
        }
        _append_event(event)
        return {"ok": True, "outcome": "already_running", "detected": status}

    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)

        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        event = {
            "ts": now,
            "iso": _utc_iso(now),
            "event": "start_stewardship_supervisor",
            "outcome": "started",
            "cmd": cmd,
            "details": {"pid": proc.pid},
        }
        _append_event(event)

        return {"ok": True, "outcome": "started", "pid": proc.pid}
    except Exception as e:  # noqa: BLE001
        event = {
            "ts": now,
            "iso": _utc_iso(now),
            "event": "start_stewardship_supervisor",
            "outcome": "error",
            "cmd": cmd,
            "details": {"error": f"{type(e).__name__}: {e}"},
        }
        _append_event(event)
        return {"ok": False, "outcome": "error", "error": event["details"]["error"]}


@dataclass
class UiState:
    last_snapshot: dict[str, Any] | None = None
    last_healthcheck: dict[str, Any] | None = None


class StewardshipLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Stewardship Health Monitor Launcher v0.1")
        self.geometry("1100x720")

        self.state = UiState()
        self._start_in_progress = False

        self._build_ui()
        self._refresh(readonly=True)

    # ---- UI ------------------------------------------------------------

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        # Overview
        self.lbl_overall = ttk.Label(root, text="Overall: (loading)", font=("Segoe UI", 14, "bold"))
        self.lbl_overall.pack(anchor=tk.W)

        self.lbl_mode = ttk.Label(root, text="Mode: READ-ONLY (Stabilization)")
        self.lbl_mode.pack(anchor=tk.W, pady=(2, 8))

        self.lbl_last_check = ttk.Label(root, text="Last Health Check: (none)")
        self.lbl_last_check.pack(anchor=tk.W, pady=(0, 12))

        # Main content split
        main = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, padding=(0, 0, 10, 0))
        right = ttk.Frame(main)
        main.add(left, weight=2)
        main.add(right, weight=3)

        # Stewardship loops table
        loops_box = ttk.LabelFrame(left, text="B) Stewardship Loops")
        loops_box.pack(fill=tk.BOTH, expand=False)

        cols = ("lock", "status", "age_sec", "timestamp", "path")
        self.tree = ttk.Treeview(loops_box, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("lock", width=160, anchor=tk.W)
        self.tree.column("status", width=90, anchor=tk.W)
        self.tree.column("age_sec", width=90, anchor=tk.E)
        self.tree.column("timestamp", width=190, anchor=tk.W)
        self.tree.column("path", width=480, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # CBO presence
        cbo_box = ttk.LabelFrame(left, text="C) CBO Presence")
        cbo_box.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.lbl_cbo = ttk.Label(cbo_box, text="cbo.lock: (unknown)")
        self.lbl_cbo.pack(anchor=tk.W, padx=8, pady=(8, 4))

        self.txt_activity = tk.Text(cbo_box, height=10, wrap="none")
        self.txt_activity.configure(state=tk.DISABLED)
        self.txt_activity.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Repo hooks
        repo_box = ttk.LabelFrame(right, text="D) Repo Hooks (Display-only)")
        repo_box.pack(fill=tk.X, expand=False)

        self.lbl_repo = ttk.Label(repo_box, text="Git: (unknown)")
        self.lbl_repo.pack(anchor=tk.W, padx=8, pady=8)

        # Controls
        controls = ttk.LabelFrame(right, text="E) Controls")
        controls.pack(fill=tk.X, expand=False, pady=(12, 0))

        btn_row = ttk.Frame(controls)
        btn_row.pack(fill=tk.X, padx=8, pady=8)

        self.btn_start = ttk.Button(btn_row, text="Start Stewardship Supervisor", command=self._on_start_supervisor)
        self.btn_start.pack(side=tk.LEFT)

        self.btn_health = ttk.Button(btn_row, text="Run Health Check", command=self._on_run_healthcheck)
        self.btn_health.pack(side=tk.LEFT, padx=(10, 0))

        self.lbl_action = ttk.Label(controls, text="")
        self.lbl_action.pack(anchor=tk.W, padx=8, pady=(0, 8))

    # ---- behaviors -----------------------------------------------------

    def _set_activity_text(self, lines: list[str]) -> None:
        self.txt_activity.configure(state=tk.NORMAL)
        self.txt_activity.delete("1.0", tk.END)
        self.txt_activity.insert(tk.END, "\n".join(lines) + ("\n" if lines else ""))
        self.txt_activity.configure(state=tk.DISABLED)

    def _load_last_healthcheck_summary(self) -> Optional[dict[str, Any]]:
        runs_log = ROOT / "logs" / "stewardship" / "healthcheck_runs.jsonl"
        if not runs_log.exists():
            return None
        try:
            lines = runs_log.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines:
                return None
            last = json.loads(lines[-1])
            if isinstance(last, dict):
                return last
        except Exception:
            return None
        return None

    def _refresh(self, *, readonly: bool) -> None:
        # readonly=True means no writes; this function is read-only.
        snap = collect_health_snapshot()
        self.state.last_snapshot = snap

        overall = snap.get("overall_status")
        self.lbl_overall.configure(text=f"Overall: {overall}")

        last = self._load_last_healthcheck_summary()
        if last:
            self.lbl_last_check.configure(text=f"Last Health Check: {last.get('iso')} ({last.get('overall_status')})")
        else:
            self.lbl_last_check.configure(text="Last Health Check: (none)")

        # table
        for row in self.tree.get_children():
            self.tree.delete(row)

        locks = snap.get("locks") or []
        for l in locks:
            name = l.get("name")
            status = l.get("status")
            age = l.get("age_sec")
            ts = l.get("mtime_utc")
            path = l.get("path")
            self.tree.insert("", tk.END, values=(name, status, age if age is not None else "-", ts or "-", path or "-"))

        # CBO presence
        cbo = next((l for l in locks if l.get("name") == "cbo"), None)
        if cbo:
            self.lbl_cbo.configure(text=f"cbo.lock: {cbo.get('status')} (mtime_utc={cbo.get('mtime_utc')})")
        else:
            self.lbl_cbo.configure(text="cbo.lock: (missing)")

        activity = snap.get("cbo_activity") or {}
        if activity.get("found"):
            self._set_activity_text([f"Activity log: {activity.get('path')}", ""] + (activity.get("tail") or []))
        else:
            self._set_activity_text(["no activity log found"])

        # Repo
        repo = snap.get("repo") or {}
        if repo.get("git"):
            bits = [
                f"Branch: {repo.get('branch')}",
                f"HEAD: {repo.get('head')}",
                f"Dirty: {repo.get('dirty')}",
            ]
            if repo.get("origin"):
                bits.append(f"Origin: {repo.get('origin')}")
            self.lbl_repo.configure(text=" | ".join(bits))
        else:
            self.lbl_repo.configure(text="Git: not detected")

    def _on_start_supervisor(self) -> None:
        if self._start_in_progress:
            return
        self._start_in_progress = True

        try:
            self.btn_start.configure(state=tk.DISABLED)
        except Exception:
            pass

        self.lbl_action.configure(text="Starting stewardship supervisor…")
        self.update_idletasks()

        try:
            result = _start_supervisor()
            if result.get("ok") and result.get("outcome") == "started":
                self.lbl_action.configure(text=f"Started (pid={result.get('pid')})")
            elif result.get("ok") and result.get("outcome") == "already_running":
                self.lbl_action.configure(text="Already running")
            else:
                self.lbl_action.configure(text=f"Error: {result.get('error')}")
                messagebox.showerror("Start Stewardship Supervisor", str(result.get("error")))

            # Refresh read-only view after action
            self._refresh(readonly=True)
        finally:
            try:
                self.btn_start.configure(state=tk.NORMAL)
            except Exception:
                pass
            self._start_in_progress = False

    def _on_run_healthcheck(self) -> None:
        self.lbl_action.configure(text="Running health check export…")
        self.update_idletasks()

        snap = collect_health_snapshot()
        try:
            result = write_healthcheck(snap, write_md=True)
        except Exception as e:  # noqa: BLE001
            self.lbl_action.configure(text=f"Error: {type(e).__name__}: {e}")
            messagebox.showerror("Run Health Check", f"{type(e).__name__}: {e}")
            return

        self.state.last_healthcheck = result
        self.lbl_action.configure(text=f"Wrote {Path(result['json_path']).name} ({result.get('overall_status')})")

        # Refresh read-only view after action
        self._refresh(readonly=True)


def main() -> int:
    app = StewardshipLauncher()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
