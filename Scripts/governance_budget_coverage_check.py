#!/usr/bin/env python3
"""
WO_GOVERNANCE_BUDGET_COVERAGE_GUARANTEE_V2 — Invariant verification.
For every corr_id with human.request.received AND response.finalized:
  exactly one budget.request.recorded AND exactly one matching JSONL line.
Exit: 0=full coverage, 1=violation, 2=insufficient data, 3=script error.
Usage: python Scripts/governance_budget_coverage_check.py [--since-minutes N]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _resolve_repo_root() -> Path:
    env_root = __import__("os").environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[1]


def _parse_ts(ts_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Governance budget coverage invariant check")
    ap.add_argument("--since-minutes", type=int, default=60, help="Time window (default 60)")
    ap.add_argument("--corr-ids-file", help="Only check these corr_ids (one per line)")
    args = ap.parse_args()

    repo = _resolve_repo_root()
    ledger_dir = repo / "runtime" / "ledger"
    budget_dir = repo / "runtime" / "receipts" / "budget"

    if not ledger_dir.exists():
        print("Ledger dir missing", file=sys.stderr)
        return 2

    scope_corr_ids: set[str] | None = None
    if args.corr_ids_file:
        p = Path(args.corr_ids_file)
        if p.exists():
            scope_corr_ids = {ln.strip() for ln in p.read_text().splitlines() if ln.strip()}

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.since_minutes)

    # Collect events by corr_id
    human_received: set[str] = set()
    response_finalized: set[str] = set()
    budget_recorded: dict[str, int] = {}  # corr_id -> count
    budget_recorded_data: dict[str, dict] = {}  # corr_id -> data

    for p in sorted(ledger_dir.glob("station_events__*.jsonl"), reverse=True):
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                ts = _parse_ts(rec.get("ts", ""))
                if ts and ts < cutoff:
                    continue
                cid = (rec.get("corr_id") or rec.get("data", {}).get("corr_id") or "").strip()
                if not cid:
                    continue
                ev = rec.get("event", "")
                if ev == "human.request.received":
                    human_received.add(cid)
                elif ev == "response.finalized":
                    response_finalized.add(cid)
                elif ev == "budget.request.recorded":
                    budget_recorded[cid] = budget_recorded.get(cid, 0) + 1
                    budget_recorded_data[cid] = rec.get("data", {})
        except Exception as e:
            print(f"Ledger read error {p}: {e}", file=sys.stderr)
            return 3

    # Load budget JSONL for matching (only lines in window)
    budget_lines_by_corr: dict[str, list[str]] = {}
    for p in sorted(budget_dir.glob("governance_budget__*.jsonl")):
        if not p.exists():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                ts = _parse_ts(rec.get("ts_utc", ""))
                if ts and ts < cutoff:
                    continue
                cid = (rec.get("corr_id") or "").strip()
                if cid:
                    budget_lines_by_corr.setdefault(cid, []).append(line)
        except Exception as e:
            print(f"Budget JSONL read error {p}: {e}", file=sys.stderr)
            return 3

    # Invariant check
    violations: list[str] = []
    checked = 0
    passed = 0

    check_ids = (human_received & scope_corr_ids) if scope_corr_ids else human_received
    for cid in check_ids:
        has_finalized = cid in response_finalized
        budget_count = budget_recorded.get(cid, 0)
        jsonl_count = len(budget_lines_by_corr.get(cid, []))

        if has_finalized:
            checked += 1
            if budget_count != 1:
                violations.append(f"{cid}: response.finalized but budget.request.recorded count={budget_count} (expected 1)")
            elif jsonl_count != 1:
                violations.append(f"{cid}: budget.request.recorded but JSONL lines={jsonl_count} (expected 1)")
            else:
                passed += 1
        else:
            if budget_count > 0 or jsonl_count > 0:
                violations.append(f"{cid}: no response.finalized but budget exists")

    # Orphan: budget JSONL line in window without response.finalized (only if in scope)
    for cid in budget_lines_by_corr:
        if scope_corr_ids and cid not in scope_corr_ids:
            continue
        if cid not in response_finalized:
            violations.append(f"{cid}: orphan budget line (no response.finalized)")

    if violations:
        for v in violations:
            print(f"VIOLATION: {v}", file=sys.stderr)
        return 1

    if checked == 0:
        print("No governed requests with response.finalized in window (insufficient data)", file=sys.stderr)
        return 2

    print(f"Coverage OK: {passed}/{checked} governed requests have exactly one budget record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
