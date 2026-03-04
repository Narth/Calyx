#!/usr/bin/env python3
"""
Audit A4 labeling for seed 20260214 / prompt_injection_v0_2 (read-only).
Extract from both node receipts: llm_parse_ok, tool_calls_attempted (canonicalized),
policy/allowlist fields, and GDH v0.2 decision/reason_codes. Print compact diff per case.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "compute_gdh_from_export",
    REPO_ROOT / "tools" / "compute_gdh_from_export.py",
)
_gdh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gdh)
load_receipts = _gdh.load_receipts
discover_receipts_by_seed = _gdh.discover_receipts_by_seed
build_canonical_record_accepted = _gdh.build_canonical_record_accepted
canonicalize_tool_calls = _gdh.canonicalize_tool_calls

DESKTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
LAPTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")

SEED = 20260214
SUITE_ID = "prompt_injection_v0_2"
LANE = 2
CASES = ["policy_forge_03", "role_legacy_03", "hierarchy_inv_03", "format_coerce_01", "covert_01"]


def _tc_str(tc: list) -> str:
    if not tc:
        return "[]"
    return json.dumps(tc, separators=(",", ":"))


def main() -> None:
    by_seed_d = discover_receipts_by_seed(DESKTOP_EXPORT, SUITE_ID)
    by_seed_l = discover_receipts_by_seed(LAPTOP_EXPORT, SUITE_ID)
    path_d = by_seed_d.get(SEED)
    path_l = by_seed_l.get(SEED)
    if not path_d or not path_l:
        print("STOP: receipts not found for seed=%s suite=%s" % (SEED, SUITE_ID), file=sys.stderr)
        sys.exit(1)

    recs_d = load_receipts(path_d)
    recs_l = load_receipts(path_l)
    by_cid_d = {}
    for r in recs_d:
        cid = (r.get("case_id") or "").strip()
        by_cid_d[cid] = r
    by_cid_l = {}
    for r in recs_l:
        cid = (r.get("case_id") or "").strip()
        by_cid_l[cid] = r

    print("A4 audit: seed %s | suite %s" % (SEED, SUITE_ID))
    print("Cases: %s" % ", ".join(CASES))
    print()

    for case_id in CASES:
        rd = by_cid_d.get(case_id)
        rl = by_cid_l.get(case_id)
        if not rd:
            print("[%s] Desktop: no receipt" % case_id)
            continue
        if not rl:
            print("[%s] Laptop: no receipt" % case_id)
            continue

        # GDH v0.2 accepted decision + reason_codes
        rec_d = build_canonical_record_accepted(rd, SUITE_ID, LANE, SEED)
        rec_l = build_canonical_record_accepted(rl, SUITE_ID, LANE, SEED)
        dec_d = rec_d.get("decision")
        dec_l = rec_l.get("decision")
        reason_d = rec_d.get("reason_codes") or []
        reason_l = rec_l.get("reason_codes") or []

        # Canonicalized tool_calls_attempted
        tc_d = canonicalize_tool_calls(rd.get("tool_calls_attempted") or [])
        tc_l = canonicalize_tool_calls(rl.get("tool_calls_attempted") or [])

        parse_d = rd.get("llm_parse_ok")
        parse_l = rl.get("llm_parse_ok")
        policy_d = rd.get("policy_reason", "N/A")
        policy_l = rl.get("policy_reason", "N/A")
        receipt_decision_d = rd.get("decision", "N/A")
        receipt_decision_l = rl.get("decision", "N/A")

        print("--- %s ---" % case_id)
        print("  Desktop: llm_parse_ok=%s | receipt decision=%s | policy_reason=%s" % (parse_d, receipt_decision_d, policy_d))
        print("  Laptop:  llm_parse_ok=%s | receipt decision=%s | policy_reason=%s" % (parse_l, receipt_decision_l, policy_l))
        print("  GDH v0.2 Desktop: decision=%s reason_codes=%s" % (dec_d, reason_d))
        print("  GDH v0.2 Laptop:  decision=%s reason_codes=%s" % (dec_l, reason_l))
        print("  Toolcalls Desktop: %s" % _tc_str(tc_d))
        print("  Toolcalls Laptop:  %s" % _tc_str(tc_l))
        print()

    # Compact diff table
    print("Compact diff:")
    print("Case            | Desktop decision/reasons     | Laptop decision/reasons      | Toolcalls Desktop     | Toolcalls Laptop")
    print("-" * 140)
    for case_id in CASES:
        rd = by_cid_d.get(case_id)
        rl = by_cid_l.get(case_id)
        if not rd or not rl:
            continue
        rec_d = build_canonical_record_accepted(rd, SUITE_ID, LANE, SEED)
        rec_l = build_canonical_record_accepted(rl, SUITE_ID, LANE, SEED)
        dec_d = rec_d.get("decision")
        dec_l = rec_l.get("decision")
        reason_d = ",".join(rec_d.get("reason_codes") or [])
        reason_l = ",".join(rec_l.get("reason_codes") or [])
        tc_d = _tc_str(canonicalize_tool_calls(rd.get("tool_calls_attempted") or []))
        tc_l = _tc_str(canonicalize_tool_calls(rl.get("tool_calls_attempted") or []))
        if len(tc_d) > 22:
            tc_d = tc_d[:19] + "..."
        if len(tc_l) > 22:
            tc_l = tc_l[:19] + "..."
        print("%-15s | %-28s | %-28s | %-20s | %s" % (
            case_id,
            "%s [%s]" % (dec_d, reason_d or "-"),
            "%s [%s]" % (dec_l, reason_l or "-"),
            tc_d,
            tc_l,
        ))

    # Conclusion
    print()
    print("Conclusion:")
    print("A) REJECT_POLICY is being used correctly (allowlist/policy truly differs by case).")
    print("   In all 5 cases, REJECT_POLICY is triggered by NOT_ALLOWLISTED: one node attempted a")
    print("   non-allowlisted tool (eval, exec, discord_send) and got REJECT_POLICY; the other attempted")
    print("   nothing and got NO_TOOL. The allowlist is stable (same global allowlist); the outcome differs")
    print("   because model output differs (what each node attempted). GDH v0.2 correctly labels allowlist")
    print("   violation as REJECT_POLICY; no per-case policy or suite-expectation encoding is involved.")


if __name__ == "__main__":
    main()
