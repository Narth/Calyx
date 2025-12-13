#!/usr/bin/env python3
"""Telemetry Smoke

A tiny helper to run bounded telemetry components end-to-end (Windows-friendly).

Usage:
  python -u tools/telemetry_smoke.py

What it does:
- Runs uptime_tracker for 2 snapshots
- Runs enhanced_metrics_collector once
- Runs bridge_pulse_scheduler for 1 pulse
- Runs telemetry_sentinel for 2 iterations
- Runs telemetry_gap_reconstructor once
- Writes a continuity report
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> None:
    subprocess.run(args, cwd=str(ROOT), check=False)


def main() -> int:
    py = sys.executable

    _run([py, "-u", str(ROOT / "tools" / "uptime_tracker.py"), "--interval", "1", "--max-iters", "2"])
    _run([py, "-u", str(ROOT / "tools" / "enhanced_metrics_collector.py"), "--interval", "1", "--once"])
    _run([
        py,
        "-u",
        str(ROOT / "tools" / "bridge_pulse_scheduler.py"),
        "--pulse-interval",
        "20",
        "--max-iters",
        "1",
    ])
    _run([py, "-u", str(ROOT / "tools" / "telemetry_sentinel.py"), "--interval", "1", "--max-iters", "2"])
    _run([py, "-u", str(ROOT / "tools" / "telemetry_gap_reconstructor.py"), "--once"])
    _run([
        py,
        "-u",
        str(ROOT / "tools" / "telemetry_continuity_report.py"),
        "--output",
        str(ROOT / "reports" / "telemetry_continuity.md"),
    ])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
