#!/usr/bin/env python3
"""
WO_CANONICAL_EQUIVALENCE_HASH_V2 — Cross-channel parity checker.
Reads response.equivalence_hash events; compares equivalence_hash (NOT receipt_hash).
Parity checks must never compare receipt hashes.
Exit: 0=equivalence matches, 1=mismatch, 2=insufficient data.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def resolve_repo_root() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    for anchor in [Path(__file__).resolve().parents[1], Path.cwd()]:
        for _ in range(10):
            if (anchor / ".git").exists() or (anchor / "cbo_hub").exists():
                return anchor
            anchor = anchor.parent
    return Path.cwd()


def main() -> int:
    ap = argparse.ArgumentParser(description="Canonical equivalence hash parity check")
    ap.add_argument("--corr-id", help="Filter by correlation ID")
    ap.add_argument("--since-minutes", type=int, default=60, help="Time window (default 60)")
    ap.add_argument("--ledger-dir", help="Override ledger directory")
    args = ap.parse_args()

    repo_root = resolve_repo_root()
    ledger_dir = Path(args.ledger_dir) if args.ledger_dir else repo_root / "runtime" / "ledger"
    if not ledger_dir.exists():
        print("Ledger directory not found:", ledger_dir, file=sys.stderr)
        return 2

    cutoff = None
    if args.since_minutes:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.since_minutes)

    def in_window(ts_str: str) -> bool:
        if not cutoff or not ts_str:
            return True
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return ts >= cutoff
        except ValueError:
            return True

    eq_events: list[dict] = []
    receipt_by_corr: dict[str, str] = {}
    for f in sorted(ledger_dir.glob("station_events__*.jsonl"), reverse=True)[:3]:
        try:
            for line in f.read_text(encoding="utf-8", errors="replace").strip().splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if args.corr_id and rec.get("corr_id") != args.corr_id:
                    continue
                if not in_window(rec.get("ts", "")):
                    continue
                ev = rec.get("event")
                data = rec.get("data") or {}
                if ev == "response.equivalence_hash":
                    eq_events.append(rec)
                elif ev == "response.canonical_hash":
                    cid = rec.get("corr_id", "")
                    rh = data.get("receipt_hash") or data.get("canonical_hash_sha256", "")
                    if cid and rh:
                        receipt_by_corr[cid] = rh
        except Exception as e:
            print(f"Warning: {f}: {e}", file=sys.stderr)

    if not eq_events:
        print("No response.equivalence_hash events found.", file=sys.stderr)
        return 2

    # Group by normalized_request_sha256
    groups: dict[str, list[dict]] = {}
    for e in eq_events:
        data = e.get("data") or {}
        key = data.get("normalized_request_sha256") or e.get("corr_id", "")
        if not key:
            key = e.get("corr_id", "")
        groups.setdefault(key, []).append(e)

    # Parity: compare equivalence_hash_sha256 (never receipt_hash)
    all_match = True
    for key, group in groups.items():
        eq_hashes = {e.get("data", {}).get("equivalence_hash_sha256", "") for e in group}
        eq_hashes = {h for h in eq_hashes if h}
        if len(eq_hashes) > 1:
            all_match = False

    # Output table: equivalence_hash | receipt_hash | intent | response_sha256 | evidence_count
    print("entry_point | equivalence_hash | receipt_hash | intent | response_sha256 | evidence_count")
    print("-" * 100)
    for key, group in groups.items():
        for e in group:
            d = e.get("data") or {}
            ep = d.get("entry_point", "?")
            eqh = (d.get("equivalence_hash_sha256") or "")[:16] + "..."
            rcp = (receipt_by_corr.get(e.get("corr_id", ""), ""))[:16] + "..."
            intent = d.get("intent", "?")
            rs = (d.get("response_sha256") or "")[:16] + "..."
            ec = d.get("evidence_count", 0)
            print(f"{ep:20} | {eqh:20} | {rcp:20} | {intent:25} | {rs:20} | {ec}")
        print()

    if not all_match:
        print("VARIANCE DETECTED (equivalence_hash mismatch)")
        print("Suggested culprits:")
        for group in list(groups.values())[:1]:
            resp_hashes = {e.get("data", {}).get("response_sha256") for e in group}
            ev_counts = {e.get("data", {}).get("evidence_count") for e in group}
            if len(resp_hashes) > 1:
                print("  - Different response_sha256 -> synthesis nondeterminism or different STATE")
            if len(ev_counts) > 1:
                print("  - Different evidence_count -> different evidence hashes (STATE drift, repo diff)")

    return 0 if all_match else 1


if __name__ == "__main__":
    sys.exit(main())
