#!/usr/bin/env python3
"""
Windows-friendly runner for CP6 Sociologist.

Usage examples (PowerShell):
  python -u Scripts\cp6.py --interval 2 --max-iters 5
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "tools").resolve()))

from cp6_sociologist import main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(main())
