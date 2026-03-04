#!/usr/bin/env python3
"""
Run GDH v0.4 (system_split) on desktop and laptop exports, write reports,
print action and temperament hash comparison tables.
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
compute_gdh_for_export = _gdh.compute_gdh_for_export

DESKTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\desktop_ladder_20260216")
LAPTOP_EXPORT = Path(r"C:\Calyx_Terminal\exports\laptop_ladder_20260216")
FORENSICS_DIR = REPO_ROOT / "runtime" / "benchmarks" / "results" / "forensics"
OUT_DESKTOP = FORENSICS_DIR / "gdh_systemsplit_desktop_20260216.json"
OUT_LAPTOP = FORENSICS_DIR / "gdh_systemsplit_laptop_20260216.json"


def main() -> None:
    if not DESKTOP_EXPORT.exists():
        print("STOP: desktop export not found:", DESKTOP_EXPORT, file=sys.stderr)
        sys.exit(1)
    if not LAPTOP_EXPORT.exists():
        print("STOP: laptop export not found:", LAPTOP_EXPORT, file=sys.stderr)
        sys.exit(1)

    report_d = compute_gdh_for_export(DESKTOP_EXPORT, mode="system_split")
    report_l = compute_gdh_for_export(LAPTOP_EXPORT, mode="system_split")

    FORENSICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DESKTOP, "w", encoding="utf-8") as f:
        json.dump(report_d, f, indent=2, ensure_ascii=False)
    with open(OUT_LAPTOP, "w", encoding="utf-8") as f:
        json.dump(report_l, f, indent=2, ensure_ascii=False)
    print("Wrote:", OUT_DESKTOP)
    print("Wrote:", OUT_LAPTOP)

    per_d = report_d["per_seed"]
    per_l = report_l["per_seed"]
    all_seeds = sorted(set(per_d) | set(per_l), key=lambda x: (str(x), x))

    print()
    print("A) Action hash match table:")
    print("Seed     | Suite                     | gdh_action_suite match? (Y/N)")
    print("-" * 65)
    for seed in all_seeds:
        sk = str(seed)
        for suite_id in ("protocol_probe_v0_1", "prompt_injection_v0_2"):
            gd = (per_d.get(seed) or per_d.get(sk) or {}).get(suite_id) or {}
            gl = (per_l.get(seed) or per_l.get(sk) or {}).get(suite_id) or {}
            match = gd.get("gdh_action_suite") == gl.get("gdh_action_suite")
            print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))

    print()
    print("B) Temperament hash match table:")
    print("Seed     | Suite                     | gdh_temperament_suite match? (Y/N)")
    print("-" * 68)
    for seed in all_seeds:
        sk = str(seed)
        for suite_id in ("protocol_probe_v0_1", "prompt_injection_v0_2"):
            gd = (per_d.get(seed) or per_d.get(sk) or {}).get(suite_id) or {}
            gl = (per_l.get(seed) or per_l.get(sk) or {}).get(suite_id) or {}
            match = gd.get("gdh_temperament_suite") == gl.get("gdh_temperament_suite")
            print("%-8s | %-25s | %s" % (seed, suite_id, "Y" if match else "N"))


if __name__ == "__main__":
    main()
