#!/usr/bin/env python3
"""Bootstrap Station Calyx services in a known-good order."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import psutil

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
GPU_PY = ROOT / "venvs" / "calyx-gpu" / "Scripts" / "python.exe"


@dataclass(slots=True)
class Service:
    name: str
    args: List[str]
    cwd: Path = ROOT


SERVICES: List[Service] = [
    Service("cbo.bridge_overseer", [PYTHON, "-m", "calyx.cbo.bridge_overseer"]),
    Service("cbo.api", [PYTHON, "-m", "calyx.cbo.api"]),
    Service("agent_scheduler", [PYTHON, "-u", "tools/agent_scheduler.py", "--interval", "240"]),
    Service(
        "agent_scheduler_agent2",
        [
            PYTHON,
            "-u",
            "tools/agent_scheduler.py",
            "--agent-id",
            "2",
            "--interval",
            "300",
            "--heartbeat-name",
            "agent2",
            "--auto-promote",
            "--adaptive-backoff",
        ],
    ),
    Service("cp6_sociologist", [PYTHON, "-u", "tools/cp6_sociologist.py", "--interval", "60"]),
    Service("cp7_chronicler", [PYTHON, "-u", "tools/cp7_chronicler.py", "--interval", "60"]),
    Service("agent_cp8", [PYTHON, "Scripts/agent_cp8.py", "--interval", "60"]),
    Service("agent_cp9", [PYTHON, "Scripts/agent_cp9.py", "--interval", "60"]),
    Service(
        "ai4all_teaching",
        [
            str(GPU_PY if GPU_PY.exists() else Path(PYTHON)),
            "Projects/AI_for_All/ai4all_teaching.py",
            "--start",
        ],
    ),
    Service("sys_integrator", [PYTHON, "-u", "tools/sys_integrator.py", "--interval", "30"]),
]


def is_running(service: Service) -> bool:
    target = service.args[1:]
    for proc in psutil.process_iter(["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        # Compare tail of command line ignoring python executable differences
        if len(cmdline) >= len(target) and cmdline[-len(target):] == target:
            return True
    return False


def start_service(service: Service) -> None:
    if is_running(service):
        print(f"[skip] {service.name} already running", flush=True)
        return
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        service.args,
        cwd=str(service.cwd),
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[start] {service.name}", flush=True)


def main() -> int:
    for service in SERVICES:
        start_service(service)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
