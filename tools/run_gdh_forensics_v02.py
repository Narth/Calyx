#!/usr/bin/env python3
"""
Run GDH v0.1 (attempted) and v0.2 (accepted) for desktop/laptop exports,
write the four forensics reports, and print comparison tables.
No harness changes; read-only from exports.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import after path fix
from tools.compute_gdh_from_export import compute_gdh_for_export

DESKTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
LAPTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")
FORENSICS_DIR = REPO_ROOT / "runtime" / "benchmarks" / "results" / "forensics"

OUT_ATTEMPTED_DESKTOP = FORENSICS_DIR / "gdh_attempted_desktop_20260216.json"
OUT_ATTEMPTED_LAPTOP = FORENSICS_DIR / "gdh_attempted_laptop_20260216.json"
OUT_ACCEPTED_DESKTOP = FORENSICS_DIR / "gdh_accepted_desktop_20260216.json"
OUT_ACCEPTED_LAPTOP = FORENSICS_DIR / "gdh_accepted_laptop_20260216.json"


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Wrote:", path)


def per_seed_suite_match(per_seed_a: dict, per_seed_b: dict) -> list[tuple[int, str, bool]]:
    """Return list of (seed, suite_id, match)."""
    all_seeds = sorted(set(per_seed_a) | set(per_seed_b), key=lambda x: (x, str(x)))
    rows = []
    for seed in all_seeds:
        for suite_id in ("protocol_probe_v0_1", "prompt_injection_v0_2"):
            ga = (per_seed_a.get(seed) or {}).get(suite_id) or {}
            gb = (per_seed_b.get(seed) or {}).get(suite_id) or {}
            match = ga.get("gdh_suite") == gb.get("gdh_suite")
            rows.append((seed, suite_id, match))
    return rows


def main() -> None:
    if not DESKTOP_EXPORT.exists():
        print("STOP: desktop export not found:", DESKTOP_EXPORT, file=sys.stderr)
        sys.exit(1)
    if not LAPTOP_EXPORT.exists():
        print("STOP: laptop export not found:", LAPTOP_EXPORT, file=sys.stderr)
        sys.exit(1)

    # Attempted (v0.1)
    report_attempted_d = compute_gdh_for_export(DESKTOP_EXPORT, mode="attempted")
    report_attempted_l = compute_gdh_for_export(LAPTOP_EXPORT, mode="attempted")
    write_report(report_attempted_d, OUT_ATTEMPTED_DESKTOP)
    write_report(report_attempted_l, OUT_ATTEMPTED_LAPTOP)

    # Accepted (v0.2)
    report_accepted_d = compute_gdh_for_export(DESKTOP_EXPORT, mode="accepted")
    report_accepted_l = compute_gdh_for_export(LAPTOP_EXPORT, mode="accepted")
    write_report(report_accepted_d, OUT_ACCEPTED_DESKTOP)
    write_report(report_accepted_l, OUT_ACCEPTED_LAPTOP)

    # Comparison tables
    attempted_rows = per_seed_suite_match(report_attempted_d["per_seed"], report_attempted_l["per_seed"])
    accepted_rows = per_seed_suite_match(report_accepted_d["per_seed"], report_accepted_l["per_seed"])

    print()
    print("A) Attempted mode (v0.1):")
    print("Seed     | Suite                     | gdh_suite match? (Y/N)")
    print("-" * 60)
    for seed, suite_id, match in attempted_rows:
        print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))

    print()
    print("B) Accepted mode (v0.2):")
    print("Seed     | Suite                     | gdh_suite match? (Y/N)")
    print("-" * 60)
    for seed, suite_id, match in accepted_rows:
        print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))

    attempted_differing = sum(1 for _, __, m in attempted_rows if not m)
    accepted_differing = sum(1 for _, __, m in accepted_rows if not m)
    print()
    print("Total differing suites (attempted):", attempted_differing)
    print("Total differing suites (accepted):", accepted_differing)


if __name__ == "__main__":
    main()
