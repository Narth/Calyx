#!/usr/bin/env python3
"""
Summarize logs/agent_metrics.csv to compare tool efficacy across autonomy modes.
Outputs a console table and writes logs/agent_metrics_summary.csv.
"""
from __future__ import annotations
import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "logs" / "agent_metrics.csv"
CSV_OUT = ROOT / "logs" / "agent_metrics_summary.csv"


def _quantiles(arr: list[float], qs=(0.5, 0.9)):
    if not arr:
        return [0.0 for _ in qs]
    arr = sorted(arr)
    out = []
    n = len(arr)
    for q in qs:
        if n == 1:
            out.append(arr[0])
            continue
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(arr[lo] * (1 - frac) + arr[hi] * frac)
    return out


def main() -> int:
    if not CSV_IN.exists():
        print("No metrics CSV found at", CSV_IN)
        return 0

    by_mode: dict[str, dict[str, list[float] | int]] = {}

    with CSV_IN.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            mode = r.get("autonomy_mode") or ""
            if not mode:
                continue
            by_mode.setdefault(mode, {"tes": [], "stability": [], "count": 0})
            try:
                by_mode[mode]["tes"].append(float(r.get("tes", "0")))  # type: ignore[index]
                by_mode[mode]["stability"].append(float(r.get("stability", "0")))  # type: ignore[index]
                by_mode[mode]["count"] = int(by_mode[mode]["count"]) + 1  # type: ignore[index]
            except Exception:
                pass

    # Prepare output
    rows_out = [["mode", "count", "tes_mean", "tes_p50", "tes_p90", "stability_mean"]]
    for mode in sorted(by_mode.keys()):
        tes_list = by_mode[mode]["tes"]  # type: ignore[index]
        stab_list = by_mode[mode]["stability"]  # type: ignore[index]
        cnt = int(by_mode[mode]["count"])  # type: ignore[index]
        p50, p90 = _quantiles(list(tes_list), qs=(0.5, 0.9)) if tes_list else (0.0, 0.0)
        row = [
            mode,
            cnt,
            round(mean(tes_list), 2) if tes_list else 0.0,
            round(p50, 2),
            round(p90, 2),
            round(mean(stab_list), 3) if stab_list else 0.0,
        ]
        rows_out.append(row)

    # Console print
    for r in rows_out:
        print(", ".join(map(str, r)))

    # CSV write
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
