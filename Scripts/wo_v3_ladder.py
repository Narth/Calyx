#!/usr/bin/env python3
"""
WO_GOVERNANCE_SINGULARITY_AND_DOC_AUTHORITY_V3 — Ladder runner.
Runs automatable phases; reports on manual phases.
Usage: python Scripts/wo_v3_ladder.py [--phase 0|1|5|all]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _repo_root() -> Path:
    env = __import__("os").environ.get("CALYX_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _iter_ledger(ledger_dir: Path, since_minutes: int):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_str = rec.get("ts") or rec.get("ts_utc", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < cutoff:
                continue
            yield ts, rec


def phase0_baseline(ledger_dir: Path, since_min: int = 10) -> list[str]:
    """Phase 0: Exactly one singularity.confirmed, one sender identity, no violations."""
    errs: list[str] = []
    singularity_confirmed = 0
    sender_identity_enabled = 0
    violations = 0
    breaches = 0
    heartbeats = 0

    for _, rec in _iter_ledger(ledger_dir, since_min):
        ev = rec.get("event", "")
        data = rec.get("data") or {}
        if ev == "audit.runtime.singularity.confirmed":
            singularity_confirmed += 1
        elif ev == "discord.heartbeat.sender.identity" and data.get("heartbeat_sender_enabled") is True:
            sender_identity_enabled += 1
        elif ev == "audit.runtime.singularity_violation":
            violations += 1
        elif ev == "audit.runtime.singularity.breach":
            breaches += 1
        elif ev == "calyx_gateway.heartbeat":
            heartbeats += 1

    if sender_identity_enabled != 1:
        errs.append(f"Phase 0: expected exactly 1 sender identity (enabled), got {sender_identity_enabled}")
    if singularity_confirmed != 1:
        errs.append(f"Phase 0: expected 1 singularity.confirmed, got {singularity_confirmed}")
    if violations > 0:
        errs.append(f"Phase 0: singularity_violation detected ({violations})")
    if breaches > 0:
        errs.append(f"Phase 0: singularity.breach detected ({breaches})")

    return errs


def phase1_doc_override(ledger_dir: Path, since_min: int = 10) -> list[str]:
    """Phase 1: Check doc override events. Manual: run Cases A-D and inspect."""
    errs: list[str] = []
    override_requested = []
    legacy_used = []
    rejected = []

    for _, rec in _iter_ledger(ledger_dir, since_min):
        ev = rec.get("event", "")
        data = rec.get("data") or {}
        if ev == "audit.doc.override.requested":
            override_requested.append(data.get("source", "?"))
        elif ev == "audit.doc.override.legacy_token_used":
            legacy_used.append(1)
        elif ev == "audit.doc.override.rejected_legacy":
            rejected.append(1)

    # Mixed sources check
    if len(set(override_requested)) > 1:
        errs.append(f"Phase 1: mixed override sources: {override_requested}")

    return errs


def phase5_audit_health() -> tuple[int, str]:
    """Phase 5: Run audit_health. Must exit 0."""
    repo = _repo_root()
    result = subprocess.run(
        [sys.executable, str(repo / "Scripts" / "audit_health.py"), "--since-minutes", "60"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="WO_V3 Ladder runner")
    parser.add_argument("--phase", choices=["0", "1", "5", "all"], default="all")
    parser.add_argument("--since-minutes", type=int, default=10)
    args = parser.parse_args()

    repo = _repo_root()
    ledger_dir = repo / "runtime" / "ledger"

    if not ledger_dir.exists():
        print(f"Ledger dir missing: {ledger_dir}", file=sys.stderr)
        return 1

    errs: list[str] = []

    if args.phase in ("0", "all"):
        print("Phase 0 — Baseline...")
        errs.extend(phase0_baseline(ledger_dir, args.since_minutes))

    if args.phase in ("1", "all"):
        print("Phase 1 — Doc override (mixed-source check)...")
        errs.extend(phase1_doc_override(ledger_dir, args.since_minutes))

    if args.phase in ("5", "all"):
        print("Phase 5 — Audit health...")
        code, out = phase5_audit_health()
        print(out)
        if code != 0:
            errs.append("Phase 5: audit_health failed (exit non-zero)")

    if errs:
        print("\nLadder FAILED:")
        for e in errs:
            print(f"  ! {e}")
        return 1

    print("\nLadder passed (automated phases).")
    print("Manual: Phase 1 Cases A-D, Phase 2 restart, Phase 3 OpenClaw probe, Phase 4 kill switch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
