#!/usr/bin/env python3
"""
LLM Gate toggler: creates or removes outgoing/gates/llm.ok to grant/deny
LLM-enabled operations to agents (triage, runner, CBO, etc.).

Usage (Windows PowerShell):
    python -u tools/llm_gate.py --enable --note "manual"
    python -u tools/llm_gate.py --disable

The gate file is a small JSON with timestamp and optional note.
This script does not perform any network calls.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
GATES = OUT / "gates"
LLM_OK = GATES / "llm.ok"


def enable(note: str | None = None) -> None:
    GATES.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time()}
    if note:
        payload["note"] = str(note)[:200]
    LLM_OK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def disable() -> None:
    try:
        LLM_OK.unlink()
    except FileNotFoundError:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Toggle LLM gate file")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--enable", action="store_true", help="Create gates/llm.ok")
    g.add_argument("--disable", action="store_true", help="Remove gates/llm.ok")
    ap.add_argument("--note", type=str, default=None, help="Optional note recorded in the gate file")
    args = ap.parse_args(argv)

    if args.enable:
        enable(args.note)
        print("LLM gate enabled (gates/llm.ok)")
    else:
        disable()
        print("LLM gate disabled (gates/llm.ok removed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
