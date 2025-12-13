"""
Metrics snapshot aggregator (Safe Mode, append-only).

Merges key safety signals into a single markdown report:
- Governance status (safe_mode/deny_all, naming rites presence)
- Entropy diagnostics (latest summaries for UCC DDM)
- Outcome Density aggregates (if present)

Outputs:
- reports/metrics_snapshot_<timestamp>.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.calyx_telemetry_logger import now_iso


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def latest_boot() -> Optional[Dict[str, Any]]:
    recs = read_jsonl(Path("logs/bloomos/kernel_boot.jsonl"))
    return recs[-1] if recs else None


def naming_rites_present() -> bool:
    return Path("config/naming_rites_v1.json").exists()


def load_od_aggregate() -> Optional[Dict[str, Any]]:
    # Heuristic: pick the last OD run aggregate in benchmarks/runs
    runs_dir = Path("benchmarks/runs")
    if not runs_dir.exists():
        return None
    aggregates = []
    for p in runs_dir.glob("CB-*-OD-*.jsonl"):
        recs = read_jsonl(p)
        for r in recs:
            if r.get("entry_type") == "aggregate":
                aggregates.append((p, r))
    return aggregates[-1][1] if aggregates else None


def load_entropy_summaries() -> List[str]:
    out = []
    for p in Path("reports/ucc_ddm").glob("summary_v*.md"):
        out.append(f"{p}")
    for p in Path("reports/ucc_ddm_mc").glob("summary_v*.md"):
        out.append(f"{p}")
    return sorted(out)


def main() -> None:
    ts = now_iso()
    report_path = Path("reports") / f"metrics_snapshot_{ts.replace(':','-')}.md"
    lines = ["# Metrics Snapshot", "", f"Generated: {ts}", ""]

    boot = latest_boot()
    lines.append("## Governance")
    if boot:
        lines.append(f"- boot_id: {boot.get('boot_id')}")
        lines.append(f"- safe_mode: {boot.get('safe_mode')}")
        lines.append(f"- deny_all: {boot.get('deny_all')}")
        lines.append(f"- naming_rites_required_at_boot: {boot.get('naming_rites_required')}")
    else:
        lines.append("- No boot records found.")
    lines.append(f"- naming_rites_config_present: {naming_rites_present()}")
    lines.append("")

    lines.append("## Entropy Diagnostics")
    summaries = load_entropy_summaries()
    if summaries:
        lines.append("Latest summaries:")
        for s in summaries[-5:]:
            lines.append(f"- {s}")
    else:
        lines.append("- No entropy summaries found.")
    lines.append("")

    lines.append("## Outcome Density")
    agg = load_od_aggregate()
    if agg:
        lines.append(f"- benchmark_run_id: {agg.get('benchmark_run_id')}")
        lines.append(f"- insight_quality_sum: {agg.get('insight_quality_sum')}")
        lines.append(f"- avg_insight_quality: {agg.get('avg_insight_quality')}")
        lines.append(f"- hallucinations: {agg.get('hallucinations')} (rate {agg.get('hallucination_rate')})")
        lines.append(f"- resource_units_sum: {agg.get('resource_units_sum')}")
        lines.append(f"- outcome_density: {agg.get('outcome_density')}")
        lines.append(f"- quality_only: {agg.get('quality_only')}")
    else:
        lines.append("- No outcome density aggregates found.")
    lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Snapshot written: {report_path}")


if __name__ == "__main__":
    main()
