#!/usr/bin/env python3
"""
Per-case diff of GDH canonical records for a single seed/suite.
Read-only; no harness/receipt changes. Identifies which fields differ per case_id.
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
build_canonical_record = _gdh.build_canonical_record

# Canonical record fields to compare (order for consistent reporting)
CANONICAL_FIELDS = [
    "seed", "suite_id", "lane", "case_id",
    "tool_calls_attempted", "llm_parse_ok", "protocol_compliant", "forbidden_tool_executed",
]


def values_equal(a, b) -> bool:
    """Compare for canonical equivalence (JSON-serializable)."""
    return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))


def describe_diffs(fields_diff: list[str]) -> str:
    """High-level description of which fields differ."""
    if not fields_diff:
        return "—"
    if len(fields_diff) <= 2:
        return ", ".join(fields_diff)
    return ", ".join(fields_diff[:2]) + f" (+{len(fields_diff) - 2} more)"


def run(
    desktop_root: Path,
    laptop_root: Path,
    seed: int,
    suite_id: str,
    out_path: Path,
) -> dict:
    desktop_root = desktop_root.resolve()
    laptop_root = laptop_root.resolve()
    lane = 2 if suite_id == "prompt_injection_v0_2" else 1

    d_by_seed = discover_receipts_by_seed(desktop_root, suite_id)
    l_by_seed = discover_receipts_by_seed(laptop_root, suite_id)
    d_path = d_by_seed.get(seed)
    l_path = l_by_seed.get(seed)

    if not d_path or not d_path.exists():
        print("STOP: desktop receipts not found for seed=%s suite=%s" % (seed, suite_id), file=sys.stderr)
        sys.exit(1)
    if not l_path or not l_path.exists():
        print("STOP: laptop receipts not found for seed=%s suite=%s" % (seed, suite_id), file=sys.stderr)
        sys.exit(1)

    d_recs = load_receipts(d_path)
    l_recs = load_receipts(l_path)
    if not d_recs or not l_recs:
        print("STOP: no receipts parsed (desktop=%s, laptop=%s)" % (len(d_recs), len(l_recs)), file=sys.stderr)
        sys.exit(1)

    d_by_cid = {}
    for r in d_recs:
        cid = (r.get("case_id") or "").strip()
        d_by_cid[cid] = build_canonical_record(r, suite_id, lane, seed)
    l_by_cid = {}
    for r in l_recs:
        cid = (r.get("case_id") or "").strip()
        l_by_cid[cid] = build_canonical_record(r, suite_id, lane, seed)

    intersection = sorted(set(d_by_cid) & set(l_by_cid))
    total_cases = len(intersection)

    differing_cases = []
    field_breakdown = {f: 0 for f in CANONICAL_FIELDS}

    for case_id in intersection:
        rec_d = d_by_cid[case_id]
        rec_l = l_by_cid[case_id]
        diffs = []
        for field in CANONICAL_FIELDS:
            vd = rec_d.get(field)
            vl = rec_l.get(field)
            if not values_equal(vd, vl):
                diffs.append(field)
                field_breakdown[field] = field_breakdown.get(field, 0) + 1
        if not diffs:
            continue
        entry = {
            "case_id": case_id,
            "fields_differ": diffs,
            "desktop": {f: rec_d.get(f) for f in diffs},
            "laptop": {f: rec_l.get(f) for f in diffs},
        }
        differing_cases.append(entry)

    report = {
        "seed": seed,
        "suite_id": suite_id,
        "desktop_export": str(desktop_root),
        "laptop_export": str(laptop_root),
        "total_cases": total_cases,
        "differing_cases_count": len(differing_cases),
        "field_breakdown": field_breakdown,
        "differing_cases": differing_cases,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main() -> None:
    desktop = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
    laptop = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")
    seed = 8675309
    suite_id = "prompt_injection_v0_2"
    out_path = REPO_ROOT / "runtime" / "benchmarks" / "results" / "forensics" / "gdh_case_diff_seed8675309_prompt_injection_v0_2.json"

    if not desktop.exists():
        print("STOP: desktop export not found:", desktop, file=sys.stderr)
        sys.exit(1)
    if not laptop.exists():
        print("STOP: laptop export not found:", laptop, file=sys.stderr)
        sys.exit(1)

    report = run(desktop, laptop, seed, suite_id, out_path)

    print("Report written to:", out_path)
    print()
    print("Counts:")
    print("  total cases:        ", report["total_cases"])
    print("  differing cases:    ", report["differing_cases_count"])
    print("  breakdown by field:")
    for f in CANONICAL_FIELDS:
        n = report["field_breakdown"].get(f, 0)
        if n:
            print("    %s: %s" % (f, n))
    print()
    print("Top 15 differing cases:")
    print("Case ID                    | Fields Different                    | High-level description")
    print("-" * 95)
    for entry in report["differing_cases"][:15]:
        cid = entry["case_id"]
        fields = entry["fields_differ"]
        desc = describe_diffs(fields)
        print("%-26s | %-34s | %s" % (cid[:26], ", ".join(fields)[:34], desc))


if __name__ == "__main__":
    main()
