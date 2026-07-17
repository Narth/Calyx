#!/usr/bin/env python3
"""
WO_AUDIT_QUERY_TOOLING_V1 — Trace ledger events by corr_id or task_corr_id.
Usage:
  python Scripts/audit_trace.py --corr-id <id>
  python Scripts/audit_trace.py --task-corr-id <id>
  python Scripts/audit_trace.py --corr-id <id> --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
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


def _parse_ts(ts_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _iter_ledger_lines(ledger_dir: Path, since_minutes: int = 1440) -> list[tuple[Path, int, str, dict]]:
    """Yield (path, line_num, raw_line, rec) for lines in time window. Sorted by ts ascending."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    results: list[tuple[datetime, Path, int, str, dict]] = []
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        if not p.exists():
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _parse_ts(rec.get("ts", "") or rec.get("ts_utc", ""))
                if ts and ts < cutoff:
                    continue
                results.append((ts or datetime.min.replace(tzinfo=timezone.utc), p, i, line, rec))
        except Exception:
            continue
    results.sort(key=lambda x: x[0])
    return [(p, ln, raw, rec) for _, p, ln, raw, rec in results]


def _matches_corr_id(rec: dict, target: str) -> bool:
    """Check if record belongs to corr_id (human path)."""
    target = (target or "").strip()
    if not target:
        return False
    cid = rec.get("corr_id") or (rec.get("causal_envelope") or {}).get("corr_id") or (rec.get("data") or {}).get("corr_id") or ""
    return cid and (cid == target or cid.startswith(target) or target.startswith(cid))


def _matches_task_corr_id(rec: dict, target: str) -> bool:
    """Check if record belongs to task_corr_id."""
    target = (target or "").strip()
    if not target:
        return False
    tid = (rec.get("causal_envelope") or {}).get("task_corr_id") or (rec.get("data") or {}).get("task_corr_id") or ""
    return tid and (tid == target or tid.startswith(target) or target.startswith(tid))


def _compact_envelope(rec: dict) -> str:
    """Compact view of causal_envelope."""
    env = rec.get("causal_envelope") or {}
    kind = env.get("causal_kind")
    if kind == "human":
        cid = env.get("corr_id", "")[:16]
        am = env.get("auth_mode", "?")
        return f"human corr={cid}... auth={am}"
    if kind == "task":
        tid = env.get("task_corr_id", "")[:16]
        tname = env.get("task_name", "?")
        return f"task tid={tid}... name={tname}"
    if kind == "system":
        phase = env.get("system_phase", "?")
        return f"system phase={phase}"
    if kind == "missing":
        return "missing"
    cid = rec.get("corr_id") or env.get("corr_id")
    tid = env.get("task_corr_id")
    if cid:
        return f"legacy corr={str(cid)[:16]}..."
    if tid:
        return f"legacy task={str(tid)[:16]}..."
    return "?"


def _format_human(rec: dict) -> str:
    """Single-line human-legible format."""
    ts = (rec.get("ts") or rec.get("ts_utc") or "")[:19]
    level = (rec.get("level") or "INFO")[:5].ljust(5)
    comp = (rec.get("component") or "?")[:16].ljust(16)
    ev = (rec.get("event") or "?")[:36].ljust(36)
    msg = (rec.get("msg") or "")[:50]
    env = _compact_envelope(rec)
    return f"{ts} {level} {comp} {ev} {msg}  [{env}]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace ledger events by corr_id or task_corr_id")
    parser.add_argument("--corr-id", help="Human request corr_id to trace")
    parser.add_argument("--task-corr-id", help="System task task_corr_id to trace")
    parser.add_argument("--json", action="store_true", help="Output raw JSON lines")
    parser.add_argument("--since-minutes", type=int, default=1440, help="Scan window (default 1440=24h)")
    args = parser.parse_args()

    if not args.corr_id and not args.task_corr_id:
        print("Specify --corr-id or --task-corr-id", file=sys.stderr)
        return 2

    ledger_dir = _resolve_ledger_dir()
    if not ledger_dir.exists():
        print(f"Ledger dir missing: {ledger_dir}", file=sys.stderr)
        return 1

    lines = _iter_ledger_lines(ledger_dir, args.since_minutes)
    matched: list[tuple[Path, int, str, dict]] = []

    for p, ln, raw, rec in lines:
        if args.corr_id and _matches_corr_id(rec, args.corr_id):
            matched.append((p, ln, raw, rec))
        elif args.task_corr_id and _matches_task_corr_id(rec, args.task_corr_id):
            matched.append((p, ln, raw, rec))

    if not matched:
        id_val = args.corr_id or args.task_corr_id
        print(f"No events found for {id_val} in last {args.since_minutes} minutes", file=sys.stderr)
        return 1

    for p, ln, raw, rec in matched:
        if args.json:
            print(raw)
        else:
            print(_format_human(rec))

    return 0


if __name__ == "__main__":
    sys.exit(main())
