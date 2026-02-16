#!/usr/bin/env python3
"""
GDH accepted-mode decision diff summary (read-only).
For seed/suite pairs where gdh_suite differs, classify each differing case as A/B/C/D
and print summary table + top 10 examples per category.
Does not modify files or recompute GDH reports.
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

FORENSICS_DIR = REPO_ROOT / "runtime" / "benchmarks" / "results" / "forensics"
REPORT_DESKTOP = FORENSICS_DIR / "gdh_accepted_desktop_20260216.json"
REPORT_LAPTOP = FORENSICS_DIR / "gdh_accepted_laptop_20260216.json"
DESKTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
LAPTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")

SUITES = [("protocol_probe_v0_1", 1), ("prompt_injection_v0_2", 2)]

# Classification: A = decision differs, B = decision same but accepted_tool_calls differ, C = reason_codes differ, D = forbidden_tool_executed differs
def _values_equal(a, b) -> bool:
    if a == b:
        return True
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_values_equal(a.get(k), b.get(k)) for k in a)
    return False


def classify_diff(rec_d: dict, rec_l: dict) -> str:
    """Exactly one of A, B, C, D."""
    if rec_d.get("decision") != rec_l.get("decision"):
        return "A"
    if not _values_equal(rec_d.get("accepted_tool_calls"), rec_l.get("accepted_tool_calls")):
        return "B"
    if rec_d.get("reason_codes") != rec_l.get("reason_codes"):
        return "C"
    if rec_d.get("forbidden_tool_executed") != rec_l.get("forbidden_tool_executed"):
        return "D"
    return "—"  # identical (shouldn't appear for "differing" cases)


def main() -> None:
    with open(REPORT_DESKTOP, "r", encoding="utf-8") as f:
        report_d = json.load(f)
    with open(REPORT_LAPTOP, "r", encoding="utf-8") as f:
        report_l = json.load(f)

    per_seed_d = report_d["per_seed"]
    per_seed_l = report_l["per_seed"]

    # Seed/suite pairs where gdh_suite differs (normalize seed to int for receipt lookup)
    differing_pairs = []
    all_seeds = set()
    for k in set(per_seed_d) | set(per_seed_l):
        try:
            all_seeds.add(int(k))
        except (TypeError, ValueError):
            all_seeds.add(k)
    for seed in sorted(all_seeds, key=lambda x: (str(x), x)):
        sk = str(seed)
        for suite_id, lane in SUITES:
            gd = (per_seed_d.get(seed) or per_seed_d.get(sk) or {}).get(suite_id) or {}
            gl = (per_seed_l.get(seed) or per_seed_l.get(sk) or {}).get(suite_id) or {}
            if gd.get("gdh_suite") != gl.get("gdh_suite"):
                differing_pairs.append((seed, suite_id, lane))

    # Build canonical records by case_id from receipts for each differing pair
    rows = []
    examples = {"A": [], "B": [], "C": [], "D": []}

    for seed, suite_id, lane in differing_pairs:
        by_seed_d = discover_receipts_by_seed(DESKTOP_EXPORT, suite_id)
        by_seed_l = discover_receipts_by_seed(LAPTOP_EXPORT, suite_id)
        seed_int = int(seed) if isinstance(seed, str) and seed.isdigit() else seed
        path_d = by_seed_d.get(seed_int)
        path_l = by_seed_l.get(seed_int)
        if not path_d or not path_l:
            continue
        recs_d = load_receipts(path_d)
        recs_l = load_receipts(path_l)
        by_cid_d = {}
        for r in recs_d:
            rec = build_canonical_record_accepted(r, suite_id, lane, seed_int)
            by_cid_d[rec["case_id"]] = rec
        by_cid_l = {}
        for r in recs_l:
            rec = build_canonical_record_accepted(r, suite_id, lane, seed_int)
            by_cid_l[rec["case_id"]] = rec

        intersection = sorted(set(by_cid_d) & set(by_cid_l))
        total_cases = len(intersection)
        differing = []
        counts = {"A": 0, "B": 0, "C": 0, "D": 0}

        for case_id in intersection:
            rd = by_cid_d[case_id]
            rl = by_cid_l[case_id]
            if rd == rl:
                continue
            cat = classify_diff(rd, rl)
            if cat == "—":
                continue
            differing.append((case_id, cat, rd, rl))
            counts[cat] += 1

        diff_count = len(differing)
        rows.append((seed, suite_id, total_cases, diff_count, counts["A"], counts["B"], counts["C"], counts["D"]))

        for case_id, cat, rd, rl in differing:
            if len(examples[cat]) < 10:
                examples[cat].append((seed, suite_id, case_id, rd, rl))

    # Summary table
    print("Seed     | Suite                     | Total cases | Differing | A   | B   | C   | D")
    print("-" * 85)
    for seed, suite_id, total, diff, a, b, c, d in rows:
        print("%-8s | %-25s | %11s | %8s | %3s | %3s | %3s | %3s" % (seed, suite_id, total, diff, a, b, c, d))

    # Top 10 examples per category
    print()
    for cat in ("A", "B", "C", "D"):
        label = {"A": "decision differs", "B": "decision same, accepted_tool_calls differ",
                 "C": "reason_codes differ (decision same)", "D": "forbidden_tool_executed differs"}[cat]
        print("Top 10 examples - %s: %s" % (cat, label))
        print("  (Seed, Suite, Case ID)")
        for item in examples[cat][:10]:
            seed, suite_id, case_id = item[0], item[1], item[2]
            print("    %s | %s | %s" % (seed, suite_id, case_id))
        if len(examples[cat]) < 10:
            print("    (total %s examples)" % len(examples[cat]))
        print()


if __name__ == "__main__":
    main()
