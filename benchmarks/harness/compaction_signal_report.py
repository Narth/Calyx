"""
Compaction signal report — capability-based report for plan compaction metrics.
Aggregates compaction_applied_count, compaction_rate, rules_applied, per-model breakdown.
"""
from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _find_artifacts(runtime_root: Path, run_id: str) -> list[dict]:
    """Find run.json, metrics.json, events.jsonl for run_id."""
    autonomous_dir = runtime_root / "benchmarks" / "autonomous"
    logs_dir = runtime_root / "benchmarks" / "execution_logs"
    artifacts = []
    if not autonomous_dir.exists():
        return artifacts
    for run_path in autonomous_dir.glob(f"{run_id}__*.run.json"):
        instance_id = run_path.name.replace(f"{run_id}__", "").replace(".run.json", "")
        metrics_path = autonomous_dir / f"{run_id}__{instance_id}.metrics.json"
        events_path = logs_dir / f"{run_id}__{instance_id}.events.jsonl"
        artifacts.append({
            "run_path": run_path,
            "metrics_path": metrics_path,
            "events_path": events_path,
            "instance_id": instance_id,
        })
    return sorted(artifacts, key=lambda x: x["instance_id"])


def _rules_applied_counts(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in events:
        if ev.get("stage") != "plan_compaction":
            continue
        for rule in ev.get("rules_applied", []):
            counts[rule] = counts.get(rule, 0) + 1
    return counts


def _failures_by_case(events: list[dict]) -> list[dict]:
    failures = []
    case_status: dict[str, dict] = {}
    for ev in events:
        case_id = ev.get("case_id", "")
        if not case_id:
            continue
        if ev.get("stage") == "adapter_invocation" and ev.get("adapter_status") != "success":
            case_status[case_id] = case_status.get(case_id, {})
            case_status[case_id]["adapter_fail"] = True
        if ev.get("stage") == "state_validation" and ev.get("integrity_ok") is False:
            case_status[case_id] = case_status.get(case_id, {})
            case_status[case_id]["integrity_fail"] = True
        if ev.get("stage") == "plan_parse_failure":
            case_status[case_id] = case_status.get(case_id, {})
            case_status[case_id]["parse_fail"] = True
    for case_id, status in case_status.items():
        if status:
            failures.append({"case_id": case_id, **status})
    return failures


def _runtime_seconds(env: dict) -> float:
    try:
        start = env.get("run_start_ts_utc", "").replace("Z", "+00:00")
        end = env.get("run_end_ts_utc", "").replace("Z", "+00:00")
        if start and end:
            from datetime import datetime
            return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    except Exception:
        pass
    return 0.0


def write_compaction_signal_report(
    runtime_root: Path,
    run_id: str,
    *,
    valid_runs: list[dict] | None = None,
    report_filename: str | None = None,
    title: str = "Compaction Signal Report",
    subtitle: str | None = None,
) -> Path:
    """
    Produce compaction signal report from run artifacts.
    When valid_runs provided, use only those (already verified). Otherwise find and filter internally.
    """
    runtime_root = Path(runtime_root)
    filename = report_filename or f"{run_id}_compaction_signal.report.md"
    report_path = runtime_root / "benchmarks" / "reports" / filename
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if valid_runs is not None:
        artifacts = [
            {
                "run_path": r.get("run_path") or r.get("envelope_path"),
                "metrics_path": r.get("metrics_path"),
                "events_path": r.get("events_path"),
                "instance_id": r.get("instance_id", ""),
                "envelope_data": r.get("envelope_data", _load_json(r.get("run_path") or r.get("envelope_path"))),
            }
            for r in valid_runs
        ]
    else:
        raw = _find_artifacts(runtime_root, run_id)
        artifacts = []
        for art in raw:
            run_data = _load_json(art["run_path"])
            if run_data.get("exit_status") != "normal":
                continue
            if run_data.get("total_cases_completed") != run_data.get("total_cases_expected"):
                continue
            verif = run_data.get("verification", {}).get("overall", {})
            if not verif.get("pass"):
                continue
            art["envelope_data"] = run_data
            artifacts.append(art)

    compaction_applied_count = 0
    total_planned_before = 0
    dropped_action_count = 0
    token_savings_est = 0
    rules_counts: dict[str, int] = {}
    all_top_cases: list[tuple[str, int, str]] = []
    benefit_rates: list[float] = []
    stabilization_rates: list[float] = []
    sandbox_breach_rates: list[float] = []
    failures: list[dict] = []
    schema_versions: list[str] = []
    verifier_pass: list[bool] = []
    per_model: dict[str, dict] = {}

    for art in artifacts:
        run_data = art.get("envelope_data") or _load_json(art["run_path"])
        metrics = _load_json(art["metrics_path"])
        events = _load_events(art["events_path"])
        model_id = run_data.get("model_id", "")

        compaction_applied_count += metrics.get("compaction_applied_count", 0)
        dropped_action_count += metrics.get("dropped_action_count", 0)
        token_savings_est += metrics.get("compaction_token_savings_est", 0)
        total_planned_before += metrics.get("total_actions_planned", 0) + metrics.get("dropped_action_count", 0)
        benefit_rates.append(metrics.get("benefit_completion_rate", 0))
        stabilization_rates.append(metrics.get("stabilization_intervention_rate", 0))
        sandbox_breach_rates.append(metrics.get("sandbox_integrity_breach_rate", 0))

        for k, v in _rules_applied_counts(events).items():
            rules_counts[k] = rules_counts.get(k, 0) + v

        for ev in events:
            if ev.get("stage") == "plan_compaction":
                case_id = ev.get("case_id", "")
                dropped = len(ev.get("dropped_action_ids", []))
                if dropped > 0:
                    all_top_cases.append((case_id, dropped, ev.get("model_id", model_id)))
        failures.extend(_failures_by_case(events))
        schema_versions.append(run_data.get("schema_version", ""))
        verifier_pass.append(True)

        per_model[model_id] = {
            "compaction_applied_count": metrics.get("compaction_applied_count", 0),
            "compaction_rate": metrics.get("compaction_rate", 0),
            "dropped_action_count": metrics.get("dropped_action_count", 0),
            "compaction_token_savings_est": metrics.get("compaction_token_savings_est", 0),
            "rules_applied": _rules_applied_counts(events),
            "top_cases": sorted(
                [(ev.get("case_id"), len(ev.get("dropped_action_ids", [])), model_id)
                 for ev in events if ev.get("stage") == "plan_compaction" and len(ev.get("dropped_action_ids", [])) > 0],
                key=lambda x: -x[1],
            )[:10],
            "benefit_completion_rate": metrics.get("benefit_completion_rate", 0),
            "stabilization_intervention_rate": metrics.get("stabilization_intervention_rate", 0),
            "sandbox_integrity_breach_rate": metrics.get("sandbox_integrity_breach_rate", 0),
            "total_runtime_seconds": _runtime_seconds(run_data),
            "schema_version": run_data.get("schema_version", ""),
            "execution_log_hash": run_data.get("execution_log_hash", ""),
        }

    compaction_rate = dropped_action_count / max(total_planned_before, 1) if total_planned_before else 0.0
    benefit_completion_rate = sum(benefit_rates) / len(benefit_rates) if benefit_rates else 0.0
    stabilization_intervention_rate = sum(stabilization_rates) / len(stabilization_rates) if stabilization_rates else 0.0
    sandbox_integrity_breach_rate = max(sandbox_breach_rates) if sandbox_breach_rates else 0.0
    top_cases = sorted(all_top_cases, key=lambda x: -x[1])[:10]

    rules_lines = [f"- {r}: {c}" for r, c in sorted(rules_counts.items())]
    if not rules_lines:
        rules_lines = ["- (none applied)"]

    lines = [
        f"# {title}",
        "",
        subtitle or f"Run ID: {run_id}. Aggregated compaction metrics.",
        "",
        "---",
        "",
        "## Summary table",
        "",
        "| Model | compaction_applied | compaction_rate | dropped | token_savings | runtime (s) | schema | execution_log_hash |",
        "|-------|--------------------|-----------------|---------|---------------|-------------|--------|--------------------|",
    ]
    for mid, pm in sorted(per_model.items()):
        h = (pm.get("execution_log_hash") or "")[:16]
        lines.append(
            f"| {mid} | {pm.get('compaction_applied_count', 0)} | {pm.get('compaction_rate', 0):.4f} | "
            f"{pm.get('dropped_action_count', 0)} | {pm.get('compaction_token_savings_est', 0)} | "
            f"{pm.get('total_runtime_seconds', 0):.0f} | {pm.get('schema_version', '')} | {h}... |"
        )

    lines.extend(["", "## Per-model breakdown", ""])
    for mid, pm in sorted(per_model.items()):
        lines.extend([
            f"### {mid}",
            "",
            f"- compaction_applied_count: {pm.get('compaction_applied_count', 0)}",
            f"- compaction_rate: {pm.get('compaction_rate', 0)}",
            f"- dropped_action_count: {pm.get('dropped_action_count', 0)}",
            f"- rules_applied: {pm.get('rules_applied', {})}",
            f"- top compacted case_ids: {[(c, d) for c, d, _ in pm.get('top_cases', [])]}",
            f"- benefit_completion_rate: {pm.get('benefit_completion_rate', 0)}",
            f"- stabilization_intervention_rate: {pm.get('stabilization_intervention_rate', 0)}",
            f"- sandbox_integrity_breach_rate: {pm.get('sandbox_integrity_breach_rate', 0)}",
            f"- total_runtime_seconds: {pm.get('total_runtime_seconds', 0):.0f}",
            f"- execution_log_hash: {pm.get('execution_log_hash', '')}",
            "",
        ])

    lines.extend([
        "## Aggregated metrics",
        "",
        f"- compaction_applied_count: {compaction_applied_count}",
        f"- compaction_rate: {compaction_rate}",
        f"- dropped_action_count: {dropped_action_count}",
        f"- compaction_token_savings_est: {token_savings_est}",
        "",
        "## Rules applied (A-D)",
        "",
    ] + rules_lines + [
        "",
        "## Top 10 case_ids by dropped_action_count",
        "",
        "| case_id | dropped | model |",
        "|---------|---------|-------|",
    ])
    for case_id, dropped, mid in top_cases:
        lines.append(f"| {case_id} | {dropped} | {mid} |")
    if not top_cases:
        lines.append("| (none) | - | - |")

    lines.extend([
        "",
        "## Benefit & stabilization",
        "",
        f"- benefit_completion_rate: {benefit_completion_rate}",
        f"- stabilization_intervention_rate: {stabilization_intervention_rate}",
        f"- sandbox_integrity_breach_rate: {sandbox_integrity_breach_rate}",
        "",
        "## Failures (if any)",
        "",
    ])
    if failures:
        for f in failures:
            lines.append(f"- case_id={f.get('case_id')}: {f}")
    else:
        lines.append("- None")

    if sandbox_integrity_breach_rate > 0:
        rec = "**Abort** — sandbox_integrity_breach_rate > 0."
    elif dropped_action_count > 0:
        rec = "**Run full ladder** — compaction signal positive, safety invariants intact."
    elif len(artifacts) >= 2:
        rec = "**Do not run full ladder** — compaction_rate=0. Consider expand compaction rules."
    else:
        rec = "**Incomplete** — awaiting valid artifacts."

    lines.extend([
        "",
        "## Recommendation",
        "",
        rec,
        "",
        "## Artifacts",
        "",
        f"- Runs found: {len(artifacts)}",
        f"- schema_version: {schema_versions}",
        "",
        "---",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
