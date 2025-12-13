#!/usr/bin/env python3
"""Set coordinator autonomy mode with backup.

Usage: python -u tools/set_autonomy_mode.py guide
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Usage: set_autonomy_mode.py <mode>")
        return 2
    mode = argv[0]
    root = Path(__file__).resolve().parents[1]
    state_path = root / "state" / "coordinator_state.json"
    if not state_path.exists():
        print("state file missing:", state_path)
        return 3
    bak = root / "state" / f"coordinator_state.json.bak.{int(__import__('time').time())}"
    shutil.copy2(state_path, bak)
    # Import local StateCore
    sys.path.insert(0, str(root))
    try:
        from calyx.cbo.coordinator.state_core import StateCore
    except Exception as e:
        print("Failed to import StateCore:", e)
        return 4
    s = StateCore(root)
    before = s.get_autonomy_mode()
    s.set_autonomy_mode(mode)
    after = s.get_autonomy_mode()
    print(f"backup: {bak}")
    print(f"autonomy before: {before}")
    print(f"autonomy after: {after}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
