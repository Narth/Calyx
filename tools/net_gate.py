#!/usr/bin/env python3
"""
Network Gate toggler: creates or removes outgoing/gates/network.ok to permit
outbound network connections. With the gate absent, sitecustomize.py blocks
outbound sockets (except loopback if CALYX_ALLOW_LOOPBACK is set).

Usage (Windows PowerShell):
  python -u tools\net_gate.py --enable --note "manual"
  python -u tools\net_gate.py --disable
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
GATES = OUT / "gates"
NET_OK = GATES / "network.ok"

def enable(note: str | None = None) -> None:
    GATES.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time()}
    if note:
        payload["note"] = str(note)[:200]
    NET_OK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def disable() -> None:
    try:
        NET_OK.unlink()
    except FileNotFoundError:
        pass

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Toggle Network gate file")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--enable", action="store_true", help="Create gates/network.ok")
    g.add_argument("--disable", action="store_true", help="Remove gates/network.ok")
    ap.add_argument("--note", type=str, default=None, help="Optional note recorded in the gate file")
    args = ap.parse_args(argv)

    if args.enable:
        enable(args.note)
        print("Network gate enabled (gates/network.ok)")
    else:
        disable()
        print("Network gate disabled (gates/network.ok removed)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
