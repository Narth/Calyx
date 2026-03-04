#!/usr/bin/env python3
"""
Lane 1 action diff (system_split): explain which cases cause gdh_action_suite mismatch.
Protocol_probe_v0_1 only, seeds 1337 and 8675309. Read-only; writes one forensics JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "compute_gdh_from_export",
    REPO / "tools" / "compute_gdh_from_export.py",
)
_gdh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gdh)
load_receipts = _gdh.load_receipts
discover_receipts_by_seed = _gdh.discover_receipts_by_seed
build_canonical_record_action = _gdh.build_canonical_record_action
_check_required_fields_system = _gdh._check_required_fields_system

DESKTOP_EXPORT = REPO / "exports" / "desktop_ladder_20260216"
LAPTOP_EXPORT = REPO / "exports" / "laptop_ladder_20260216"
SUITE_ID = "protocol_probe_v0_1"
LANE = 1
SEEDS = [1337, 8675309]
ACTION_FIELDS_TO_COMPARE = ["system_decision", "accepted_tool_calls_canonical", "forbidden_tool_executed"]
OUT_PATH = REPO / "runtime" / "benchmarks" / "results" / "forensics" / "lane1_action_diff_seed1337_8675309_protocol_probe_v0_1.json"


def values_equal(a, b) -> bool:
    return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))


def run_seed(seed: int) -> dict:
    d_by_seed = discover_receipts_by_seed(DESKTOP_EXPORT, SUITE_ID)
    l_by_seed = discover_receipts_by_seed(LAPTOP_EXPORT, SUITE_ID)
    d_path = d_by_seed.get(seed)
    l_path = l_by_seed.get(seed)

    if not d_path or not d_path.exists():
        print("STOP: desktop receipts not found for seed=%s suite=%s" % (seed, SUITE_ID), file=sys.stderr)
        sys.exit(1)
    if not l_path or not l_path.exists():
        print("STOP: laptop receipts not found for seed=%s suite=%s" % (seed, SUITE_ID), file=sys.stderr)
        sys.exit(1)

    d_recs = load_receipts(d_path)
    l_recs = load_receipts(l_path)
    if not d_recs:
        print("STOP: no desktop receipts for seed=%s" % seed, file=sys.stderr)
        sys.exit(1)
    if not l_recs:
        print("STOP: no laptop receipts for seed=%s" % seed, file=sys.stderr)
        sys.exit(1)

    for r in d_recs:
        _check_required_fields_system(r, SUITE_ID)
    for r in l_recs:
        _check_required_fields_system(r, SUITE_ID)

    d_by_cid = {}
    for r in d_recs:
        cid = (r.get("case_id") or "").strip()
        d_by_cid[cid] = build_canonical_record_action(r, SUITE_ID, LANE, seed)
    l_by_cid = {}
    for r in l_recs:
        cid = (r.get("case_id") or "").strip()
        l_by_cid[cid] = build_canonical_record_action(r, SUITE_ID, LANE, seed)

    only_d = sorted(set(d_by_cid) - set(l_by_cid))
    only_l = sorted(set(l_by_cid) - set(d_by_cid))
    if only_d or only_l:
        print("STOP: case-set drift for seed=%s" % seed, file=sys.stderr)
        print("case_ids only in desktop:", only_d, file=sys.stderr)
        print("case_ids only in laptop:", only_l, file=sys.stderr)
        sys.exit(1)

    common = sorted(set(d_by_cid) & set(l_by_cid))
    case_count = len(common)
    differing_cases = []
    for cid in common:
        rec_d = d_by_cid[cid]
        rec_l = l_by_cid[cid]
        fields_differ = []
        for f in ACTION_FIELDS_TO_COMPARE:
            vd = rec_d.get(f)
            vl = rec_l.get(f)
            if not values_equal(vd, vl):
                fields_differ.append(f)
        if not fields_differ:
            continue
        differing_cases.append({
            "case_id": cid,
            "fields_differ": fields_differ,
            "desktop": {f: rec_d.get(f) for f in fields_differ},
            "laptop": {f: rec_l.get(f) for f in fields_differ},
        })
    return {
        "case_count": case_count,
        "differing_case_count": len(differing_cases),
        "differing_cases": differing_cases,
    }


def main() -> None:
    if not DESKTOP_EXPORT.exists():
        print("STOP: desktop export not found:", DESKTOP_EXPORT, file=sys.stderr)
        sys.exit(1)
    if not LAPTOP_EXPORT.exists():
        print("STOP: laptop export not found:", LAPTOP_EXPORT, file=sys.stderr)
        sys.exit(1)

    report = {
        "suite_id": SUITE_ID,
        "lane": 1,
        "desktop_export": str(DESKTOP_EXPORT),
        "laptop_export": str(LAPTOP_EXPORT),
        "per_seed": {},
    }
    for seed in SEEDS:
        report["per_seed"][seed] = run_seed(seed)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Report written to:", OUT_PATH)

    print()
    print("Compact summary")
    print("Seed     | Total cases | Differing cases")
    print("-" * 45)
    for seed in SEEDS:
        p = report["per_seed"][seed]
        print("%-8s | %11s | %s" % (seed, p["case_count"], p["differing_case_count"]))

    all_differing = []
    for seed in SEEDS:
        for entry in report["per_seed"][seed]["differing_cases"]:
            all_differing.append((entry["case_id"], entry["fields_differ"]))
    print()
    print("Top 5 differing case_ids (with fields that differ):")
    for cid, fields in all_differing[:5]:
        print("  %s: %s" % (cid, ", ".join(fields)))
    if len(all_differing) > 5:
        print("  ... and %s more" % (len(all_differing) - 5))


if __name__ == "__main__":
    main()
