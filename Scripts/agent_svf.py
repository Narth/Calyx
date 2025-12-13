#!/usr/bin/env python3
"""
Agent launcher for SVF Probe — Shared Voice Protocol activation/monitor.

Usage:
  python -u Scripts/agent_svf.py --interval 5

This is a thin wrapper over tools/svf_probe.py to keep Scripts/ entrypoints consistent.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


essage = "Launch SVF Probe"

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=essage)
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--max-iters", type=int, default=0)
    p.add_argument("--emit-sample", action="store_true")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)
    # Forward args to the tool module via sys.argv
    tool = ROOT / "tools" / "svf_probe.py"
    sys.argv = [str(tool), "--interval", str(args.interval), "--max-iters", str(args.max_iters)] + (["--emit-sample"] if args.emit_sample else []) + (["--quiet"] if args.quiet else [])
    runpy.run_path(str(tool), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
