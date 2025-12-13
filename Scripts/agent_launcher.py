"""
Agent Launcher — one window to run common Calyx Agent commands.

Features
- Open Watcher GUI
- Start/Stop Triage Probe (WSL adaptive)
- Probe once (Win test)
- Open Agent Console (Windows)
- Agent one-shot (WSL): prompt for goal and optional args
- Live status panel for agent1.lock and triage.lock

Notes
- Designed for Windows with WSL2; uses the WSL venv at ~/.calyx-venv for WSL actions.
- Stop Probe (WSL) uses pkill inside WSL: "pkill -f tools/triage_probe.py".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

def _fallback_messagebox(title: str, message: str) -> None:
    try:
        # Try Tkinter messagebox with a temporary root
        import tkinter as _tk
        from tkinter import messagebox as _mb
        root = _tk.Tk()
        root.withdraw()
        try:
            _mb.showerror(title, message)
        finally:
            root.destroy()
        return
    except Exception:
        pass
    try:
        # Fallback to Windows MessageBoxW
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x00000010)
    except Exception:
        # Last resort: print to stderr
        print(f"{title}: {message}", file=sys.stderr)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
except Exception as exc:
    _fallback_messagebox("Calyx Agent Launcher", f"Tkinter not available: {exc}\n\nTip: ensure you are using the project venv Python.")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _wsl(cmd: str) -> subprocess.Popen:
    return subprocess.Popen(["wsl", "bash", "-lc", cmd], cwd=str(ROOT))


def _run_py(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-u", *args], cwd=str(ROOT))


def _wsl_status(cmd: str) -> tuple[int, str, str]:
    """Run a WSL command and return (rc, stdout, stderr)."""
    proc = subprocess.run(["wsl", "bash", "-lc", cmd], cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class LauncherApp:
    def __init__(self) -> None:
        self.win = tk.Tk()
        self.win.title("Calyx Agent Launcher")
        self.win.geometry("820x520")

        # Simple internal state for automation
        self.feeders_started = False
        self.digestors_started = False
        self.did_warn_python = False
        self.did_warn_llm = False
        self.did_bus_ping_once = False
        self.auto_activate_var = tk.BooleanVar(value=False)

        container = ttk.Frame(self.win, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Actions row (streamlined)
        act = ttk.LabelFrame(container, text="Actions")
        act.pack(fill=tk.X, pady=(0, 8))

        btn_watcher = ttk.Button(act, text="Open Watcher", command=self.open_watcher)
        btn_watcher.pack(side=tk.LEFT, padx=4, pady=6)

        btn_watcher_paged = ttk.Button(act, text="Open Watcher (Paged)", command=self.open_watcher_paged)
        btn_watcher_paged.pack(side=tk.LEFT, padx=4)

        btn_probe_start = ttk.Button(act, text="Start Probe (WSL Adaptive)", command=self.start_probe_adaptive)
        btn_probe_start.pack(side=tk.LEFT, padx=4)

        btn_probe_stop = ttk.Button(act, text="Stop Probe (WSL)", command=self.stop_probe)
        btn_probe_stop.pack(side=tk.LEFT, padx=4)

        # Keep one-shot probe test available under Diagnostics below

        btn_console = ttk.Button(act, text="Open Agent Console", command=self.open_console)
        btn_console.pack(side=tk.LEFT, padx=16)

        btn_oneshot = ttk.Button(act, text="Agent one-shot (WSL)", command=self.agent_oneshot)
        btn_oneshot.pack(side=tk.LEFT, padx=4)

        # Hide heavier apply/tests from primary row to reduce clutter

        # Diagnostics row — quick deployment of probes/monitors to fix stale or failing systems
        diag = ttk.LabelFrame(container, text="Diagnostics & Monitors")
        diag.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(diag, text="Fix Stale Monitor (Restart Probes)", command=self.restart_all_probes).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(diag, text="TES Monitor", command=self.open_tes_monitor).pack(side=tk.LEFT, padx=4)
        ttk.Button(diag, text="Metrics Report", command=self.open_metrics_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(diag, text="Navigator (start)", command=self.start_navigator).pack(side=tk.LEFT, padx=16)
        ttk.Button(diag, text="Manifest Probe (start)", command=self.start_manifest_probe).pack(side=tk.LEFT, padx=4)
        ttk.Button(diag, text="Sys Integrator (start)", command=self.start_sys_integrator).pack(side=tk.LEFT, padx=4)
        ttk.Button(diag, text="Probe Once (Win test)", command=self.probe_once_win).pack(side=tk.LEFT, padx=16)
        ttk.Button(diag, text="Stop All Diagnostics", command=self.stop_all_probes).pack(side=tk.LEFT, padx=4)

        # Quick Feeder / Digestor controls for operator convenience
        quick = ttk.Frame(container)
        quick.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(quick, text="Quick Controls:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(quick, text="Start Feeder (agent1a)", command=self.start_feeder_agent1a).pack(side=tk.LEFT, padx=4)
        ttk.Button(quick, text="Stop Feeder (agent1a)", command=self.stop_feeder_agent1a).pack(side=tk.LEFT, padx=4)
        ttk.Separator(quick, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(quick, text="Start Digestors 3&4", command=self.start_digestors_3_4).pack(side=tk.LEFT, padx=4)
        ttk.Button(quick, text="Stop Digestors 3&4", command=self.stop_digestors_3_4).pack(side=tk.LEFT, padx=4)

        # Optional utilities (advanced)
        self.adv_var = tk.BooleanVar(value=False)
        adv = ttk.LabelFrame(container, text="Advanced Utilities (optional)")
        adv.pack(fill=tk.X, pady=(0, 8))
        ttk.Checkbutton(adv, text="Show advanced controls", variable=self.adv_var, command=self._toggle_advanced).pack(side=tk.LEFT, padx=4, pady=6)
        # Create but keep hidden until toggled
        self.util_frame = ttk.Frame(container)
        # Utilities inside advanced
        util = ttk.Frame(self.util_frame)
        util.pack(fill=tk.X)
        ttk.Button(util, text="Indicator (Pop)", command=self.open_indicator).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(util, text="Dock (Top Bar)", command=self.open_dock).pack(side=tk.LEFT, padx=4)
        ttk.Button(util, text="WSL Deps (pip)", command=self.wsl_deps_pip).pack(side=tk.LEFT, padx=16)
        ttk.Button(util, text="WSL Libs (apt)", command=self.wsl_deps_apt).pack(side=tk.LEFT, padx=4)
        auto = ttk.Frame(self.util_frame)
        auto.pack(fill=tk.X, pady=(0, 8))
        ttk.Checkbutton(auto, text="Auto-activate when ready", variable=self.auto_activate_var).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(auto, text="Start All (auto)", command=self.start_all_auto).pack(side=tk.LEFT, padx=8)

        # Feeder controls moved under advanced
        feeders = ttk.LabelFrame(self.util_frame, text="Feeder Agents (Agent1a, Agent1b, Agent1c)")
        feeders.pack(fill=tk.X, pady=(0, 8))
        self.btn_start_feeders = ttk.Button(feeders, text="Start Feeders (fast)", command=self.start_feeders)
        self.btn_start_feeders.pack(side=tk.LEFT, padx=4, pady=6)
        self.btn_start_all = ttk.Button(feeders, text="Start Feeders + Digestors", command=self.start_feeders_and_digestors)
        self.btn_start_all.pack(side=tk.LEFT, padx=4)
        self.btn_stop_feeders = ttk.Button(feeders, text="Stop Feeders", command=self.stop_feeders)
        self.btn_stop_feeders.pack(side=tk.LEFT, padx=4)

        # Digestors controls moved under advanced
        dig = ttk.LabelFrame(self.util_frame, text="Digestors (LLM-free)")
        dig.pack(fill=tk.X, pady=(0, 8))
        self.btn_start_digestors = ttk.Button(dig, text="Start Digestors (2-4)", command=self.start_digestors)
        self.btn_start_digestors.pack(side=tk.LEFT, padx=4, pady=6)
        self.btn_stop_digestors = ttk.Button(dig, text="Stop Digestors", command=self.stop_digestors)
        self.btn_stop_digestors.pack(side=tk.LEFT, padx=4)

        # Agent1 controls
        a1 = ttk.LabelFrame(container, text="Agent1 Controls")
        a1.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(a1, text="Start Scheduler (WSL)", command=self.start_agent1_scheduler).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(a1, text="Stop Scheduler", command=self.stop_agent1_scheduler).pack(side=tk.LEFT, padx=4)
        ttk.Button(a1, text="Agent1 Bus Ping", command=self.agent1_bus_ping).pack(side=tk.LEFT, padx=16)

        # Status
        status = ttk.LabelFrame(container, text="Live status (heartbeats)")
        status.pack(fill=tk.BOTH, expand=True)

        grid = ttk.Frame(status)
        grid.pack(fill=tk.X, pady=(6, 6))

        ttk.Label(grid, text="triage:").grid(row=0, column=0, sticky="w")
        self.triage_lbl = ttk.Label(grid, text="—")
        self.triage_lbl.grid(row=0, column=1, sticky="w")
        self.triage_details = ttk.Label(grid, text="")
        self.triage_details.grid(row=1, column=0, columnspan=2, sticky="w")

        ttk.Separator(grid, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)

        ttk.Label(grid, text="agent1:").grid(row=3, column=0, sticky="w")
        self.agent_lbl = ttk.Label(grid, text="—")
        self.agent_lbl.grid(row=3, column=1, sticky="w")
        self.agent_details = ttk.Label(grid, text="")
        self.agent_details.grid(row=4, column=0, columnspan=2, sticky="w")

        # Agents 2–4 status rows
        ttk.Label(grid, text="agent2:").grid(row=5, column=0, sticky="w")
        self.agent2_lbl = ttk.Label(grid, text="—")
        self.agent2_lbl.grid(row=5, column=1, sticky="w")
        self.agent2_details = ttk.Label(grid, text="")
        self.agent2_details.grid(row=6, column=0, columnspan=2, sticky="w")

        ttk.Label(grid, text="agent3:").grid(row=7, column=0, sticky="w")
        self.agent3_lbl = ttk.Label(grid, text="—")
        self.agent3_lbl.grid(row=7, column=1, sticky="w")
        self.agent3_details = ttk.Label(grid, text="")
        self.agent3_details.grid(row=8, column=0, columnspan=2, sticky="w")

        ttk.Label(grid, text="agent4:").grid(row=9, column=0, sticky="w")
        self.agent4_lbl = ttk.Label(grid, text="—")
        self.agent4_lbl.grid(row=9, column=1, sticky="w")
        self.agent4_details = ttk.Label(grid, text="")
        self.agent4_details.grid(row=10, column=0, columnspan=2, sticky="w")

        # Feeder status rows (agent1a/1b/1c)
        ttk.Label(grid, text="agent1a:").grid(row=11, column=0, sticky="w")
        self.agent1a_lbl = ttk.Label(grid, text="—")
        self.agent1a_lbl.grid(row=11, column=1, sticky="w")
        self.agent1a_details = ttk.Label(grid, text="")
        self.agent1a_details.grid(row=12, column=0, columnspan=2, sticky="w")

        ttk.Label(grid, text="agent1b:").grid(row=13, column=0, sticky="w")
        self.agent1b_lbl = ttk.Label(grid, text="—")
        self.agent1b_lbl.grid(row=13, column=1, sticky="w")
        self.agent1b_details = ttk.Label(grid, text="")
        self.agent1b_details.grid(row=14, column=0, columnspan=2, sticky="w")

        ttk.Label(grid, text="agent1c:").grid(row=15, column=0, sticky="w")
        self.agent1c_lbl = ttk.Label(grid, text="—")
        self.agent1c_lbl.grid(row=15, column=1, sticky="w")
        self.agent1c_details = ttk.Label(grid, text="")
        self.agent1c_details.grid(row=16, column=0, columnspan=2, sticky="w")

        # Log
        self.log = tk.Text(container, height=10, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        # Action status bar
        statusbar = ttk.Frame(container)
        statusbar.pack(fill=tk.X, pady=(4, 0))
        self.action_status = ttk.Label(statusbar, text="Ready")
        self.action_status.pack(side=tk.LEFT, padx=4)
        self.action_prog = ttk.Progressbar(statusbar, mode="indeterminate", length=120)
        self.action_prog.pack(side=tk.RIGHT, padx=4)
        self.action_prog.stop()

        self._log("Launcher ready.")

        self._tick()

    def _toggle_advanced(self) -> None:
        try:
            if self.adv_var.get():
                self.util_frame.pack(fill=tk.X, pady=(0, 8))
            else:
                self.util_frame.pack_forget()
        except Exception:
            pass

    def _log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {msg}\n")
        self.log.see(tk.END)

    # Actions
    def open_watcher(self) -> None:
        try:
            _run_py(["Scripts\\agent_watcher.py", "--quiet"])
            self._log("Watcher launched.")
        except Exception as e:
            messagebox.showerror("Watcher", f"Failed to launch watcher: {e}")

    def start_probe_adaptive(self) -> None:
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "nohup $PY -u tools/triage_probe.py --interval 2 --adaptive "
                "--initial-probe-sec 30 --relaxed-probe-sec 300 --warmup-minutes 15 --agent-boost-sec 90 "
                "> /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Probe (WSL adaptive) started in background.")
        except Exception as e:
            messagebox.showerror("Probe", f"Failed to start probe: {e}")

    def restart_all_probes(self) -> None:
        """Restart triage, manifest, navigator, and sys integrator to fix stale watcher rows."""
        try:
            # Stop first (best-effort)
            _wsl("pkill -f tools/triage_probe.py || true; pkill -f tools/manifest_probe.py || true; pkill -f tools/traffic_navigator.py || true; pkill -f tools/sys_integrator.py || true")
            # Start in background
            cmds = [
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; nohup $PY -u tools/triage_probe.py --interval 2 --adaptive --initial-probe-sec 30 --relaxed-probe-sec 300 --warmup-minutes 15 --agent-boost-sec 90 > /dev/null 2>&1 &",
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; nohup $PY -u tools/manifest_probe.py --interval 5 > /dev/null 2>&1 &",
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; nohup $PY -u tools/traffic_navigator.py --interval 3 > /dev/null 2>&1 &",
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; nohup $PY -u tools/sys_integrator.py --interval 10 > /dev/null 2>&1 &",
            ]
            for c in cmds:
                _wsl(c)
            self._log("Diagnostics restarted: triage, manifest, navigator, sysint.")
        except Exception as e:
            messagebox.showerror("Diagnostics", f"Failed to restart probes: {e}")

    def open_tes_monitor(self) -> None:
        try:
            _run_py(["tools\\tes_monitor.py", "--interval", "10", "--tail", "5"])  # Windows-friendly monitor
            self._log("TES monitor opened.")
        except Exception as e:
            messagebox.showerror("TES Monitor", f"Failed to open TES monitor: {e}")

    def open_metrics_report(self) -> None:
        try:
            _run_py(["tools\\agent_metrics_report.py"]) 
            self._log("Metrics report generated (see logs/agent_metrics_summary.csv).")
        except Exception as e:
            messagebox.showerror("Metrics Report", f"Failed to run metrics report: {e}")

    def start_navigator(self) -> None:
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "nohup $PY -u tools/traffic_navigator.py --interval 3 > /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Navigator started (WSL background).")
        except Exception as e:
            messagebox.showerror("Navigator", f"Failed to start navigator: {e}")

    def start_manifest_probe(self) -> None:
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "nohup $PY -u tools/manifest_probe.py --interval 5 > /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Manifest probe started (WSL background).")
        except Exception as e:
            messagebox.showerror("Manifest Probe", f"Failed to start manifest probe: {e}")

    # Quick Feeder / Digestor starters
    def start_feeder_agent1a(self) -> None:
        try:
            # Use project venv if present and avoid $ var quoting issues
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                "nohup python -u tools/agent_scheduler.py --interval 30 "
                "--heartbeat-name agent1a --agent-id 1 "
                "--agent-args \"--skip-patches --max-steps 1 --publish-bus --heartbeat-name agent1a --llm-token llm_shared --llm-wait-sec 45 --llm-optional\" "
                "> /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Feeder (agent1a) started.")
        except Exception as e:
            messagebox.showerror("Feeder", f"Failed to start feeder agent1a: {e}")

    def stop_feeder_agent1a(self) -> None:
        try:
            # Kill only the feeder scheduler with heartbeat-name agent1a
            cmd = (
                "pkill -f 'agent_scheduler.py .*heartbeat-name agent1a' || true"
            )
            _wsl(cmd)
            self._log("Feeder (agent1a) stop signal sent.")
        except Exception as e:
            messagebox.showerror("Feeder", f"Failed to stop feeder agent1a: {e}")

    def start_digestors_3_4(self) -> None:
        try:
            for aid in (3, 4):
                cmd = (
                    "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                    "cd /mnt/c/Calyx_Terminal && "
                    f"nohup python -u tools/agent_digestor.py --agent-id {aid} --poll-sec 2 --max-files 3 > /dev/null 2>&1 &"
                )
                _wsl(cmd)
            self._log("Digestors (agent3 & agent4) started.")
        except Exception as e:
            messagebox.showerror("Digestors", f"Failed to start digestors 3 & 4: {e}")

    def stop_digestors_3_4(self) -> None:
        try:
            _wsl("pkill -f 'agent_digestor.py --agent-id 3' || true; pkill -f 'agent_digestor.py --agent-id 4' || true")
            self._log("Digestors (agent3 & agent4) stop signals sent.")
        except Exception as e:
            messagebox.showerror("Digestors", f"Failed to stop digestors 3 & 4: {e}")

    def start_sys_integrator(self) -> None:
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "nohup $PY -u tools/sys_integrator.py --interval 10 > /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Systems integrator started (WSL background).")
        except Exception as e:
            messagebox.showerror("Sys Integrator", f"Failed to start systems integrator: {e}")

    def stop_all_probes(self) -> None:
        try:
            _wsl("pkill -f tools/triage_probe.py || true; pkill -f tools/manifest_probe.py || true; pkill -f tools/traffic_navigator.py || true; pkill -f tools/sys_integrator.py || true")
            self._log("Stop signals sent to triage/manifest/navigator/sysint.")
        except Exception as e:
            messagebox.showerror("Diagnostics", f"Failed to stop diagnostics: {e}")

    def open_watcher_paged(self) -> None:
        try:
            _run_py(["Scripts\\agent_watcher.py", "--page-size", "10", "--hide-idle"]) 
            self._log("Watcher (paged) launched.")
        except Exception as e:
            messagebox.showerror("Watcher", f"Failed to launch watcher (paged): {e}")
    def stop_probe(self) -> None:
        try:
            _wsl("pkill -f tools/triage_probe.py || true")
            self._log("Probe stop signal sent (WSL pkill).")
        except Exception as e:
            messagebox.showerror("Probe", f"Failed to stop probe: {e}")

    def probe_once_win(self) -> None:
        try:
            _run_py([
                "tools\\triage_probe.py",
                "--interval", "0.5",
                "--adaptive",
                "--initial-probe-sec", "1",
                "--relaxed-probe-sec", "2",
                "--agent-boost-sec", "1",
                "--max-iters", "6",
            ]) 
            self._log("Probe once (Win) started.")
        except Exception as e:
            messagebox.showerror("Probe", f"Failed to run probe once: {e}")

    def open_console(self) -> None:
        try:
            _run_py(["Scripts\\agent_console.py"]) 
            self._log("Agent console opened.")
        except Exception as e:
            messagebox.showerror("Console", f"Failed to open agent console: {e}")

    # Automation helpers
    def _wsl_has_python(self) -> bool:
        rc, _, _ = _wsl_status("if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then exit 0; else exit 1; fi")
        return rc == 0

    def _wsl_has_llm(self) -> bool:
        rc, _, _ = _wsl_status("PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; $PY -c 'import llama_cpp' 2>/dev/null")
        return rc == 0

    def _try_auto_activate(self) -> None:
        has_py = self._wsl_has_python()
        has_llm = self._wsl_has_llm() if has_py else False
        if not has_py and not self.did_warn_python:
            self._log("WSL python/python3 not found — feeders and digestors pending. Install python3 in WSL.")
            self.did_warn_python = True
        # Start digestors regardless once Python is available
        if has_py and not self.digestors_started:
            try:
                self.start_digestors()
                self.digestors_started = True
            except Exception:
                pass
        # Start feeders only when LLM is importable
        if has_py and has_llm and not self.feeders_started:
            try:
                self.start_feeders()
                self.feeders_started = True
            except Exception:
                pass
        if has_py and self.digestors_started and not self.did_bus_ping_once:
            try:
                # seed digestors with a bus message if a prior run exists
                self.agent1_bus_ping()
                self.did_bus_ping_once = True
            except Exception:
                pass

    def start_all_auto(self) -> None:
        self.auto_activate_var.set(True)
        self._log("Auto-activate enabled and immediate attempt started.")
        self._try_auto_activate()

    def agent_oneshot(self) -> None:
        goal = simpledialog.askstring("Agent one-shot (WSL)", "Enter goal:")
        if not goal:
            return
        agent_id_s = simpledialog.askstring("Agent one-shot (WSL)", "Agent ID (1..9):", initialvalue="1") or "1"
        try:
            agent_id = max(1, min(9, int(agent_id_s)))
        except Exception:
            agent_id = 1
        extra = simpledialog.askstring("Agent one-shot (WSL)", "Extra args (optional):", initialvalue="--skip-patches") or ""
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                f"python tools/agent_runner.py --goal \"{goal.replace('\\', ' ').replace('"', '\\"')}\" --agent-id {agent_id} {extra}"
            )
            _wsl(cmd)
            self._log("Agent one-shot (WSL) invoked.")
        except Exception as e:
            messagebox.showerror("Agent run", f"Failed to run Agent1: {e}")

    def agent_apply_tests(self) -> None:
        goal = simpledialog.askstring("Agent (WSL) Apply+Tests", "Enter goal for apply+tests:")
        if not goal:
            return
        agent_id_s = simpledialog.askstring("Agent (WSL) Apply+Tests", "Agent ID (1..9):", initialvalue="1") or "1"
        try:
            agent_id = max(1, min(9, int(agent_id_s)))
        except Exception:
            agent_id = 1
        extra = simpledialog.askstring("Agent (WSL) Apply+Tests", "Extra args (optional):", initialvalue="") or ""
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                f"python tools/agent_runner.py --goal \"{goal.replace('\\', ' ').replace('"', '\\"')}\" --agent-id {agent_id} --run-tests --apply {extra}"
            )
            _wsl(cmd)
            self._log("Agent (WSL) Apply+Tests invoked.")
        except Exception as e:
            messagebox.showerror("Agent run", f"Failed to run apply+tests: {e}")

    def open_indicator(self) -> None:
        try:
            _run_py(["Scripts\\agent_indicator.py", "--auto-close", "--top"]) 
            self._log("Indicator popup launched.")
        except Exception as e:
            messagebox.showerror("Indicator", f"Failed to launch indicator: {e}")

    def open_dock(self) -> None:
        try:
            _run_py(["Scripts\\agent_dock.py", "--top"]) 
            self._log("Dock launched.")
        except Exception as e:
            messagebox.showerror("Dock", f"Failed to launch dock: {e}")

    def wsl_deps_pip(self) -> None:
        try:
            self._busy_start("Installing WSL pip dependencies…")
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "$PY -m pip install --upgrade pip && $PY -m pip install -r requirements.txt sounddevice pytest"
            )
            _wsl(cmd)
            self._log("WSL pip deps install started.")
        except Exception as e:
            messagebox.showerror("WSL deps", f"Failed to start pip deps install: {e}")
        finally:
            self._busy_end()

    def wsl_deps_apt(self) -> None:
        try:
            cmd = (
                "sudo -n apt-get update -y && "
                "sudo -n apt-get install -y libportaudio2 libsndfile1 || echo 'Note: sudo password required to install system libs.'"
            )
            _wsl(cmd)
            self._log("WSL apt libs install started.")
        except Exception as e:
            messagebox.showerror("WSL libs", f"Failed to start apt install: {e}")

    def start_digestors(self) -> None:
        try:
            self._busy_start("Starting digestors…")
            # Start 3 background loops for agent IDs 2,3,4
            for agent_id in (2, 3, 4):
                cmd = (
                    "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                    "cd /mnt/c/Calyx_Terminal && "
                    "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                    f"nohup $PY -u tools/agent_digestor.py --agent-id {agent_id} --poll-sec 2 --max-files 3 > /dev/null 2>&1 &"
                )
                _wsl(cmd)
            self._log("Digestors (2–4) started in background.")
        except Exception as e:
            messagebox.showerror("Digestors", f"Failed to start digestors: {e}")
        finally:
            self._busy_end()

    def stop_digestors(self) -> None:
        try:
            _wsl("pkill -f tools/agent_digestor.py || true")
            self._log("Digestors stop signal sent (WSL pkill).")
        except Exception as e:
            messagebox.showerror("Digestors", f"Failed to stop digestors: {e}")

    def start_agent1_scheduler(self) -> None:
        try:
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "nohup $PY -u tools/agent_scheduler.py --interval 180 --auto-promote --promote-after 5 --cooldown-mins 30 > /dev/null 2>&1 &"
            )
            _wsl(cmd)
            self._log("Agent1 scheduler started in background.")
        except Exception as e:
            messagebox.showerror("Agent1", f"Failed to start scheduler: {e}")

    def stop_agent1_scheduler(self) -> None:
        try:
            _wsl("pkill -f tools/agent_scheduler.py || true")
            self._log("Agent1 scheduler stop signal sent.")
        except Exception as e:
            messagebox.showerror("Agent1", f"Failed to stop scheduler: {e}")

    def agent1_bus_ping(self) -> None:
        try:
            self._busy_start("Seeding bus with last run…")
            # Publish the most recent agent_run_* as a bus message without invoking the LLM.
            cmd = (
                "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                "cd /mnt/c/Calyx_Terminal && "
                "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                "$PY -u tools/bus_ping_last_run.py"
            )
            _wsl(cmd)
            self._log("Bus ping of last run invoked (no LLM).")
        except Exception as e:
            messagebox.showerror("Agent1", f"Failed to run bus ping: {e}")
        finally:
            self._busy_end()

    # Feeder controls
    def start_feeders(self) -> None:
        try:
            self._busy_start("Starting feeders…")
            # Three feeder schedulers with fast intervals and shared LLM token
            feeders = [
                ("agent1a", 30),
                ("agent1b", 30),
                ("agent1c", 30),
            ]
            for name, interval in feeders:
                cmd = (
                    "if [ -f ~/.calyx-venv/bin/activate ]; then source ~/.calyx-venv/bin/activate; fi; "
                    "cd /mnt/c/Calyx_Terminal && "
                    "PY=python; command -v $PY >/dev/null 2>&1 || PY=python3; "
                    # Fast micro-tasks: max-steps=1, skip patches, publish bus, shared LLM token
                    f"nohup $PY -u tools/agent_scheduler.py --interval {interval} "
                    f"--heartbeat-name {name} --agent-id 1 --agent-args '--skip-patches --max-steps 1 --publish-bus --heartbeat-name {name} --llm-token llm_shared --llm-wait-sec 45 --llm-optional' > /dev/null 2>&1 &"
                )
                _wsl(cmd)
            self._log("Feeder schedulers (agent1a/b/c) started.")
        except Exception as e:
            messagebox.showerror("Feeders", f"Failed to start feeders: {e}")
        finally:
            self._busy_end()

    def stop_feeders(self) -> None:
        try:
            _wsl("pkill -f tools/agent_scheduler.py || true")
            self._log("Feeder schedulers stop signal sent.")
        except Exception as e:
            messagebox.showerror("Feeders", f"Failed to stop feeders: {e}")

    def start_feeders_and_digestors(self) -> None:
        try:
            self._busy_start("Starting feeders and digestors…")
            self.start_feeders()
            # Give a brief moment before spinning up digestors
            self.win.after(300, lambda: self.start_digestors())
            self._log("Started feeders and scheduled digestors start.")
        except Exception as e:
            messagebox.showerror("Start All", f"Failed to start feeders + digestors: {e}")
        finally:
            self._busy_end()

    # Status polling
    def _tick(self) -> None:
        try:
            t = _read_json(OUT / "triage.lock") or {}
            a = _read_json(OUT / "agent1.lock") or {}
            self._render_status("triage", t, self.triage_lbl, self.triage_details)
            self._render_status("agent1", a, self.agent_lbl, self.agent_details)
            a2 = _read_json(OUT / "agent2.lock") or {}
            self._render_status("agent2", a2, self.agent2_lbl, self.agent2_details)
            a3 = _read_json(OUT / "agent3.lock") or {}
            self._render_status("agent3", a3, self.agent3_lbl, self.agent3_details)
            a4 = _read_json(OUT / "agent4.lock") or {}
            self._render_status("agent4", a4, self.agent4_lbl, self.agent4_details)
            # Feeders
            fa = _read_json(OUT / "agent1a.lock") or {}
            self._render_status("agent1a", fa, self.agent1a_lbl, self.agent1a_details)
            fb = _read_json(OUT / "agent1b.lock") or {}
            self._render_status("agent1b", fb, self.agent1b_lbl, self.agent1b_details)
            fc = _read_json(OUT / "agent1c.lock") or {}
            self._render_status("agent1c", fc, self.agent1c_lbl, self.agent1c_details)
            # Auto-activation loop
            if self.auto_activate_var.get():
                self._try_auto_activate()
        except Exception:
            pass
        self.win.after(1000, self._tick)

    def _render_status(self, name: str, data: Dict[str, Any], lbl: ttk.Label, details_lbl: ttk.Label) -> None:
        status = str(data.get("status", "idle"))
        phase = str(data.get("phase", "—"))
        ts = data.get("ts")
        ago = "—"
        if ts:
            try:
                d = max(0.0, time.time() - float(ts))
                ago = f"{int(d)}s ago"
            except Exception:
                pass
        lbl.config(text=f"{phase} | {status} | {ago}")
        parts = []
        if name == "triage":
            p = data.get("probe")
            if isinstance(p, dict):
                last = p.get("last") or {}
                ok = last.get("ok")
                lat = last.get("latency_ms")
                be = p.get("backend") or data.get("backend")
                mid = p.get("model_id") or data.get("model_id")
                mode = p.get("mode")
                nx = p.get("next_in_sec")
                parts.append(f"probe: ok={ok} lat={lat}ms mode={mode} next~{nx}s model={mid} be={be}")
        if name in ("agent1", "agent2", "agent3", "agent4", "agent1a", "agent1b", "agent1c"):
            sm = data.get("status_message") or data.get("goal_preview")
            if sm:
                parts.append(sm)
        rd = data.get("run_dir")
        if rd:
            parts.append(f"run: {rd}")
        details_lbl.config(text="  •  ".join([str(x) for x in parts if x]))

    def run(self) -> None:
        self.win.mainloop()

    # Busy UI helpers
    def _set_buttons_state(self, state: str) -> None:
        for b in [
            getattr(self, 'btn_start_feeders', None),
            getattr(self, 'btn_start_all', None),
            getattr(self, 'btn_stop_feeders', None),
            getattr(self, 'btn_start_digestors', None),
            getattr(self, 'btn_stop_digestors', None),
        ]:
            try:
                if b is not None:
                    b.config(state=state)
            except Exception:
                pass

    def _busy_start(self, msg: str) -> None:
        try:
            self.action_status.config(text=msg)
            self._set_buttons_state('disabled')
            self.action_prog.start(50)
        except Exception:
            pass

    def _busy_end(self) -> None:
        try:
            self.action_prog.stop()
            self._set_buttons_state('normal')
            self.action_status.config(text='Ready')
        except Exception:
            pass


def main(argv: Optional[list[str]] = None) -> int:
    try:
        app = LauncherApp()
        app.run()
        return 0
    except Exception as e:
        # Log to file and show a dialog so pythonw users see the error.
        import traceback
        log_path = OUT / "agent_launcher.log"
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("\n")
                traceback.print_exc(file=f)
                f.write("\n")
        except Exception:
            pass
        _fallback_messagebox(
            "Calyx Agent Launcher",
            f"Failed to start launcher: {e}\n\nSee log: {log_path}\nTip: Run in a console to see details:\n  python -u Scripts\\agent_launcher.py",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
