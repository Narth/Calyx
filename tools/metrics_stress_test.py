#!/usr/bin/env python3
"""
Stress-test harness for Calyx core metrics.

Generates synthetic agent run data, evaluates TES and AREI behaviour,
and records scenario summaries for research mode analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
AREI_SCRIPT = ROOT / "tools" / "agent_resilience_monitor.py"

CSV_HEADER = [
    "iso_ts",
    "tes",
    "stability",
    "velocity",
    "footprint",
    "duration_s",
    "status",
    "applied",
    "changed_files",
    "run_tests",
    "autonomy_mode",
    "model_id",
    "run_dir",
    "hint",
    "compliance",
    "ethics",
    "coherence",
    "tes_v3",
    "tes_schema",
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def lerp(value: float, low: float, high: float, invert: bool = False) -> float:
    value = clamp((value - low) / (high - low), 0.0, 1.0)
    return 1.0 - value if invert else value


def synthesize_rows(
    count: int,
    success_ratio: float,
    duration_range: Tuple[float, float],
    change_range: Tuple[int, int],
    compliance_range: Tuple[float, float],
    ethics_range: Tuple[float, float],
    modes: Tuple[str, ...],
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for idx in range(count):
        success = random.random() < success_ratio
        duration = random.uniform(*duration_range)
        changed_files = random.randint(*change_range)
        compliance = random.uniform(*compliance_range)
        ethics = random.uniform(*ethics_range)
        stability = 1.0 if success else 0.0
        velocity = lerp(duration, 90.0, 900.0, invert=True)
        footprint = lerp(changed_files, 1.0, 10.0, invert=True)
        tes = 100.0 * (0.5 * stability + 0.3 * velocity + 0.2 * footprint)
        coherence = min(1.0, (compliance + ethics) / 2.0)

        row = {
            "iso_ts": (datetime.now(timezone.utc)).isoformat(),
            "tes": f"{tes:.2f}",
            "stability": f"{stability:.2f}",
            "velocity": f"{velocity:.3f}",
            "footprint": f"{footprint:.3f}",
            "duration_s": f"{duration:.2f}",
            "status": "done" if success else "error",
            "applied": "1" if success and random.random() < 0.5 else "0",
            "changed_files": str(changed_files),
            "run_tests": "1" if random.random() < 0.4 else "0",
            "autonomy_mode": random.choice(modes),
            "model_id": "simulated-metric",
            "run_dir": f"synthetic/run_{idx}",
            "hint": "",
            "compliance": f"{clamp(compliance):.3f}",
            "ethics": f"{clamp(ethics):.3f}",
            "coherence": f"{clamp(coherence):.3f}",
            "tes_v3": "",
            "tes_schema": "v2.5",
        }
        rows.append(row)
    return rows


def write_metrics_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def run_arei(csv_path: Path, window: int) -> Dict:
    env = os.environ.copy()
    env["CALYX_METRICS_CSV"] = str(csv_path)
    env["CALYX_AREI_LOG"] = str(csv_path.with_suffix(".arei.log"))
    proc = subprocess.run(
        [sys.executable, str(AREI_SCRIPT), "--window", str(window), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"AREI monitor failed: {proc.stderr.strip()}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    snapshot = json.loads(lines[0])
    return snapshot


def summarize_tes(rows: List[Dict[str, str]]) -> Dict[str, Dict]:
    buckets: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        mode = row["autonomy_mode"]
        buckets.setdefault(mode, {"tes": [], "stability": []})
        buckets[mode]["tes"].append(float(row["tes"]))
        buckets[mode]["stability"].append(float(row["stability"]))
    out: Dict[str, Dict] = {}
    for mode, vals in buckets.items():
        tes_values = vals["tes"]
        stab_values = vals["stability"]
        out[mode] = {
            "count": len(tes_values),
            "tes_mean": round(statistics.mean(tes_values), 2) if tes_values else 0.0,
            "tes_p50": round(statistics.median(tes_values), 2) if tes_values else 0.0,
            "tes_p90": round(percentile(tes_values, 0.9), 2) if tes_values else 0.0,
            "stability_mean": round(statistics.mean(stab_values), 3) if stab_values else 0.0,
        }
    return out


def percentile(data: List[float], q: float) -> float:
    if not data:
        return 0.0
    ordered = sorted(data)
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def scenario_configs() -> Dict[str, Dict]:
    return {
        "baseline_green": dict(
            count=200,
            success_ratio=0.98,
            duration_range=(60.0, 140.0),
            change_range=(0, 2),
            compliance_range=(0.92, 1.0),
            ethics_range=(0.92, 1.0),
            modes=("tests", "apply_tests", "safe"),
        ),
        "degraded_stability": dict(
            count=200,
            success_ratio=0.6,
            duration_range=(120.0, 600.0),
            change_range=(0, 6),
            compliance_range=(0.55, 0.85),
            ethics_range=(0.4, 0.9),
            modes=("tests", "apply_tests"),
        ),
        "resource_pressure": dict(
            count=200,
            success_ratio=0.85,
            duration_range=(400.0, 1200.0),
            change_range=(4, 15),
            compliance_range=(0.8, 0.95),
            ethics_range=(0.75, 0.92),
            modes=("tests", "apply_tests"),
        ),
    }


def run_scenarios(window: int) -> Dict[str, Dict]:
    results: Dict[str, Dict] = {}
    cfgs = scenario_configs()
    with tempfile.TemporaryDirectory(prefix="calyx_metrics_stress_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        for name, cfg in cfgs.items():
            rows = synthesize_rows(**cfg)
            csv_path = tmpdir_path / f"{name}.csv"
            write_metrics_csv(csv_path, rows)
            arei_snapshot = run_arei(csv_path, window)
            tes_summary = summarize_tes(rows)
            reliability = round(sum(1 for r in rows if r["status"] == "done") / len(rows), 3)
            results[name] = {
                "arei_snapshot": arei_snapshot,
                "tes_summary": tes_summary,
                "reliability": reliability,
                "sample_size": len(rows),
            }
    return results


def write_report(results: Dict[str, Dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "window": max(results.values(), key=lambda r: r["arei_snapshot"]["window"])["arei_snapshot"]["window"]
        if results
        else 0,
        "scenarios": results,
    }
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stress test Calyx metrics using synthetic data.")
    parser.add_argument("--window", type=int, default=50, help="AREI window size to evaluate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "metrics_stress_test_latest.json",
        help="Path to write JSON results.",
    )
    args = parser.parse_args()

    random.seed(0xC4111)
    results = run_scenarios(args.window)
    write_report(results, args.output)

    # Console summary
    for name, data in results.items():
        snap = data["arei_snapshot"]
        print(
            f"[{name}] AREI={snap['arei']} integrity={snap['integrity_of_self']} "
            f"empathy={snap['empathic_alignment']} sustainability={snap['sustainability']} "
            f"reliability={data['reliability']}"
        )
        for mode, summary in data["tes_summary"].items():
            print(
                f"  - {mode}: count={summary['count']} tes_mean={summary['tes_mean']} "
                f"tes_p50={summary['tes_p50']} tes_p90={summary['tes_p90']} "
                f"stability={summary['stability_mean']}"
            )
    print(f"\nResults written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
