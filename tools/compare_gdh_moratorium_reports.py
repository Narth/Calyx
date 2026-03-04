#!/usr/bin/env python3
"""
Read GDH system_split moratorium reports (desktop + laptop) and print comparison tables.
A) Action hash match per seed+suite; B) Temperament hash match; run-level gdh_action_run / gdh_temperament_run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FORENSICS = REPO / "runtime" / "benchmarks" / "results" / "forensics"
DEFAULT_DESKTOP = FORENSICS / "gdh_systemsplit_desktop_20260216_moratorium.json"
DEFAULT_LAPTOP = FORENSICS / "gdh_systemsplit_laptop_20260216_moratorium.json"
SUITES = ("protocol_probe_v0_1", "prompt_injection_v0_2")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare GDH system_split reports (desktop vs laptop).")
    ap.add_argument("--desktop", type=Path, default=DEFAULT_DESKTOP, help="Desktop report JSON path.")
    ap.add_argument("--laptop", type=Path, default=DEFAULT_LAPTOP, help="Laptop report JSON path.")
    args = ap.parse_args()
    desktop_json = args.desktop.resolve()
    laptop_json = args.laptop.resolve()

    if not desktop_json.exists():
        print("STOP: desktop report missing:", desktop_json, file=sys.stderr)
        sys.exit(1)
    if not laptop_json.exists():
        print("STOP: laptop report missing:", laptop_json, file=sys.stderr)
        sys.exit(1)

    with open(desktop_json, "r", encoding="utf-8") as f:
        report_d = json.load(f)
    with open(laptop_json, "r", encoding="utf-8") as f:
        report_l = json.load(f)

    per_d = report_d.get("per_seed") or {}
    per_l = report_l.get("per_seed") or {}
    all_seeds = sorted(set(per_d) | set(per_l), key=lambda x: (str(x), x))

    print("A) Action hash match table (per seed+suite)")
    print("Seed     | Suite                     | Match?")
    print("-" * 55)
    for seed in all_seeds:
        for suite_id in SUITES:
            gd = (per_d.get(seed) or per_d.get(str(seed)) or {}).get(suite_id) or {}
            gl = (per_l.get(seed) or per_l.get(str(seed)) or {}).get(suite_id) or {}
            match = gd.get("gdh_action_suite") == gl.get("gdh_action_suite")
            print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))

    print()
    print("B) Temperament hash match table (per seed+suite)")
    print("Seed     | Suite                     | Match?")
    print("-" * 55)
    for seed in all_seeds:
        for suite_id in SUITES:
            gd = (per_d.get(seed) or per_d.get(str(seed)) or {}).get(suite_id) or {}
            gl = (per_l.get(seed) or per_l.get(str(seed)) or {}).get(suite_id) or {}
            match = gd.get("gdh_temperament_suite") == gl.get("gdh_temperament_suite")
            print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))

    print()
    print("Run-level")
    action_d = report_d.get("gdh_action_run") or ""
    action_l = report_l.get("gdh_action_run") or ""
    temp_d = report_d.get("gdh_temperament_run") or ""
    temp_l = report_l.get("gdh_temperament_run") or ""
    print("gdh_action_run     desktop: %s" % action_d)
    print("gdh_action_run     laptop:  %s" % action_l)
    print("gdh_action_run     Match? %s" % ("Y" if action_d == action_l else "N"))
    print()
    print("gdh_temperament_run desktop: %s" % temp_d)
    print("gdh_temperament_run laptop:  %s" % temp_l)
    print("gdh_temperament_run Match? %s" % ("Y" if temp_d == temp_l else "N"))


if __name__ == "__main__":
    main()
