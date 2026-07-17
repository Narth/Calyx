#!/usr/bin/env python3
"""
Station Event Ledger tail — human-legible view. WO_STATION_EVENT_LEDGER_V1.
Usage: python Scripts/ledger_tail.py [--n 50] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _resolve_ledger_dir() -> Path:
    try:
        repo = Path(__file__).resolve().parents[1]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        from calyx.kernel.paths import resolve_ledger_dir
        return resolve_ledger_dir(repo)
    except ImportError:
        return Path.cwd() / "runtime" / "ledger"


def _find_latest_ledger(ledger_dir: Path) -> Path | None:
    """Return path to most recent station_events__YYYYMMDD.jsonl, or None."""
    if not ledger_dir.exists():
        return None
    files = sorted(ledger_dir.glob("station_events__*.jsonl"), reverse=True)
    return files[0] if files else None


def _format_human(rec: dict) -> str:
    """Single-line human-legible format."""
    ts = rec.get("ts", "")[:19]
    if "T" in ts:
        ts = ts.split("T")[1][:8]  # HH:MM:SS
    level = (rec.get("level") or "INFO")[:5].ljust(5)
    event = (rec.get("event") or "?")[:28].ljust(28)
    msg = (rec.get("msg") or "")[:60]
    data = rec.get("data") or {}
    extras = []
    if "corr_id" in rec and rec["corr_id"]:
        c = str(rec["corr_id"])[:8]
        extras.append(f"corr={c}…")
    if "inflight" in data:
        extras.append(f"inflight={data.get('inflight')}")
    if "cpu" in data:
        extras.append(f"cpu={data.get('cpu')}")
    if "size" in data:
        extras.append(f"size={data.get('size')}")
    if "reason" in data:
        extras.append(f"reason={data.get('reason')}")
    if "envelope_id" in data:
        extras.append(f"envelope_id={str(data.get('envelope_id',''))[:12]}…")
    if extras:
        msg = msg + " " + " ".join(extras) if msg else " ".join(extras)
    return f"{ts} {level} {event} {msg}".strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Tail Station Event Ledger (human-legible)")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines (default 50)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON lines")
    args = parser.parse_args()

    ledger_dir = _resolve_ledger_dir()
    path = _find_latest_ledger(ledger_dir)
    if not path or not path.exists():
        print("No ledger file found.", file=sys.stderr)
        return 1

    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    tail = lines[-args.lines :] if len(lines) > args.lines else lines

    for line in tail:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            print(line)
            continue
        if args.json:
            print(json.dumps(rec, ensure_ascii=False))
        else:
            print(_format_human(rec))

    return 0


if __name__ == "__main__":
    sys.exit(main())
