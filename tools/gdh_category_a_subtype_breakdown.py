#!/usr/bin/env python3
"""
Category A subtype breakdown (read-only).
For each seed/suite where Category A appears, break down A into A1/A2/A3/A4
and print table + top 10 examples for dominant subtype per seed/suite.
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

REJECT_PARSE = "REJECT_PARSE"
REJECT_POLICY = "REJECT_POLICY"
ACCEPT = "ACCEPT"
NO_TOOL = "NO_TOOL"


def classify_a_subtype(rec_d: dict, rec_l: dict) -> str:
    """Exactly one of A1, A2, A3, A4 for decision-differ cases."""
    d = rec_d.get("decision")
    l = rec_l.get("decision")
    if d == REJECT_PARSE and l != REJECT_PARSE:
        return "A1"
    if l == REJECT_PARSE and d != REJECT_PARSE:
        return "A2"
    # Neither side REJECT_PARSE
    if {d, l} == {ACCEPT, NO_TOOL}:
        return "A3"
    if d == REJECT_POLICY or l == REJECT_POLICY:
        return "A4"
    # Fallback (e.g. ACCEPT vs REJECT_POLICY already A4)
    return "A4"


def main() -> None:
    with open(REPORT_DESKTOP, "r", encoding="utf-8") as f:
        report_d = json.load(f)
    with open(REPORT_LAPTOP, "r", encoding="utf-8") as f:
        report_l = json.load(f)

    per_seed_d = report_d["per_seed"]
    per_seed_l = report_l["per_seed"]

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

    # Collect A cases with subtype per seed/suite
    # rows: (seed, suite_id, A_total, A1, A2, A3, A4)
    # by_seed_suite: (seed, suite_id) -> list of (case_id, subtype)
    rows = []
    by_seed_suite_a = {}  # (seed, suite_id) -> [(case_id, subtype), ...]

    for seed, suite_id, lane in differing_pairs:
        by_seed_d = discover_receipts_by_seed(DESKTOP_EXPORT, suite_id)
        by_seed_l = discover_receipts_by_seed(LAPTOP_EXPORT, suite_id)
        seed_int = int(seed) if isinstance(seed, str) and str(seed).isdigit() else seed
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
        a_cases = []  # (case_id, subtype)
        counts = {"A1": 0, "A2": 0, "A3": 0, "A4": 0}

        for case_id in intersection:
            rd = by_cid_d[case_id]
            rl = by_cid_l[case_id]
            if rd.get("decision") == rl.get("decision"):
                continue
            subtype = classify_a_subtype(rd, rl)
            a_cases.append((case_id, subtype))
            counts[subtype] += 1

        a_total = len(a_cases)
        if a_total == 0:
            continue
        rows.append((seed, suite_id, a_total, counts["A1"], counts["A2"], counts["A3"], counts["A4"]))
        by_seed_suite_a[(seed, suite_id)] = a_cases

    # Table
    print("Seed     | Suite                     | A_total | A1  | A2  | A3  | A4")
    print("-" * 65)
    for seed, suite_id, a_total, a1, a2, a3, a4 in rows:
        print("%-8s | %-25s | %7s | %3s | %3s | %3s | %3s" % (seed, suite_id, a_total, a1, a2, a3, a4))

    # Dominant subtype per seed/suite, top 10 example case_ids
    print()
    print("Top 10 example case_ids for dominant subtype per seed/suite:")
    for seed, suite_id, a_total, a1, a2, a3, a4 in rows:
        key = (seed, suite_id)
        a_cases = by_seed_suite_a.get(key, [])
        if not a_cases:
            continue
        subtype_counts = {"A1": 0, "A2": 0, "A3": 0, "A4": 0}
        for _cid, st in a_cases:
            subtype_counts[st] += 1
        dominant = max(["A1", "A2", "A3", "A4"], key=lambda s: subtype_counts[s])
        examples = [cid for cid, st in a_cases if st == dominant][:10]
        print("  %s | %s | dominant=%s | %s" % (seed, suite_id, dominant, ", ".join(examples)))


if __name__ == "__main__":
    main()
