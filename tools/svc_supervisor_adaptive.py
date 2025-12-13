#!/usr/bin/env python3
"""
Adaptive Service Supervisor (Windows-first)
===========================================

This module replaces the corrupted legacy implementation.  The goal is to keep
the essential Calyx background services alive while being lightweight, easy to
reason about, and resilient to partial failures.  The behaviour is intentionally
conservative:

* Windows processes are spawned directly using ``subprocess.Popen``.
* WSL processes can be launched when WSL is available; otherwise the supervisor
  silently falls back to running the Windows variant.
* Heartbeats are considered fresh when their modification timestamp is no older
  than ``grace = max(10, interval * 2)``.
* Dynamic overrides written by ``cbo_optimizer`` are supported (interval tweaks
  for navigator and scheduler).

The supervisor is typically invoked via VS Code tasks or PowerShell:
    python -u tools/svc_supervisor_adaptive.py --interval 60 --include-scheduler
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, Optional


_SINGLE_INSTANCE_MUTEX_HANDLE = None


def _acquire_single_instance_mutex(name: str) -> bool:
    """Acquire a best-effort global single-instance guard on Windows.

    Returns True if this process should proceed, False if another instance
    appears to already be running.
    """

    global _SINGLE_INSTANCE_MUTEX_HANDLE

    if os.name != "nt":
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32

        CreateMutexW = kernel32.CreateMutexW
        CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        CreateMutexW.restype = ctypes.c_void_p

        GetLastError = kernel32.GetLastError
        GetLastError.argtypes = []
        GetLastError.restype = ctypes.c_uint32

        ERROR_ALREADY_EXISTS = 183

        handle = CreateMutexW(None, True, name)
        if not handle:
            # If we can't acquire a mutex, fail open (best-effort) so we don't
            # accidentally prevent stewardship.
            return True

        last_error = int(GetLastError())
        if last_error == ERROR_ALREADY_EXISTS:
            return False

        _SINGLE_INSTANCE_MUTEX_HANDLE = handle
        return True
    except Exception:
        # Best-effort only.
        return True

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"
LOGS = ROOT / "logs"
TUNING = OUTGOING / "tuning"

LOCK_SVF = OUTGOING / "svf.lock"
LOCK_TRIAGE = OUTGOING / "triage.lock"
LOCK_SYSINT = OUTGOING / "sysint.lock"
LOCK_NAVIGATOR = OUTGOING / "navigator.lock"
LOCK_SCHEDULER = OUTGOING / "scheduler.lock"
LOCK_UPTIME = OUTGOING / "uptime_tracker.lock"
LOCK_ENHANCED_METRICS = OUTGOING / "enhanced_metrics.lock"
LOCK_BRIDGE_PULSE_SCHED = OUTGOING / "bridge_pulse_scheduler.lock"
LOCK_TELEMETRY_SENTINEL = OUTGOING / "telemetry_sentinel.lock"
STATE_PHM = ROOT / "state" / "proactive_health_state.json"
HEARTBEATS_MD = LOGS / "HEARTBEATS.md"

GATE_GPU = OUTGOING / "gates" / "gpu.ok"
POLICY_CBO = OUTGOING / "policies" / "cbo_permissions.json"
OVERRIDES = TUNING / "supervisor_overrides.json"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _is_wsl_available() -> bool:
    """Best-effort detection for WSL readiness."""
    try:
        ping = subprocess.run(
            ["wsl", "bash", "-lc", "echo ok"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if ping.returncode != 0:
            return False
        env_check = subprocess.run(
            ["wsl", "bash", "-lc", "test -d ~/.calyx-venv"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return env_check.returncode == 0
    except Exception:
        return False


def _heartbeat_fresh(path: Path, grace: float) -> bool:
    try:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age <= grace
    except Exception:
        return False


def _load_overrides() -> Dict[str, Dict[str, int]]:
    try:
        if not OVERRIDES.exists():
            return {}
        data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        return {
            "navigator": {
                "interval": int(data.get("navigator", {}).get("interval", 3)),
                "pause_sec": int(data.get("navigator", {}).get("pause_sec", 90)),
                "hot_interval": int(data.get("navigator", {}).get("hot_interval", 90)),
                "cool_interval": int(data.get("navigator", {}).get("cool_interval", 20)),
                "control": bool(data.get("navigator", {}).get("control", False)),
            },
            "scheduler": {
                "interval": int(data.get("scheduler", {}).get("interval", 180)),
                "include": bool(data.get("scheduler", {}).get("include", False)),
            },
        }
    except Exception:
        return {}


def _gpu_ready() -> bool:
    if not GATE_GPU.exists():
        return False
    try:
        rc = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=2).returncode
        if rc == 0:
            return True
    except Exception:
        pass
    try:
        import torch  # type: ignore

        return torch.cuda.is_available()
    except Exception:
        return False


def _child_env() -> Dict[str, str]:
    env = dict(os.environ)
    if _gpu_ready():
        env["CBO_GPU_ALLOWED"] = "1"
        env["FASTER_WHISPER_DEVICE"] = "cuda"
        env["FASTER_WHISPER_COMPUTE_TYPE"] = "float16"
    return env


def _spawn_windows(args: Iterable[str]) -> subprocess.Popen:
    return subprocess.Popen(
        list(args),
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_child_env(),
    )


def _spawn_wsl(command: str) -> subprocess.Popen:
    wrapped = (
        "bash -lc "
        "\"source ~/.calyx-venv/bin/activate || true && "
        "cd /mnt/c/Calyx_Terminal && "
        f"{command} > /dev/null 2>&1 & disown\""
    )
    return subprocess.Popen(["wsl", wrapped], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# Supervision logic
# ---------------------------------------------------------------------------


class Supervisor:
    def __init__(
        self,
        *,
        check_interval: float,
        svf_interval: float,
        triage_interval: float,
        triage_probe_every: int,
        sysint_interval: float,
        navigator_interval: float,
        navigator_control: bool,
        nav_pause_sec: int,
        nav_hot_interval: int,
        nav_cool_interval: int,
        include_scheduler: bool,
        scheduler_interval: int,
        include_uptime_tracker: bool = False,
        uptime_interval: int = 60,
        include_enhanced_metrics: bool = False,
        enhanced_metrics_interval: int = 300,
        include_bridge_pulse_scheduler: bool = False,
        bridge_pulse_interval_mins: int = 20,
        bridge_pulse_heartbeat_only: bool = False,
        include_telemetry_sentinel: bool = False,
        telemetry_sentinel_interval: float = 60.0,
        include_phm: bool = True,
        phm_interval: float = 60.0,
    ) -> None:
        self.check_interval = float(check_interval)
        self.grace = max(10.0, self.check_interval * 2)
        self.svf_interval = float(svf_interval)
        self.triage_interval = float(triage_interval)
        self.triage_probe_every = int(triage_probe_every)
        self.sysint_interval = float(sysint_interval)
        self.navigator_interval = float(navigator_interval)
        self.navigator_control = bool(navigator_control)
        self.nav_pause_sec = int(nav_pause_sec)
        self.nav_hot_interval = int(nav_hot_interval)
        self.nav_cool_interval = int(nav_cool_interval)
        self.include_scheduler = bool(include_scheduler)
        self.scheduler_interval = int(scheduler_interval)
        self.include_uptime_tracker = bool(include_uptime_tracker)
        self.uptime_interval = int(uptime_interval)
        self.include_enhanced_metrics = bool(include_enhanced_metrics)
        self.enhanced_metrics_interval = int(enhanced_metrics_interval)
        self.include_bridge_pulse_scheduler = bool(include_bridge_pulse_scheduler)
        self.bridge_pulse_interval_mins = int(bridge_pulse_interval_mins)
        self.bridge_pulse_heartbeat_only = bool(bridge_pulse_heartbeat_only)
        self.include_telemetry_sentinel = bool(include_telemetry_sentinel)
        self.telemetry_sentinel_interval = float(telemetry_sentinel_interval)
        self.include_phm = bool(include_phm)
        self.phm_interval = float(phm_interval)
        self.use_wsl = _is_wsl_available()
        self.proc_refs: Dict[str, subprocess.Popen] = {}

    # ---- individual ensure methods -------------------------------------

    def _ensure_process(self, key: str, lock: Path, spawn_fn) -> None:
        stale = not _heartbeat_fresh(lock, self.grace)
        proc = self.proc_refs.get(key)
        exited = proc is not None and proc.poll() is not None
        if stale or exited or proc is None:
            if exited:
                try:
                    proc.wait(timeout=0.1)
                except Exception:
                    pass
            self.proc_refs[key] = spawn_fn()

    def ensure_svf(self) -> None:
        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "svf_probe.py"),
                    "--interval",
                    str(self.svf_interval),
                ]
            )

        self._ensure_process("svf", LOCK_SVF, spawn)

    def ensure_triage(self) -> None:
        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "triage_probe.py"),
                    "--interval",
                    str(self.triage_interval),
                    "--probe-every",
                    str(self.triage_probe_every),
                ]
            )

        self._ensure_process("triage", LOCK_TRIAGE, spawn)

    def ensure_sysint(self) -> None:
        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "sys_integrator.py"),
                    "--interval",
                    str(self.sysint_interval),
                ]
            )

        self._ensure_process("sysint", LOCK_SYSINT, spawn)

    def ensure_heartbeat(self) -> None:
        """Ensure the lightweight heartbeat writer is running.

        Uses logs/HEARTBEATS.md as the freshness indicator; if the file is
        missing or stale, a new writer process is spawned.
        """

        def spawn_windows():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "heartbeat_writer.py"),
                    "--interval",
                    "300",
                ]
            )

        # Prefer Windows spawn to match the rest of the adaptive supervisor.
        self._ensure_process("heartbeat", HEARTBEATS_MD, spawn_windows)

    def ensure_navigator(self, overrides: Dict[str, Dict[str, int]]) -> None:
        nav_override = overrides.get("navigator", {})
        nav_interval = nav_override.get("interval", self.navigator_interval)
        nav_pause = nav_override.get("pause_sec", self.nav_pause_sec)
        nav_hot = nav_override.get("hot_interval", self.nav_hot_interval)
        nav_cool = nav_override.get("cool_interval", self.nav_cool_interval)
        nav_control = nav_override.get("control", self.navigator_control)

        def spawn_windows():
            args = [
                sys.executable,
                "-u",
                str(ROOT / "tools" / "traffic_navigator.py"),
                "--interval",
                str(nav_interval),
            ]
            if nav_control:
                args += [
                    "--control",
                    "--pause-sec",
                    str(nav_pause),
                    "--hot-interval",
                    str(nav_hot),
                    "--cool-interval",
                    str(nav_cool),
                ]
            return _spawn_windows(args)

        def spawn_wsl():
            command_parts = [
                "python -u tools/traffic_navigator.py",
                f"--interval {nav_interval}",
            ]
            if nav_control:
                command_parts.append(f"--control --pause-sec {nav_pause} --hot-interval {nav_hot} --cool-interval {nav_cool}")
            command = " ".join(command_parts)
            return _spawn_wsl(command)

        spawn_fn = spawn_wsl if self.use_wsl else spawn_windows
        self._ensure_process("navigator", LOCK_NAVIGATOR, spawn_fn)

    def ensure_scheduler(self, overrides: Dict[str, Dict[str, int]]) -> None:
        if not self.include_scheduler:
            return

        sched_override = overrides.get("scheduler", {})
        include = sched_override.get("include", True)
        if not include:
            proc = self.proc_refs.pop("scheduler", None)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return

        interval = sched_override.get("interval", self.scheduler_interval)

        def spawn_windows():
            args = [
                sys.executable,
                "-u",
                str(ROOT / "tools" / "agent_scheduler.py"),
                "--interval",
                str(interval),
                "--mode",
                "apply_tests",
                "--agent-args",
                "--run-tests",
                "--adaptive-backoff",
                "--auto-promote",
                "--preflight-compile",
            ]
            return _spawn_windows(args)

        def spawn_wsl():
            command = (
                "python -u tools/agent_scheduler.py "
                f"--interval {interval} --mode apply_tests "
                "--agent-args \"--run-tests\" "
                "--adaptive-backoff --auto-promote --preflight-compile"
            )
            return _spawn_wsl(command)

        spawn_fn = spawn_wsl if self.use_wsl else spawn_windows
        self._ensure_process("scheduler", LOCK_SCHEDULER, spawn_fn)

    def ensure_phm(self) -> None:
        """Ensure Proactive Health Monitor is running."""
        if not self.include_phm:
            return

        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "Scripts" / "start_proactive_health_monitor.py"),
                ]
            )

        self._ensure_process("phm", STATE_PHM, spawn)

    def ensure_uptime_tracker(self) -> None:
        if not self.include_uptime_tracker:
            return

        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "uptime_tracker.py"),
                    "--interval",
                    str(self.uptime_interval),
                ]
            )

        self._ensure_process("uptime_tracker", LOCK_UPTIME, spawn)

    def ensure_enhanced_metrics(self) -> None:
        if not self.include_enhanced_metrics:
            return

        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "enhanced_metrics_collector.py"),
                    "--interval",
                    str(self.enhanced_metrics_interval),
                ]
            )

        self._ensure_process("enhanced_metrics", LOCK_ENHANCED_METRICS, spawn)

    def ensure_bridge_pulse_scheduler(self) -> None:
        if not self.include_bridge_pulse_scheduler:
            return

        def spawn():
            args = [
                sys.executable,
                "-u",
                str(ROOT / "tools" / "bridge_pulse_scheduler.py"),
                "--pulse-interval",
                str(self.bridge_pulse_interval_mins),
            ]
            if self.bridge_pulse_heartbeat_only:
                args.append("--heartbeat-only")
            return _spawn_windows(
                args
            )

        self._ensure_process("bridge_pulse_scheduler", LOCK_BRIDGE_PULSE_SCHED, spawn)

    def ensure_telemetry_sentinel(self) -> None:
        if not self.include_telemetry_sentinel:
            return

        def spawn():
            return _spawn_windows(
                [
                    sys.executable,
                    "-u",
                    str(ROOT / "tools" / "telemetry_sentinel.py"),
                    "--interval",
                    str(self.telemetry_sentinel_interval),
                ]
            )

        self._ensure_process("telemetry_sentinel", LOCK_TELEMETRY_SENTINEL, spawn)

    # ---- main loop -------------------------------------------------------

    def run(self) -> None:
        try:
            while True:
                overrides = _load_overrides()
                self.ensure_svf()
                self.ensure_triage()
                self.ensure_sysint()
                self.ensure_heartbeat()
                self.ensure_navigator(overrides)
                self.ensure_scheduler(overrides)
                self.ensure_uptime_tracker()
                self.ensure_enhanced_metrics()
                self.ensure_bridge_pulse_scheduler()
                self.ensure_telemetry_sentinel()
                self.ensure_phm()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            pass
        finally:
            for proc in self.proc_refs.values():
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                    except Exception:
                        pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Adaptive supervisor for core Calyx services.")
    parser.add_argument("--interval", type=float, default=60.0, help="Check interval seconds (default 60)")
    parser.add_argument("--svf-interval", type=float, default=5.0, help="SVF probe interval seconds")
    parser.add_argument("--triage-interval", type=float, default=2.0, help="Triage probe interval seconds")
    parser.add_argument("--triage-probe-every", type=int, default=15, help="Run triage probe every N loops")
    parser.add_argument("--sysint-interval", type=float, default=10.0, help="System integrator interval seconds")
    parser.add_argument("--navigator-interval", type=float, default=3.0, help="Navigator heartbeat interval")
    parser.add_argument("--navigator-control", action="store_true", help="Enable navigator control mode on Windows")
    parser.add_argument("--nav-pause-sec", type=int, default=90, help="Navigator pause duration when hot")
    parser.add_argument("--nav-hot-interval", type=int, default=90, help="Navigator hot interval (seconds)")
    parser.add_argument("--nav-cool-interval", type=int, default=20, help="Navigator cool interval (seconds)")
    parser.add_argument("--include-scheduler", action="store_true", help="Supervise agent scheduler")
    parser.add_argument("--scheduler-interval", type=int, default=180, help="Scheduler interval seconds")
    parser.add_argument("--include-uptime-tracker", action="store_true", help="Supervise uptime_tracker (system snapshots)")
    parser.add_argument("--uptime-interval", type=int, default=60, help="Uptime tracker snapshot interval seconds")
    parser.add_argument("--include-enhanced-metrics", action="store_true", help="Supervise enhanced_metrics_collector")
    parser.add_argument("--enhanced-metrics-interval", type=int, default=300, help="Enhanced metrics collection interval seconds")
    parser.add_argument("--include-bridge-pulse-scheduler", action="store_true", help="Supervise bridge_pulse_scheduler")
    parser.add_argument("--bridge-pulse-interval", type=int, default=20, help="Bridge pulse interval minutes")
    parser.add_argument(
        "--bridge-pulse-heartbeat-only",
        action="store_true",
        help="Run bridge pulse scheduler in heartbeat-only mode (no report generation)",
    )
    parser.add_argument("--include-telemetry-sentinel", action="store_true", help="Supervise telemetry_sentinel")
    parser.add_argument("--telemetry-sentinel-interval", type=float, default=60.0, help="Telemetry sentinel check interval seconds")
    parser.add_argument("--include-phm", action="store_true", default=True, help="Supervise proactive health monitor (default: True)")
    parser.add_argument("--no-phm", dest="include_phm", action="store_false", help="Disable proactive health monitor")
    parser.add_argument("--phm-interval", type=float, default=60.0, help="Proactive health monitor interval seconds")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    if not _acquire_single_instance_mutex("Global\\Calyx_SvcSupervisorAdaptive"):
        print("svc_supervisor_adaptive: already running; exiting.")
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    supervisor = Supervisor(
        check_interval=args.interval,
        svf_interval=args.svf_interval,
        triage_interval=args.triage_interval,
        triage_probe_every=args.triage_probe_every,
        sysint_interval=args.sysint_interval,
        navigator_interval=args.navigator_interval,
        navigator_control=args.navigator_control,
        nav_pause_sec=args.nav_pause_sec,
        nav_hot_interval=args.nav_hot_interval,
        nav_cool_interval=args.nav_cool_interval,
        include_scheduler=args.include_scheduler,
        scheduler_interval=args.scheduler_interval,
        include_uptime_tracker=args.include_uptime_tracker,
        uptime_interval=args.uptime_interval,
        include_enhanced_metrics=args.include_enhanced_metrics,
        enhanced_metrics_interval=args.enhanced_metrics_interval,
        include_bridge_pulse_scheduler=args.include_bridge_pulse_scheduler,
        bridge_pulse_interval_mins=args.bridge_pulse_interval,
        bridge_pulse_heartbeat_only=args.bridge_pulse_heartbeat_only,
        include_telemetry_sentinel=args.include_telemetry_sentinel,
        telemetry_sentinel_interval=args.telemetry_sentinel_interval,
        include_phm=args.include_phm,
        phm_interval=args.phm_interval,
    )
    supervisor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
