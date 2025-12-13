#!/usr/bin/env python3
"""
SVF utility helpers.

- ensure_svf_running: checks outgoing/svf.lock and starts svf_probe in background if missing or stale.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
SVF_LOCK = OUT / "svf.lock"


def _is_fresh(path: Path, grace_sec: float = 15.0) -> bool:
    try:
        if not path.exists():
            return False
        mtime = path.stat().st_mtime
        return (time.time() - mtime) <= grace_sec
    except Exception:
        return False


def ensure_svf_running(grace_sec: float = 15.0, interval: float = 5.0, emit_sample: bool = False) -> bool:
    """Ensure the Shared Voice Probe is active.

    Returns True if we started it in this call; False if already fresh or failed to start.
    """
    if _is_fresh(SVF_LOCK, grace_sec=grace_sec):
        return False
    # Start background svf_probe
    tool = ROOT / "tools" / "svf_probe.py"
    args = [sys.executable, "-u", str(tool), "--interval", str(interval)]
    if emit_sample:
        args.append("--emit-sample")
    try:
        if os.name == "nt":
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(args, creationflags=DETACHED_PROCESS, close_fds=True)
        else:
            subprocess.Popen(args, start_new_session=True, close_fds=True)
        # Give it a moment to write the first heartbeat
        time.sleep(0.2)
        return True
    except Exception:
        return False
