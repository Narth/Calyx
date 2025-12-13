#!/usr/bin/env python3
"""
TES Recalculator - Simulate graduated stability scoring on historical data.

This script reads historical agent_metrics.csv data and recalculates TES scores
using the new graduated stability scoring model to show the impact of the fix.
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_CSV = ROOT / "logs" / "agent_metrics.csv"
OUTPUT_CSV = ROOT / "logs" / "agent_metrics_recalculated.csv"


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _velocity_score(duration_s: float, fast: float = 90.0, slow: float = 900.0) -> float:
    if duration_s <= fast:
        return 1.0
    if duration_s >= slow:
        return 0.0
    return _clamp01(1.0 - (duration_s - fast) / (slow - fast))


def _footprint_score(changed_files_count: int, small: int = 1, large: int = 10) -> float:
    if changed_files_count <= small:
        return 1.0
    if changed_files_count >= large:
        return 0.0
    return _clamp01(1.0 - (changed_files_count - small) / float(large - small))


def _stability_score_old(status: str, failure: bool) -> float:
    """Original binary stability scoring"""
    return 1.0 if (status == "done" and not failure) else 0.0


def _stability_score_new(status: str, failure: bool, mode: str, applied: bool) -> float:
    """New graduated stability scoring"""
    if status != "done":
        return 0.0
    
    if not failure:
        return 1.0
    
    # Partial credit for tests mode failures when not applied
    if mode == "tests" and not applied:
        return 0.6
    
    # Severe penalty for apply mode failures
    if mode in ("apply", "apply_tests") and applied:
        return 0.2
    
    return 0.0


def recalculate_row(row: Dict[str, str]) -> Dict[str, any]:
    """Recalculate TES scores for a single row"""
    try:
        # Parse data
        status = row.get("status", "")
        # Infer failure from stability (CSV doesn't have failure column)
        stability_old_val = float(row.get("stability", "1.0"))
        failure = (stability_old_val == 0.0)
        autonomy_mode = row.get("autonomy_mode", "safe")
        applied = str(row.get("applied", "0")).lower() in ("1", "true", "yes")
        duration_s = float(row.get("duration_s", 0))
        changed_files = int(row.get("changed_files", 0))
        
        # Calculate components
        stability_old = _stability_score_old(status, failure)
        stability_new = _stability_score_new(status, failure, autonomy_mode, applied)
        velocity = _velocity_score(duration_s)
        footprint = _footprint_score(changed_files)
        
        # Calculate TES
        tes_old = round(100.0 * (0.5 * stability_old + 0.3 * velocity + 0.2 * footprint), 1)
        tes_new = round(100.0 * (0.5 * stability_new + 0.3 * velocity + 0.2 * footprint), 1)
        
        # Return updated row
        result = row.copy()
        result["tes_old"] = tes_old
        result["tes_new"] = tes_new
        result["stability_old"] = stability_old
        result["stability_new"] = stability_new
        result["delta"] = round(tes_new - tes_old, 1)
        
        return result
        
    except Exception as e:
        print(f"Error processing row: {e}")
        return row


def main():
    """Main recalculation process"""
    if not LOG_CSV.exists():
        print(f"Error: {LOG_CSV} not found")
        return
    
    print(f"Reading historical data from {LOG_CSV}")
    
    rows = []
    with LOG_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            rows.append(row)
    
    print(f"Found {len(rows)} historical records")
    print("Recalculating TES scores with graduated stability...")
    
    # Recalculate all rows
    recalculated = []
    for row in rows:
        recalculated.append(recalculate_row(row))
    
    # Compute statistics
    tests_mode_count = sum(1 for r in recalculated if r.get("autonomy_mode") == "tests")
    improvements = [r for r in recalculated if r.get("delta", 0) > 0]
    
    if improvements:
        avg_improvement = sum(r.get("delta", 0) for r in improvements) / len(improvements)
        max_improvement = max(r.get("delta", 0) for r in improvements)
        print(f"\nRecalculation complete!")
        print(f"Tests mode records: {tests_mode_count}")
        print(f"Records improved: {len(improvements)}")
        print(f"Average improvement: +{avg_improvement:.1f}")
        print(f"Maximum improvement: +{max_improvement:.1f}")
    
    # Write output
    print(f"\nWriting recalculated data to {OUTPUT_CSV}")
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        fieldnames = headers + ["tes_old", "tes_new", "stability_old", "stability_new", "delta"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(recalculated)
    
    print(f"Done! Output written to {OUTPUT_CSV}")
    
    # Show sample comparisons
    print("\n" + "="*80)
    print("Sample Comparisons (Last 10 Tests Mode Records)")
    print("="*80)
    
    tests_records = [r for r in recalculated if r.get("autonomy_mode") == "tests"][-10:]
    for r in tests_records:
        print(f"TES: {r.get('tes_old', 'N/A'):>6} -> {r.get('tes_new', 'N/A'):>6} "
              f"(delta: {r.get('delta', 0):+.1f}) | "
              f"Stability: {r.get('stability_old', 0):.1f} -> {r.get('stability_new', 0):.1f}")


if __name__ == "__main__":
    main()

