#!/usr/bin/env python3
"""
CLI entry point for Calyx Governance Benchmark.
Delegates to benchmarks.harness.runner.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root on PYTHONPATH for benchmarks package
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from benchmarks.harness.runner import main

if __name__ == "__main__":
    main()
