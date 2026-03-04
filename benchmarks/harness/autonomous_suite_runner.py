"""
Autonomous execution benchmark suite runner.
Phase 3A/3B/3C: Loads suite, runs each case, computes metrics, verifies, writes report.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from . import run_envelope
from .autonomous_metrics import compute_metrics
from .autonomous_run import run_single_case
from .autonomous_verifier import verify_run
from .execution_adapter import compute_sandbox_state_hash
from .execution_log import compute_execution_log_hash


def load_suite(suite_path: Path) -> tuple[list[dict], dict]:
    """Load cases.jsonl and manifest.json from suite path."""
    suite_path = Path(suite_path)
    cases: list[dict] = []
    cases_path = suite_path / "cases.jsonl"
    if cases_path.exists():
        with open(cases_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(json.loads(line))
    manifest: dict = {}
    manifest_path = suite_path / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    return cases, manifest


def run_suite(
    suite_path: Path,
    run_id: str,
    run_instance_id: str,
    runtime_root: Path,
    *,
    seed: int | None = None,
) -> dict:
    """
    Run the autonomous_exec_v0_1 suite. Phase 3.
    Returns envelope data with metrics and verification results.
    """
    runtime_root = Path(runtime_root)
    suite_path = Path(suite_path)
    cases, manifest = load_suite(suite_path)
    expected_cases = manifest.get("expected_cases", len(cases))

    logs_dir = runtime_root / "benchmarks" / "execution_logs"
    autonomous_dir = runtime_root / "benchmarks" / "autonomous"
    reports_dir = runtime_root / "benchmarks" / "reports"
    autonomous_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    events_filename = f"{run_id}__{run_instance_id}.events.jsonl"
    log_path = logs_dir / events_filename
    envelope_path = autonomous_dir / f"{run_id}__{run_instance_id}.run.json"
    metrics_path = autonomous_dir / f"{run_id}__{run_instance_id}.metrics.json"
    report_path = reports_dir / f"{run_id}__{run_instance_id}.report.md"
    sandbox_root = runtime_root / "sandbox" / run_id

    run_start_ts = datetime.now(timezone.utc).isoformat()

    total_actions_planned = sum(len(c.get("actions", [])) for c in cases)
    case_summaries: list[dict] = []
    sandbox_hashes: dict[str, str] = {}

    if seed is not None:
        rng = random.Random(seed)
        cases = list(cases)
        rng.shuffle(cases)

    for case in cases:
        case_id = case.get("case_id", "unknown")
        case_sandbox = sandbox_root / case_id
        case_sandbox.mkdir(parents=True, exist_ok=True)
        plan = {
            "plan_id": case_id,
            "actions": case.get("actions", []),
        }
        summary = run_single_case(
            plan=plan,
            case_id=case_id,
            sandbox_root=case_sandbox,
            log_path=log_path,
            run_id=run_id,
        )
        case_summaries.append(summary)
        sandbox_hashes[case_id] = compute_sandbox_state_hash(case_sandbox)

    run_end_ts = datetime.now(timezone.utc).isoformat()
    execution_log_hash = compute_execution_log_hash(log_path)
    receipt_sha256 = run_envelope.compute_file_sha256(log_path)

    executed_total = sum(s["executed_action_count"] for s in case_summaries)
    blocked_total = sum(s["blocked_action_count"] for s in case_summaries)
    modified_total = sum(s["modified_action_count"] for s in case_summaries)

    metrics = compute_metrics(
        log_path=log_path,
        sandbox_root=sandbox_root,
        expected_total_actions=total_actions_planned,
        case_summaries=case_summaries,
    )

    sandbox_state_hash_before = ""
    sandbox_state_hash_after = compute_sandbox_state_hash(sandbox_root)

    envelope_data = {
        "schema_version": "1.2",
        "run_id": run_id,
        "run_instance_id": run_instance_id,
        "suite": manifest.get("suite_id", "autonomous_exec_v0_1"),
        "total_cases_expected": expected_cases,
        "total_cases_completed": len(case_summaries),
        "executed_action_count": executed_total,
        "blocked_action_count": blocked_total,
        "modified_action_count": modified_total,
        "run_start_ts_utc": run_start_ts,
        "run_end_ts_utc": run_end_ts,
        "exit_status": "normal" if len(case_summaries) == expected_cases else "incomplete",
        "sandbox_state_hash_before": sandbox_state_hash_before,
        "sandbox_state_hash_after": sandbox_state_hash_after,
        "execution_log_hash": execution_log_hash,
        "receipt_path": f"runtime/benchmarks/execution_logs/{events_filename}",
        "receipt_sha256": receipt_sha256,
        "metrics": metrics,
    }

    tmp_path = run_envelope.write_run_envelope_tmp(envelope_path, envelope_data)
    run_envelope.finalize_run_envelope(tmp_path, envelope_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    verification = verify_run(
        envelope_data=envelope_data,
        log_path=log_path,
        sandbox_root=sandbox_root,
        expected_cases=expected_cases,
        runtime_root=runtime_root,
    )

    report_lines = [
        "# Autonomous Execution Benchmark Suite Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Run Instance ID:** {run_instance_id}",
        f"**Suite:** {manifest.get('suite_id', 'autonomous_exec_v0_1')}",
        "",
        "## Audit Narrative",
        "",
        "This report documents the autonomous execution benchmark run. Every assertion references an artifact.",
        "",
        "### Artifacts",
        "",
        f"- **Execution log:** `{log_path.relative_to(runtime_root) if log_path.is_relative_to(runtime_root) else log_path}`",
        f"- **Envelope:** `{envelope_path.relative_to(runtime_root) if envelope_path.is_relative_to(runtime_root) else envelope_path}`",
        f"- **Metrics:** `{metrics_path.relative_to(runtime_root) if metrics_path.is_relative_to(runtime_root) else metrics_path}`",
        f"- **Sandbox root:** `{sandbox_root.relative_to(runtime_root) if sandbox_root.is_relative_to(runtime_root) else sandbox_root}`",
        "",
        "### Hashes",
        "",
        f"- **execution_log_hash:** `{execution_log_hash}`",
        f"- **receipt_sha256:** `{receipt_sha256}`",
        f"- **sandbox_state_hash_after:** `{sandbox_state_hash_after}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| execution_allowed_rate | {metrics.get('execution_allowed_rate', 0)} |",
        f"| stabilization_intervention_rate | {metrics.get('stabilization_intervention_rate', 0)} |",
        f"| harmful_action_prevented_count | {metrics.get('harmful_action_prevented_count', 0)} |",
        f"| sandbox_integrity_breach_rate | {metrics.get('sandbox_integrity_breach_rate', 0)} |",
        f"| benefit_completion_rate | {metrics.get('benefit_completion_rate', 0)} |",
        "",
        "## Verification",
        "",
        f"- total_cases_completed: **{'PASS' if verification.get('total_cases_completed', {}).get('pass') else 'FAIL'}** (expected {expected_cases}, actual {len(case_summaries)})",
        f"- execution_log_hash: **{'PASS' if verification.get('execution_log_hash', {}).get('pass') else 'FAIL'}**",
        f"- sandbox_hashes_recorded: **{'PASS' if verification.get('sandbox_hashes_recorded', {}).get('pass') else 'FAIL'}**",
        f"- no_tmp_remains: **{'PASS' if verification.get('no_tmp_remains', {}).get('pass') else 'FAIL'}**",
        "",
    ]
    if verification.get("no_tmp_remains", {}).get("found"):
        report_lines.append("  - Remaining .tmp files: " + ", ".join(verification["no_tmp_remains"]["found"]))
        report_lines.append("")

    report_lines.extend(["", "---", f"Generated: {run_end_ts}"])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    envelope_data["verification"] = verification
    envelope_data["report_path"] = str(report_path)

    return envelope_data


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous execution suite runner (Phase 3)")
    parser.add_argument("--suite-path", type=Path, default=Path("benchmarks/suites/autonomous_exec_v0_1"))
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    parser.add_argument("--run-id", type=str, default="autonomous_exec_v0_1")
    parser.add_argument("--run-instance-id", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    run_instance_id = args.run_instance_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    if args.seed is not None:
        run_instance_id = f"{run_instance_id}_seed{args.seed}"

    envelope = run_suite(
        suite_path=args.suite_path,
        run_id=args.run_id,
        run_instance_id=run_instance_id,
        runtime_root=args.runtime_dir,
        seed=args.seed,
    )
    print(f"Suite run complete. Report: {envelope.get('report_path', '')}")


if __name__ == "__main__":
    main()
