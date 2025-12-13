"""
Timed Network Burst helper
--------------------------
Temporarily enables the Network gate (outgoing/gates/network.ok) for a short
duration, then disables it again. Useful when you want to keep the system in
local-only mode but allow an occasional controlled egress window.

Usage (PowerShell):
  python -u tools\net_burst.py --minutes 3

Notes:
- Honors sitecustomize.py guardrails. This script only toggles the gate file.
- Does not set CALYX_ALLOW_NET; it relies solely on the gate file.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / "outgoing" / "gates"
NET_OK = GATES / "network.ok"


def enable_net() -> None:
    GATES.mkdir(parents=True, exist_ok=True)
    # Simple presence-only gate (contents not required)
    NET_OK.write_text("ok", encoding="utf-8")


def disable_net() -> None:
    try:
        NET_OK.unlink()
    except FileNotFoundError:
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Enable network for a limited time, then disable.")
    p.add_argument("--minutes", type=float, default=3.0, help="How long to allow network (default: 3 minutes)")
    p.add_argument("--quiet", action="store_true", help="Reduce console output")
    args = p.parse_args(argv)

    secs = max(0.0, float(args.minutes) * 60.0)
    if not args.quiet:
        print(f"[net-burst] Enabling network gate for {secs:.0f} sec…")
    enable_net()
    try:
        time.sleep(secs)
    finally:
        disable_net()
        if not args.quiet:
            print("[net-burst] Network gate disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
