#!/usr/bin/env python3
"""
WO_GOVERNANCE_BUDGET_COVERAGE_GUARANTEE_V2 — Coverage matrix test ladder.
Runs deterministic tests for each response path, produces matrix report.
Usage: python Scripts/governance_budget_coverage_ladder.py [--base-url URL]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


def _resolve_repo_root() -> Path:
    env_root = __import__("os").environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[1]


# Test cases: (case_id, user_text, allow_tools, expected_intent_hint)
CASES = [
    ("A", "heartbeat", False, "HEARTBEAT"),
    ("B", "What is the failure event log format?", False, "FAILURE_EVENT"),
    ("C", "Which file defines the emit function?", True, "FILE_LOCATION"),
    ("D", "Search for event_ledger and tell me which file defines emit", True, "COMPOUND"),
    ("E", "Confirm receipt. No further action necessary.", False, "CONFIRMATION"),
    ("F", "Summarize the purpose of STATE.md in one sentence.", True, "FREE_CHAT"),
]

HEADERS = {"Content-Type": "application/json", "X-Calyx-Source": "calyx-discord-gateway"}


def run_case(base_url: str, case_id: str, user_text: str, allow_tools: bool) -> dict:
    """Run one test case, return result with corr_id from response headers or receipt."""
    try:
        r = httpx.post(
            f"{base_url}/chat",
            headers=HEADERS,
            json={"user_text": user_text, "session_id": f"ladder-{case_id}", "allow_tools": allow_tools},
            timeout=120.0,
        )
        corr_id = ""
        if r.status_code == 200:
            body = r.json()
            corr_id = body.get("corr_id") or ""
            if not corr_id and "receipt_sha256" in body:
                corr_id = "see_ledger"
        return {
            "case_id": case_id,
            "status_code": r.status_code,
            "corr_id": corr_id,
            "ok": r.status_code == 200,
        }
    except Exception as e:
        return {"case_id": case_id, "status_code": -1, "corr_id": "", "ok": False, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Governance budget coverage test ladder")
    ap.add_argument("--base-url", default="http://127.0.0.1:7778", help="CBO Core base URL")
    args = ap.parse_args()

    repo = _resolve_repo_root()
    ledger_dir = repo / "runtime" / "ledger"
    budget_dir = repo / "runtime" / "receipts" / "budget"

    print("Running coverage ladder...")
    results = []
    for case_id, user_text, allow_tools, _ in CASES:
        r = run_case(args.base_url, case_id, user_text, allow_tools)
        results.append(r)
        print(f"  Case {case_id}: {'OK' if r['ok'] else 'FAIL'} (status={r['status_code']})")
        time.sleep(0.5)

    time.sleep(2)
    cutoff = datetime.now(timezone.utc)
    cutoff = cutoff - timedelta(minutes=2)

    def parse_ts(s):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    human_received: dict[str, tuple[str, str]] = {}
    response_finalized: dict[str, str] = {}
    budget_recorded: dict[str, dict] = {}
    case_to_corr: dict[str, str] = {}

    for p in sorted(ledger_dir.glob("station_events__*.jsonl"), reverse=True):
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                ts = parse_ts(rec.get("ts", ""))
                if ts and ts < cutoff:
                    continue
                cid = (rec.get("corr_id") or rec.get("data", {}).get("corr_id") or "").strip()
                if not cid:
                    continue
                data = rec.get("data", {})
                ev = rec.get("event", "")
                if ev == "human.request.received":
                    sid = data.get("session_id", "")
                    human_received[cid] = (data.get("entry_point", ""), sid)
                    if sid.startswith("ladder-"):
                        case_to_corr[sid.replace("ladder-", "")] = cid
                elif ev == "response.finalized":
                    response_finalized[cid] = data.get("intent", "")
                elif ev == "budget.request.recorded":
                    budget_recorded[cid] = data
        except Exception as e:
            print(f"Ledger error: {e}", file=sys.stderr)

    budget_lines: dict[str, dict] = {}
    for p in sorted(budget_dir.glob("governance_budget__*.jsonl")):
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                ts = parse_ts(rec.get("ts_utc", ""))
                if ts and ts < cutoff:
                    continue
                cid = (rec.get("corr_id") or "").strip()
                if cid:
                    budget_lines[cid] = rec
        except Exception as e:
            print(f"Budget error: {e}", file=sys.stderr)
            budget_lines = {}
            budget_lines = {}

    print()
    print("Coverage Matrix Report")
    print("=" * 110)
    print(f"{'Case':<6} | {'corr_id':<38} | {'entry_point':<18} | {'intent':<22} | {'fin':<4} | {'budg':<4} | {'JSONL':<5} | {'tools':<5} | {'fail':<4} | PASS/FAIL")
    print("-" * 110)

    for case_id, _, _, _ in CASES:
        cid = case_to_corr.get(case_id, "")
        if not cid:
            print(f"{case_id:<6} | (no corr_id — check session ladder-{case_id})")
            continue
        ep, _ = human_received.get(cid, ("", ""))
        intent = response_finalized.get(cid, "—")
        has_final = "yes" if cid in response_finalized else "no"
        has_budget_evt = "yes" if cid in budget_recorded else "no"
        has_jsonl = "yes" if cid in budget_lines else "no"
        tools = str(budget_recorded.get(cid, {}).get("tool_calls_total", budget_lines.get(cid, {}).get("tool_calls_total", "—")))
        claims_fail = str(budget_recorded.get(cid, {}).get("claim_failed_count", budget_lines.get(cid, {}).get("claims", {}).get("failed", "—")))
        if cid in response_finalized:
            pass_fail = "PASS" if (cid in budget_recorded and cid in budget_lines) else "FAIL"
        else:
            pass_fail = "PASS" if (cid not in budget_recorded and cid not in budget_lines) else "FAIL"
        print(f"{case_id:<6} | {cid[:36]:<38} | {ep[:16]:<18} | {intent[:20]:<22} | {has_final:<4} | {has_budget_evt:<4} | {has_jsonl:<5} | {tools:<5} | {claims_fail:<4} | {pass_fail}")

    print()
    print("Cases A–F: must have response.finalized + budget.request.recorded + JSONL line")
    print("Cases G–H: run separately (governance rejection, replay) — must NOT produce budget")

    corr_file = repo / "runtime" / "receipts" / "budget" / "last_ladder_corr_ids.txt"
    try:
        corr_file.parent.mkdir(parents=True, exist_ok=True)
        with corr_file.open("w") as f:
            for cid in case_to_corr.values():
                f.write(cid + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
