#!/usr/bin/env python3
"""
WO_AUDIT_QUERY_TOOLING_V1 — Find and summarize audit anomalies in the ledger.
Usage: python Scripts/audit_anomalies.py --since-minutes N [--context N]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


ANOMALY_EVENTS = frozenset({
    "audit.context.missing",
    "audit.context.ambiguous",
    "audit.context.invalid_system_action",
    "budget.violation",
    "governance.assertion.failed",
})


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


def _iter_ledger_lines(ledger_dir: Path, since_minutes: int) -> list[tuple[Path, int, str, dict]]:
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


def _format_line(rec: dict) -> str:
    """Compact single-line format."""
    ts = (rec.get("ts") or rec.get("ts_utc") or "")[:19]
    level = (rec.get("level") or "INFO")[:5]
    comp = rec.get("component") or "?"
    ev = rec.get("event") or "?"
    msg = (rec.get("msg") or "")[:60]
    env = rec.get("causal_envelope") or {}
    kind = env.get("causal_kind", "?")
    return f"  {ts} {level} {comp} {ev} {msg}  [{kind}]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Find audit anomalies in ledger")
    parser.add_argument("--since-minutes", type=int, default=60, help="Time window (default 60)")
    parser.add_argument("--context", type=int, default=10, help="Lines before/after each anomaly (default 10)")
    args = parser.parse_args()

    ledger_dir = _resolve_ledger_dir()
    if not ledger_dir.exists():
        print(f"Ledger dir missing: {ledger_dir}", file=sys.stderr)
        return 1

    lines = _iter_ledger_lines(ledger_dir, args.since_minutes)
    indexed: list[tuple[Path, int, str, dict]] = lines

    anomaly_indices: list[int] = []
    for i, (_, _, _, rec) in enumerate(indexed):
        ev = rec.get("event", "")
        if ev in ANOMALY_EVENTS:
            anomaly_indices.append(i)

    if not anomaly_indices:
        print(f"No anomalies in last {args.since_minutes} minutes")
        return 0

    print(f"Found {len(anomaly_indices)} anomaly(ies) in last {args.since_minutes} minutes\n")
    n = len(indexed)

    for idx in anomaly_indices:
        _, _, _, rec = indexed[idx]
        ts = rec.get("ts") or rec.get("ts_utc") or ""
        comp = rec.get("component") or "?"
        ev = rec.get("event") or "?"
        msg = rec.get("msg") or ""
        env = rec.get("causal_envelope") or {}
        env_str = json.dumps(env, ensure_ascii=False)[:80] + ("..." if len(json.dumps(env)) > 80 else "")

        print("-" * 70)
        print(f"ANOMALY: {ts} | {comp} | {ev}")
        print(f"  msg: {msg[:200]}")
        print(f"  causal_envelope: {env_str if env else 'missing'}")
        print()
        print("  Context (before):")
        start = max(0, idx - args.context)
        for j in range(start, idx):
            print(_format_line(indexed[j][3]))
        print("  >>> ANOMALY <<<")
        print(_format_line(rec))
        print("  Context (after):")
        end = min(n, idx + args.context + 1)
        for j in range(idx + 1, end):
            print(_format_line(indexed[j][3]))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
