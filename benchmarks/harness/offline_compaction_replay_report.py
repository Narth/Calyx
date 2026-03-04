"""
Report writer for offline compaction replay.
Produces runtime/benchmarks/reports/autonomous_exec_v0_1_llm_OFFLINE_COMPACTION_REPLAY.report.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _aggregate_by_model(per_run_results: list[dict]) -> dict[str, dict]:
    """Aggregate per-run results by model_id (across seeds)."""
    by_model: dict[str, list[dict]] = {}
    for r in per_run_results:
        mid = r.get("model_id", "unknown")
        if mid not in by_model:
            by_model[mid] = []
        by_model[mid].append(r)
    out = {}
    for model_id, runs in by_model.items():
        total_cases = sum(r["aggregates"].get("total_cases", 0) for r in runs)
        total_dropped = sum(r["aggregates"].get("offline_dropped_action_count", 0) for r in runs)
        total_before = sum(r["aggregates"].get("total_planned_before", 0) for r in runs)
        applied_count = sum(r["aggregates"].get("offline_compaction_applied_count", 0) for r in runs)
        rate = total_dropped / max(total_before, 1) if total_before else 0
        out[model_id] = {
            "offline_compaction_rate": rate,
            "offline_dropped_action_count": total_dropped,
            "offline_compaction_token_savings_est": total_dropped * 50,
            "total_cases": total_cases,
            "compactable_cases": applied_count,
            "pct_compactable": (100.0 * applied_count / total_cases) if total_cases else 0,
            "plan_detail_available": any(r.get("plan_detail_available") for r in runs),
        }
    return out


def write_report(
    report_path: Path,
    manifest: list[dict],
    per_run_results: list[dict],
    global_missing: dict,
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    by_model = _aggregate_by_model(per_run_results) if per_run_results else {}

    lines = [
        "# Offline Compaction Replay Report (Phase 4B)",
        "",
        "Compute-minimizing evaluation: counterfactual compaction on Phase 4A baseline event logs.",
        "No LLM calls, no execution, no envelope/metrics modification.",
        "",
        "---",
        "",
        "## 1) Summary table per model (aggregate across seeds)",
        "",
        "| Model | offline_compaction_rate | offline_dropped_action_count | estimated token savings | % cases compactable |",
        "|-------|-------------------------|------------------------------|--------------------------|---------------------|",
    ]

    if not by_model:
        lines.append("| (no baseline runs found) | — | — | — | — |")
    else:
        for model_id, agg in sorted(by_model.items()):
            rate = agg.get("offline_compaction_rate", 0)
            dropped = agg.get("offline_dropped_action_count", 0)
            savings = agg.get("offline_compaction_token_savings_est", 0)
            pct = agg.get("pct_compactable", 0)
            if not agg.get("plan_detail_available"):
                lines.append(f"| {model_id} | N/A (plan not in logs) | 0 | 0 | 0 |")
            else:
                lines.append(f"| {model_id} | {rate:.4f} | {dropped} | {savings} | {pct:.1f}% |")

    lines.extend([
        "",
        "## 2) Top 10 compactable case_ids by dropped_action_count",
        "",
    ])

    all_top_cases: list[tuple[str, int, str]] = []
    for r in per_run_results:
        for case_id, dropped in r.get("top_compactable_case_ids", []):
            all_top_cases.append((case_id, dropped, r.get("model_id", "")))
    all_top_cases.sort(key=lambda x: -x[1])
    top10 = all_top_cases[:10]
    if not top10:
        lines.append("(None — no plan detail in event logs, or no cases were compactable.)")
    else:
        lines.append("| case_id | dropped_action_count | model |")
        lines.append("|---------|------------------------|-------|")
        for case_id, dropped, mid in top10:
            lines.append(f"| {case_id} | {dropped} | {mid} |")

    lines.extend([
        "",
        "## 3) Top 10 most frequent compactable tool-sequence patterns",
        "",
    ])

    pattern_totals: dict[str, list[int]] = {}
    for r in per_run_results:
        for pattern, count, dropped in r.get("top_patterns", []):
            if pattern not in pattern_totals:
                pattern_totals[pattern] = [0, 0]
            pattern_totals[pattern][0] += count
            pattern_totals[pattern][1] += dropped
    top_patterns = sorted(pattern_totals.items(), key=lambda x: -x[1][1])[:10]
    if not top_patterns:
        lines.append("(None — no plan detail in event logs, or no compaction applied.)")
    else:
        lines.append("| Tool sequence | Occurrences | Total dropped |")
        lines.append("|---------------|-------------|---------------|")
        for pattern, (count, dropped) in top_patterns:
            lines.append(f"| {pattern} | {count} | {dropped} |")

    lines.extend([
        "",
        "## 4) Recommendation",
        "",
    ])

    if global_missing.get("reported"):
        lines.append("### Event logs lack plan detail (STOP condition)")
        lines.append("")
        lines.append("**What is missing:**")
        for stage in global_missing.get("stages_checked", []):
            lines.append(f"- Stage `{stage}` was checked.")
        for field_desc in global_missing.get("missing_fields", []):
            lines.append(f"- {field_desc}")
        lines.append("")
        lines.append("**Minimal logging addition for future runs:**")
        lines.append("")
        lines.append(global_missing.get("minimal_addition", ""))
        lines.append("")
        lines.append("**Recommendation:** A full 12-run ladder is **not justified** for quantifying Phase 4B compaction from existing baseline artifacts, because plan actions cannot be reconstructed from event logs. Either:")
        lines.append("1. Add `plan_actions_snapshot` (or equivalent) to the runner’s logging, re-run the Phase 4A ladder to capture baseline with plan detail, then re-run this offline replay; or")
        lines.append("2. Run Phase 4B live (with compaction enabled) and use in-run compaction metrics for comparison (no offline replay).")
        lines.append("")
        lines.append("For minimal live confirmation (STEP 4), running 2 Phase 4B runs (qwen2.5-coder:7b seed 1337, tinyllama seed 1337) will yield absolute compaction metrics; baseline comparison for the same model+seed is not available from current logs.")
    else:
        any_compactable = any(
            r["aggregates"].get("offline_compaction_applied_count", 0) > 0
            for r in per_run_results
        )
        if any_compactable:
            lines.append("Offline replay found compactable plans. **Recommendation:** A full 12-run Phase 4B ladder is justified to confirm compaction impact in live runs. Optional: run minimal live confirmation (2 runs) as in STEP 4.")
        else:
            lines.append("Offline replay found no compactable cases (compaction_rate = 0 or no plans compactable). **Recommendation:** A full 12-run ladder is optional; compaction impact may be small. Minimal live confirmation (2 runs) can still be run to collect absolute compaction metrics.")

    lines.append("")
    lines.append("---")
    lines.append(f"Baseline runs in manifest: {len(manifest)}. Rows processed: {len(per_run_results)}.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
