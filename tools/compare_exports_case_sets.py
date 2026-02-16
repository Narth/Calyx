#!/usr/bin/env python3
"""
Compare case sets between desktop and laptop exports; compute intersection GDH.
Read-only; no harness changes. Outputs gdh_case_set_diff report and prints summary tables.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reuse GDH canonical record logic (read-only); load from same dir for run-from-anywhere
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
gdh_canonical_dumps = _gdh.gdh_canonical_dumps
sha256_hex = _gdh.sha256_hex


def extract_case_ids(receipts: list[dict]) -> list[str]:
    """Extract ordered case_id from each receipt. STOP if field missing."""
    out = []
    for r in receipts:
        case_id = r.get("case_id")
        if case_id is None and "case_id" not in r:
            return None  # signal missing
        out.append((case_id or "").strip())
    return out


def suite_manifest_hash(suite_id: str) -> str:
    """Best-effort: hash manifest.json if present, else directory file list + file hashes."""
    suite_dir = REPO_ROOT / "benchmarks" / "suites" / suite_id
    if not suite_dir.exists():
        return ""
    manifest_path = suite_dir / "manifest.json"
    if manifest_path.exists():
        return sha256_hex(manifest_path.read_bytes())
    # Else: sorted list of (name, sha256(content))
    parts = []
    for p in sorted(suite_dir.iterdir()):
        if p.is_file():
            parts.append((p.name, sha256_hex(p.read_bytes())))
    return sha256_hex(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def run(
    desktop_root: Path,
    laptop_root: Path,
    out_path: Path,
) -> dict:
    desktop_root = desktop_root.resolve()
    laptop_root = laptop_root.resolve()

    report = {
        "desktop_export": str(desktop_root),
        "laptop_export": str(laptop_root),
        "per_seed": {},
        "gdh_suite_intersection": {},
        "gdh_suite_full": {"desktop": {}, "laptop": {}},
        "suite_manifest_hash": {},
    }

    suites = [("protocol_probe_v0_1", 1), ("prompt_injection_v0_2", 2)]

    for suite_id, lane in suites:
        d_by_seed = discover_receipts_by_seed(desktop_root, suite_id)
        l_by_seed = discover_receipts_by_seed(laptop_root, suite_id)
        all_seeds = sorted(set(d_by_seed) | set(l_by_seed))

        for seed in all_seeds:
            if seed not in report["per_seed"]:
                report["per_seed"][seed] = {}
            if suite_id not in report["per_seed"][seed]:
                report["per_seed"][seed][suite_id] = {}

            d_path = d_by_seed.get(seed)
            l_path = l_by_seed.get(seed)
            d_rec = load_receipts(d_path) if d_path else []
            l_rec = load_receipts(l_path) if l_path else []

            d_ids = extract_case_ids(d_rec) if d_rec else []
            l_ids = extract_case_ids(l_rec) if l_rec else []
            if d_rec and d_ids is None:
                print("STOP: case_id missing in desktop receipt (seed=%s, suite=%s)" % (seed, suite_id), file=sys.stderr)
                sys.exit(1)
            if l_rec and l_ids is None:
                print("STOP: case_id missing in laptop receipt (seed=%s, suite=%s)" % (seed, suite_id), file=sys.stderr)
                sys.exit(1)

            set_d = set(d_ids or [])
            set_l = set(l_ids or [])
            only_d = sorted(set_d - set_l)
            only_l = sorted(set_l - set_d)
            inter = sorted(set_d & set_l)

            report["per_seed"][seed][suite_id] = {
                "case_count_desktop": len(d_ids) if d_ids else 0,
                "case_count_laptop": len(l_ids) if l_ids else 0,
                "case_ids_only_in_desktop": only_d,
                "case_ids_only_in_laptop": only_l,
                "case_ids_intersection": inter,
                "case_set_identical": set_d == set_l,
            }

            # Build receipt lookup by case_id for intersection GDH
            d_by_cid = {(r.get("case_id") or "").strip(): r for r in (d_rec or [])}
            l_by_cid = {(r.get("case_id") or "").strip(): r for r in (l_rec or [])}

            # Intersection GDH: canonical records for intersection, sorted by case_id
            inter_hashes_d = []
            inter_hashes_l = []
            for cid in inter:
                rd = d_by_cid.get(cid)
                rl = l_by_cid.get(cid)
                if rd is not None:
                    rec_d = build_canonical_record(rd, suite_id, lane, seed)
                    inter_hashes_d.append((cid, sha256_hex(gdh_canonical_dumps(rec_d))))
                if rl is not None:
                    rec_l = build_canonical_record(rl, suite_id, lane, seed)
                    inter_hashes_l.append((cid, sha256_hex(gdh_canonical_dumps(rec_l))))

            # Sort by case_id; then list of hashes in that order
            inter_hashes_d.sort(key=lambda x: x[0])
            inter_hashes_l.sort(key=lambda x: x[0])
            list_d = [h for _, h in inter_hashes_d]
            list_l = [h for _, h in inter_hashes_l]
            gdh_inter_d = sha256_hex(gdh_canonical_dumps(list_d)) if list_d else ""
            gdh_inter_l = sha256_hex(gdh_canonical_dumps(list_l)) if list_l else ""

            if seed not in report["gdh_suite_intersection"]:
                report["gdh_suite_intersection"][seed] = {}
            report["gdh_suite_intersection"][seed][suite_id] = {
                "gdh_suite_intersection_desktop": gdh_inter_d,
                "gdh_suite_intersection_laptop": gdh_inter_l,
                "match": gdh_inter_d == gdh_inter_l,
            }

            # gdh_suite_full per node (same as GDH v0.1: receipt order)
            for label, recs, storage in [
                ("desktop", d_rec, report["gdh_suite_full"]["desktop"]),
                ("laptop", l_rec, report["gdh_suite_full"]["laptop"]),
            ]:
                if seed not in storage:
                    storage[seed] = {}
                case_hashes = []
                for r in recs or []:
                    rec = build_canonical_record(r, suite_id, lane, seed)
                    case_hashes.append(sha256_hex(gdh_canonical_dumps(rec)))
                storage[seed][suite_id] = sha256_hex(gdh_canonical_dumps(case_hashes)) if case_hashes else ""

        # Suite manifest hash (one repo = same for both nodes when run on desktop)
        h = suite_manifest_hash(suite_id)
        report["suite_manifest_hash"][suite_id] = {
            "suite_manifest_hash_desktop": h,
            "suite_manifest_hash_laptop": h,
            "match": True,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main() -> None:
    desktop = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
    laptop = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")
    out_path = REPO_ROOT / "runtime" / "benchmarks" / "results" / "forensics" / "gdh_case_set_diff_20260216.json"

    if not desktop.exists():
        print("STOP: desktop export not found:", desktop, file=sys.stderr)
        sys.exit(1)
    if not laptop.exists():
        print("STOP: laptop export not found:", laptop, file=sys.stderr)
        sys.exit(1)

    report = run(desktop, laptop, out_path)

    print("Report written to:", out_path)
    print()

    # A) Case-set parity table
    print("A) Case-set parity table:")
    print("Seed   | Suite                   | Desktop cases | Laptop cases | Case-set identical? (Y/N)")
    print("-" * 85)
    for seed in sorted(report["per_seed"].keys(), key=lambda x: (int(x) if isinstance(x, int) else x)):
        for suite_id in ["protocol_probe_v0_1", "prompt_injection_v0_2"]:
            s = report["per_seed"].get(seed, {}).get(suite_id, {})
            cd = s.get("case_count_desktop", 0)
            cl = s.get("case_count_laptop", 0)
            ident = "Y" if s.get("case_set_identical") else "N"
            print("%-6s | %-23s | %14s | %13s | %s" % (seed, suite_id, cd, cl, ident))

    print()
    # B) Intersection GDH table
    print("B) Intersection GDH table:")
    print("Seed   | Suite                   | gdh_suite_intersection match? (Y/N)")
    print("-" * 65)
    for seed in sorted(report["gdh_suite_intersection"].keys(), key=lambda x: (int(x) if isinstance(x, int) else x)):
        for suite_id in ["protocol_probe_v0_1", "prompt_injection_v0_2"]:
            s = report["gdh_suite_intersection"].get(seed, {}).get(suite_id, {})
            m = "Y" if s.get("match") else "N"
            print("%-6s | %-23s | %s" % (seed, suite_id, m))

    print()
    # Suite manifest hash
    print("Suite manifest hash (repo-based; single node so desktop = laptop):")
    for suite_id in ["protocol_probe_v0_1", "prompt_injection_v0_2"]:
        sm = report["suite_manifest_hash"].get(suite_id, {})
        hd = sm.get("suite_manifest_hash_desktop", "N/A")
        hl = sm.get("suite_manifest_hash_laptop", "N/A")
        m = "Y" if sm.get("match") else "N"
        print("  %s: desktop=%s laptop=%s match? %s" % (suite_id, hd[:16] + "..." if len(hd) > 16 else hd, hl[:16] + "..." if len(hl) > 16 else hl, m))


if __name__ == "__main__":
    main()
