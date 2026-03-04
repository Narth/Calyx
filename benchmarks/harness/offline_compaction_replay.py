"""
Offline Compaction Replay — Compute-minimizing evaluation for Phase 4B.
Counterfactual: apply compaction rules to baseline (Phase 4A) event logs without re-running LLM or execution.
Does not modify envelopes or metrics.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .plan_compaction import AVG_ACTION_TOKEN_ESTIMATE, compact_plan


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    events = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def build_baseline_manifest(runtime_root: Path) -> list[dict]:
    """
    Locate Phase 4A baseline ladder artifacts (schema 1.2 or 1.3).
    Returns list of {model_id, seed, run_instance_id, envelope_path, events_path, metrics_path}.
    """
    runtime_root = Path(runtime_root)
    autonomous_dir = runtime_root / "benchmarks" / "autonomous"
    logs_dir = runtime_root / "benchmarks" / "execution_logs"
    manifest = []

    if not autonomous_dir.exists():
        return manifest

    for envelope_path in sorted(autonomous_dir.glob("autonomous_exec_v0_1_llm__*.run.json")):
        envelope = _load_json(envelope_path)
        if not isinstance(envelope, dict):
            continue
        schema = envelope.get("schema_version", "")
        if schema not in ("1.2", "1.3"):
            continue
        run_instance_id = envelope.get("run_instance_id", "")
        if not run_instance_id:
            continue
        model_id = envelope.get("model_id", "unknown")
        seed = None
        if "_seed" in run_instance_id:
            try:
                seed = int(run_instance_id.split("_seed")[-1])
            except ValueError:
                pass
        events_name = f"autonomous_exec_v0_1_llm__{run_instance_id}.events.jsonl"
        events_path = logs_dir / events_name
        metrics_path = autonomous_dir / f"autonomous_exec_v0_1_llm__{run_instance_id}.metrics.json"
        manifest.append({
            "model_id": model_id,
            "seed": seed,
            "run_instance_id": run_instance_id,
            "envelope_path": envelope_path,
            "events_path": events_path,
            "metrics_path": metrics_path,
        })
    return manifest


def _extract_plan_from_events(events: list[dict], case_id: str) -> list[dict] | None:
    """
    Try to reconstruct per-case action list from events.
    Returns list of {tool_name, arguments} or None if not reconstructable.
    Prefers plan_committed.plan_actions_snapshot (Phase 4B+ logging).
    """
    for ev in events:
        if ev.get("case_id") != case_id:
            continue
        # plan_committed (Phase 4B+) or plan_actions_snapshot in llm_plan_response
        snapshot = ev.get("plan_actions_snapshot")
        if isinstance(snapshot, list) and snapshot:
            return [{"tool_name": a.get("tool_name", ""), "arguments": a.get("arguments") or {}} for a in snapshot]
        snapshot = ev.get("plan_snapshot")
        if isinstance(snapshot, list) and snapshot:
            return [{"tool_name": a.get("tool_name", ""), "arguments": a.get("arguments") or {}} for a in snapshot]
        actions = ev.get("actions")
        if isinstance(actions, list) and actions:
            return [{"tool_name": a.get("tool_name", ""), "arguments": a.get("arguments") or {}} for a in actions]

    return None


def _group_events_by_case(events: list[dict]) -> dict[str, list[dict]]:
    by_case: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        case_id = ev.get("case_id") or "_no_case"
        by_case[case_id].append(ev)
    return dict(by_case)


def _get_actions_planned_per_case(events: list[dict]) -> dict[str, int]:
    """From llm_plan_response, get actions_planned per case_id."""
    by_case: dict[str, int] = {}
    for ev in events:
        if ev.get("stage") == "llm_plan_response" and ev.get("case_id"):
            by_case[ev["case_id"]] = int(ev.get("actions_planned", 0))
    return by_case


def replay_run(
    events_path: Path,
    *,
    run_instance_id: str = "",
) -> dict:
    """
    Offline compaction replay for one run.
    Returns:
      - per_case: list of {case_id, compactable, dropped_action_count, rules_applied, compaction_aborted, reason, planned_before, planned_after}
      - aggregates: offline_compaction_applied_count, offline_compaction_rate, offline_dropped_action_count, offline_compaction_token_savings_est
      - top_compactable_case_ids: [(case_id, dropped_count), ...]
      - top_patterns: [(tool_sequence_str, count, total_dropped), ...]
      - plan_detail_available: bool (False if events lack plan snapshot)
      - missing_logging: dict describing what is missing (when plan_detail_available is False)
    """
    events = _load_events(events_path)
    by_case = _group_events_by_case(events)
    actions_planned = _get_actions_planned_per_case(events)

    per_case_results: list[dict] = []
    pattern_drops: list[tuple[str, int, int]] = []  # (pattern, count, total_dropped)
    pattern_counts: defaultdict = defaultdict(lambda: {"count": 0, "dropped": 0})
    plan_detail_available = False
    missing_logging: dict[str, Any] = {"stages_checked": [], "missing_fields": []}

    for case_id, case_events in by_case.items():
        planned_before = actions_planned.get(case_id, 0)
        actions = _extract_plan_from_events(case_events, case_id)

        if actions is None:
            if planned_before > 0:
                plan_detail_available = False
            per_case_results.append({
                "case_id": case_id,
                "compactable": False,
                "dropped_action_count": 0,
                "rules_applied": [],
                "compaction_aborted": False,
                "reason": "plan_not_reconstructable",
                "planned_before": planned_before,
                "planned_after": planned_before,
            })
            continue

        plan_detail_available = True
        plan = {"plan_id": case_id, "actions": []}
        for i, a in enumerate(actions):
            plan["actions"].append({
                "action_id": str(i + 1),
                "order": i + 1,
                "tool_name": a.get("tool_name", ""),
                "arguments": a.get("arguments") or {},
            })

        compacted_plan, info = compact_plan(plan, skip_if_uncertain=True)
        dropped = info.get("dropped_action_count", 0)
        applied = info.get("compaction_applied", False)
        aborted = info.get("compaction_aborted", False)
        planned_after = len(compacted_plan.get("actions", []))

        per_case_results.append({
            "case_id": case_id,
            "compactable": applied,
            "dropped_action_count": dropped,
            "rules_applied": info.get("rules_applied", []),
            "compaction_aborted": aborted,
            "reason": info.get("compaction_aborted_reason") or ("ok" if applied else "no_change"),
            "planned_before": planned_before,
            "planned_after": planned_after,
        })

        if applied and dropped > 0:
            seq = tuple(a.get("tool_name", "") for a in plan["actions"])
            pattern_key = " → ".join(seq)
            pattern_counts[pattern_key]["count"] += 1
            pattern_counts[pattern_key]["dropped"] += dropped

    total_planned_before = sum(r["planned_before"] for r in per_case_results)
    total_planned_after = sum(r["planned_after"] for r in per_case_results)
    offline_dropped = sum(r["dropped_action_count"] for r in per_case_results)
    offline_applied_count = sum(1 for r in per_case_results if r["compactable"])

    aggregates = {
        "offline_compaction_applied_count": offline_applied_count,
        "offline_compaction_rate": (total_planned_before - total_planned_after) / max(total_planned_before, 1) if total_planned_before else 0,
        "offline_dropped_action_count": offline_dropped,
        "offline_compaction_token_savings_est": offline_dropped * AVG_ACTION_TOKEN_ESTIMATE,
        "total_cases": len(per_case_results),
        "total_planned_before": total_planned_before,
        "total_planned_after": total_planned_after,
    }

    top_case_ids = sorted(
        [(r["case_id"], r["dropped_action_count"]) for r in per_case_results if r["dropped_action_count"] > 0],
        key=lambda x: -x[1],
    )[:10]

    top_patterns = sorted(
        [(k, v["count"], v["dropped"]) for k, v in pattern_counts.items()],
        key=lambda x: -x[2],
    )[:10]

    if not plan_detail_available and events:
        missing_logging["stages_checked"] = ["llm_plan_response", "task_intake", "plan_generation", "plan_committed", "risk_evaluation", "adapter_invocation"]
        missing_logging["missing_fields"] = [
            "llm_plan_response: has actions_planned (count) only; no plan_actions_snapshot (array of {tool_name, arguments}).",
            "task_intake: has plan_id, action_count only; no action list.",
            "risk_evaluation: has action_id, risk_label; no tool_name or arguments.path.",
            "adapter_invocation: has action_id, adapter_status; no tool_name or arguments.",
        ]
        missing_logging["minimal_addition"] = (
            "Add to llm_plan_response (or a new 'plan_committed' stage after plan_parse) a field: "
            "'plan_actions_snapshot': [{\"tool_name\": \"...\", \"arguments\": {\"path\": \"...\", ...}}, ...] "
            "for each action in the plan, so offline compaction replay can reconstruct and apply rules A–D."
        )

    return {
        "run_instance_id": run_instance_id,
        "per_case": per_case_results,
        "aggregates": aggregates,
        "top_compactable_case_ids": top_case_ids,
        "top_patterns": top_patterns,
        "plan_detail_available": plan_detail_available,
        "missing_logging": missing_logging if not plan_detail_available else {},
    }


def run_offline_replay(runtime_root: Path) -> tuple[list[dict], list[dict], dict]:
    """
    Run offline compaction replay for all baseline runs in manifest.
    Returns (manifest, per_run_results, global_missing_logging).
    """
    manifest = build_baseline_manifest(runtime_root)
    per_run_results: list[dict] = []
    global_missing: dict = {"reported": False, "stages_checked": [], "missing_fields": [], "minimal_addition": ""}

    for entry in manifest:
        run_id = entry["run_instance_id"]
        events_path = entry["events_path"]
        if not events_path.exists():
            continue
        result = replay_run(events_path, run_instance_id=run_id)
        result["model_id"] = entry["model_id"]
        result["seed"] = entry["seed"]
        per_run_results.append(result)
        if result.get("missing_logging") and not global_missing["reported"]:
            global_missing["reported"] = True
            global_missing["stages_checked"] = result["missing_logging"].get("stages_checked", [])
            global_missing["missing_fields"] = result["missing_logging"].get("missing_fields", [])
            global_missing["minimal_addition"] = result["missing_logging"].get("minimal_addition", "")

    return manifest, per_run_results, global_missing


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Offline compaction replay (Phase 4B counterfactual)")
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    parser.add_argument("--report", type=Path, default=None, help="Write report to this path")
    args = parser.parse_args()

    runtime_root = Path(args.runtime_dir)
    manifest, per_run_results, global_missing = run_offline_replay(runtime_root)

    report_path = args.report or runtime_root / "benchmarks" / "reports" / "autonomous_exec_v0_1_llm_OFFLINE_COMPACTION_REPLAY.report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    from .offline_compaction_replay_report import write_report
    write_report(report_path, manifest, per_run_results, global_missing)

    print(f"Manifest: {len(manifest)} baseline runs. Report: {report_path}")
    if global_missing.get("reported"):
        print("Plan detail not in event logs; see report for missing fields and minimal logging addition.")


if __name__ == "__main__":
    main()
