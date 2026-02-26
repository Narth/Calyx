#!/usr/bin/env python3
"""
WO_AUDIT_QUERY_TOOLING_V1 — Coverage quick checks (operator-friendly).
Usage: python Scripts/audit_health.py --since-minutes N
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


def _iter_ledger_lines(ledger_dir: Path, since_minutes: int) -> list[tuple[datetime, dict]]:
    """Yield (ts, rec) for lines in time window. Sorted by ts ascending."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    results: list[tuple[datetime, dict]] = []
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        if not p.exists():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _parse_ts(rec.get("ts", "") or rec.get("ts_utc", ""))
                if ts and ts < cutoff:
                    continue
                results.append((ts or datetime.min.replace(tzinfo=timezone.utc), rec))
        except Exception:
            continue
    results.sort(key=lambda x: x[0])
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit health coverage check")
    parser.add_argument("--since-minutes", type=int, default=60, help="Time window (default 60)")
    args = parser.parse_args()

    repo = _resolve_repo_root()
    ledger_dir = repo / "runtime" / "ledger"

    if not ledger_dir.exists():
        print(f"Ledger dir missing: {ledger_dir}", file=sys.stderr)
        return 1

    indexed = _iter_ledger_lines(ledger_dir, args.since_minutes)
    recs = [r for _, r in indexed]

    human_received: set[str] = set()
    response_finalized: set[str] = set()
    budget_request_recorded: set[str] = set()
    task_triggered: set[str] = set()
    task_completed: set[str] = set()
    budget_task_recorded: set[str] = set()
    calyx_gateway_heartbeat: list[tuple[datetime, dict]] = []
    sender_identity_enabled: int = 0
    mismatches: list[str] = []

    for ts, rec in indexed:
        ev = rec.get("event", "")
        env = rec.get("causal_envelope") or {}
        data = rec.get("data") or {}

        cid = rec.get("corr_id") or env.get("corr_id") or data.get("corr_id") or ""
        tid = env.get("task_corr_id") or data.get("task_corr_id") or ""

        if ev == "human.request.received" and cid:
            human_received.add(cid)
        elif ev == "response.finalized" and cid:
            response_finalized.add(cid)
        elif ev == "budget.request.recorded":
            bc = data.get("corr_id") or cid
            if bc:
                budget_request_recorded.add(bc)
        elif ev == "system.task.triggered" and tid:
            task_triggered.add(tid)
        elif ev == "system.task.completed" and tid:
            task_completed.add(tid)
        elif ev == "budget.task.recorded":
            bt = data.get("task_corr_id") or tid
            if bt:
                budget_task_recorded.add(bt)
        elif ev == "calyx_gateway.heartbeat":
            calyx_gateway_heartbeat.append((ts, rec))
        elif ev == "discord.heartbeat.sender.identity":
            if data.get("heartbeat_sender_enabled") is True:
                sender_identity_enabled += 1
        elif ev == "audit.external.emitter.detected":
            if "openclaw" in str(data.get("emitter", "")).lower():
                mismatches.append("audit.external.emitter.detected (openclaw) — fail-closed required")

    print(f"Audit health (last {args.since_minutes} minutes)")
    print("-" * 50)
    print(f"  human.request.received (unique corr_id):  {len(human_received)}")
    print(f"  response.finalized:                       {len(response_finalized)}")
    print(f"  budget.request.recorded:                  {len(budget_request_recorded)}")
    print(f"  system.task.triggered (unique task_corr_id): {len(task_triggered)}")
    print(f"  system.task.completed:                    {len(task_completed)}")
    print(f"  budget.task.recorded:                     {len(budget_task_recorded)}")
    print(f"  calyx_gateway.heartbeat:                  {len(calyx_gateway_heartbeat)}")
    print(f"  discord.heartbeat.sender.identity (enabled): {sender_identity_enabled}")
    print()

    # WO_HEARTBEAT_SENDER_UNIFICATION_V1 + WO_GOVERNANCE_SINGULARITY_V3: exactly one sender
    if sender_identity_enabled != 1 and len(calyx_gateway_heartbeat) > 0:
        mismatches.append(f"discord.heartbeat.sender.identity with heartbeat_sender_enabled=true: expected 1, got {sender_identity_enabled} (audit.runtime.singularity_violation)")
    # WO_GOVERNANCE_SINGULARITY_V3: report singularity.confirmed count (informational)
    singularity_confirmed = sum(1 for _, r in indexed if r.get("event") == "audit.runtime.singularity.confirmed")
    print(f"  audit.runtime.singularity.confirmed:           {singularity_confirmed}")

    # WO_HEARTBEAT_SENDER_UNIFICATION_V1: no calyx_gateway.heartbeat without adjacent task events
    for hb_ts, hb_rec in calyx_gateway_heartbeat:
        tid = (hb_rec.get("data") or {}).get("task_corr_id") or (hb_rec.get("causal_envelope") or {}).get("task_corr_id") or ""
        has_triggered = any(
            abs((hb_ts - t).total_seconds()) <= 5 and r.get("event") == "system.task.triggered"
            and ((r.get("data") or {}).get("task_corr_id") or (r.get("causal_envelope") or {}).get("task_corr_id") or "") == tid
            for t, r in indexed
        )
        has_budget = any(
            abs((hb_ts - t).total_seconds()) <= 5 and r.get("event") == "budget.task.recorded"
            and ((r.get("data") or {}).get("task_corr_id") or "") == tid
            for t, r in indexed
        )
        if not has_triggered or not has_budget:
            mismatches.append(f"calyx_gateway.heartbeat at {hb_ts.strftime('%H:%M:%S')}: missing adjacent system.task.triggered={not has_triggered} budget.task.recorded={not has_budget}")

    for cid in human_received:
        if cid not in response_finalized:
            mismatches.append(f"corr_id={cid[:16]}...: human.request.received but no response.finalized")
        if cid in response_finalized and cid not in budget_request_recorded:
            mismatches.append(f"corr_id={cid[:16]}...: response.finalized but no budget.request.recorded")

    for cid in response_finalized:
        if cid not in human_received:
            mismatches.append(f"corr_id={cid[:16]}...: response.finalized without human.request.received (orphan?)")

    for tid in task_triggered:
        if tid not in task_completed:
            mismatches.append(f"task_corr_id={tid[:16]}...: system.task.triggered but no system.task.completed")
        if tid not in budget_task_recorded:
            mismatches.append(f"task_corr_id={tid[:16]}...: system.task.triggered but no budget.task.recorded")

    for tid in task_completed:
        if tid not in task_triggered:
            mismatches.append(f"task_corr_id={tid[:16]}...: system.task.completed without system.task.triggered (orphan?)")

    if mismatches:
        print("Mismatches / orphan conditions (WO_GOVERNANCE_SINGULARITY_V3: fail):")
        for m in mismatches[:20]:
            print(f"  ! {m}")
        if len(mismatches) > 20:
            print(f"  ... and {len(mismatches) - 20} more")
        return 1
    print("No mismatches detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
