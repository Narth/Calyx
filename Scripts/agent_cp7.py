#!/usr/bin/env python3
"""
Agent launcher for CP7 — The Chronicler.

Usage:
  python -u Scripts/agent_cp7.py --interval 5

This is a thin wrapper over tools/cp7_chronicler.py to keep Scripts/ entrypoints consistent.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Launch CP7 Chronicler")
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--max-iters", type=int, default=0)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)
    # Forward args to the tool module via sys.argv
    tool = ROOT / "tools" / "cp7_chronicler.py"
    sys.argv = [str(tool), "--interval", str(args.interval), "--max-iters", str(args.max_iters)] + (["--quiet"] if args.quiet else [])
    runpy.run_path(str(tool), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
