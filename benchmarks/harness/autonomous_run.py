"""
Autonomous execution run orchestrator.
Phase 2B: Deterministic policy evaluation + stabilization for allow_modified.
Produces envelope schema_version 1.2 with sandbox and execution_log hashes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from . import run_envelope
from .action_schema import normalize_action
from .execution_adapter import ExecutionAdapter, compute_sandbox_state_hash
from .execution_log import append_event, compute_execution_log_hash
from .policy_eval import evaluate as policy_evaluate
from .stabilize import stabilize_action


def _payload_with_case(payload: dict | None, case_id: str | None) -> dict:
    """Merge case_id into payload for suite logging."""
    out = dict(payload) if payload else {}
    if case_id:
        out["case_id"] = case_id
    return out


def run_single_case(
    plan: dict,
    case_id: str,
    sandbox_root: Path,
    log_path: Path,
    run_id: str,
) -> dict:
    """
    Execute one case of an autonomous suite. Appends events to log_path with case_id.
    Returns case summary: executed_action_count, blocked_action_count, modified_action_count.
    """
    sandbox_root = Path(sandbox_root)
    sandbox_root.mkdir(parents=True, exist_ok=True)
    raw_actions = plan.get("actions", [])
    actions: list[dict] = []
    for i, a in enumerate(raw_actions):
        na = normalize_action(a)
        na["order"] = na.get("order") or i
        actions.append(na)

    append_event(
        log_path,
        run_id,
        "task_intake",
        payload=_payload_with_case({"plan_id": plan.get("plan_id", ""), "action_count": len(actions)}, case_id),
    )
    append_event(
        log_path,
        run_id,
        "plan_generation",
        payload=_payload_with_case({"action_count": len(actions)}, case_id),
    )

    evaluations: list[dict] = []
    for action in actions:
        ev = policy_evaluate(action, sandbox_root)
        evaluations.append(ev)
        append_event(
            log_path,
            run_id,
            "risk_evaluation",
            action_id=action.get("action_id"),
            decision_type=ev["decision_type"],
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload=_payload_with_case({
                "modified_action": ev.get("modified_action"),
                "stabilization_mechanism": ev.get("stabilization_mechanism"),
            }, case_id),
        )

    actions_to_execute: list[tuple[dict, dict, bool]] = []
    blocked_action_count = 0
    modified_action_count = 0

    for action, ev in zip(actions, evaluations):
        dt = ev["decision_type"]
        if dt == "allow":
            actions_to_execute.append((action, ev, False))
            continue
        s_dt, s_action, s_mechanism, s_reason = stabilize_action(action, ev, sandbox_root)
        append_event(
            log_path,
            run_id,
            "stabilization",
            action_id=action.get("action_id"),
            decision_type=s_dt,
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload=_payload_with_case({
                "original_action": action,
                "modified_action": s_action,
                "stabilization_mechanism": s_mechanism,
                "stabilization_reason": s_reason,
            }, case_id),
        )
        if s_dt == "allow_modified" and s_action is not None:
            actions_to_execute.append((s_action, {**ev, "decision_type": "allow_modified"}, True))
            modified_action_count += 1
        else:
            blocked_action_count += 1

    adapter = ExecutionAdapter(sandbox_root)
    results: list[dict] = []

    for action, ev, is_modified in actions_to_execute:
        result = adapter.execute(action)
        results.append(result)
        append_event(
            log_path,
            run_id,
            "adapter_invocation",
            action_id=action.get("action_id"),
            decision_type=ev["decision_type"],
            adapter_status=result.get("adapter_status", "error"),
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload=_payload_with_case({"output_hash": result.get("output_hash"), "was_modified": is_modified}, case_id),
        )

    executed_action_count = len(results)
    append_event(
        log_path,
        run_id,
        "state_validation",
        payload=_payload_with_case({
            "integrity_ok": all(r.get("adapter_status") == "success" for r in results),
            "completed_action_count": executed_action_count,
            "total_evaluated": len(actions),
            "blocked_count": blocked_action_count,
            "modified_count": modified_action_count,
        }, case_id),
    )
    stabilization_event_count = blocked_action_count + modified_action_count
    event_count = 2 + len(actions) + stabilization_event_count + executed_action_count + 1
    append_event(
        log_path,
        run_id,
        "receipt_logging",
        payload=_payload_with_case({
            "event_count": event_count,
            "executed_action_count": executed_action_count,
            "modified_action_count": modified_action_count,
        }, case_id),
    )

    return {
        "case_id": case_id,
        "executed_action_count": executed_action_count,
        "blocked_action_count": blocked_action_count,
        "modified_action_count": modified_action_count,
        "total_actions": len(actions),
    }


def run_autonomous(
    plan: dict,
    run_id: str,
    run_instance_id: str,
    runtime_root: Path,
) -> dict:
    """
    Execute an autonomous run. Phase 2B: policy evaluation + stabilization.
    allow → execute original; allow_modified → execute modified_action; block → no execution.
    Returns envelope data (including 1.2 fields).
    """
    runtime_root = Path(runtime_root)
    sandbox_root = runtime_root / "sandbox" / run_id
    logs_dir = runtime_root / "benchmarks" / "execution_logs"
    autonomous_dir = runtime_root / "benchmarks" / "autonomous"
    autonomous_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    events_filename = f"{run_id}__{run_instance_id}.events.jsonl"
    log_path = logs_dir / events_filename
    envelope_path = autonomous_dir / f"{run_id}__{run_instance_id}.run.json"

    run_start_ts = datetime.now(timezone.utc).isoformat()
    raw_actions = plan.get("actions", [])

    # Normalize actions with order
    actions: list[dict] = []
    for i, a in enumerate(raw_actions):
        na = normalize_action(a)
        na["order"] = na.get("order") or i
        actions.append(na)

    # task_intake
    append_event(
        log_path,
        run_id,
        "task_intake",
        payload={"plan_id": plan.get("plan_id", ""), "action_count": len(actions)},
    )

    # plan_generation
    append_event(
        log_path,
        run_id,
        "plan_generation",
        payload={"action_count": len(actions)},
    )

    # Pre-execution: evaluate all actions, log risk_evaluation
    evaluations: list[dict] = []
    for action in actions:
        ev = policy_evaluate(action, sandbox_root)
        evaluations.append(ev)
        append_event(
            log_path,
            run_id,
            "risk_evaluation",
            action_id=action.get("action_id"),
            decision_type=ev["decision_type"],
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload={
                "modified_action": ev.get("modified_action"),
                "stabilization_mechanism": ev.get("stabilization_mechanism"),
            },
        )

    # Stabilization: for allow_modified and block, run stabilize and log
    actions_to_execute: list[tuple[dict, dict, bool]] = []
    blocked_action_count = 0
    modified_action_count = 0

    for action, ev in zip(actions, evaluations):
        dt = ev["decision_type"]
        if dt == "allow":
            actions_to_execute.append((action, ev, False))
            continue
        # allow_modified or block: run stabilize
        s_dt, s_action, s_mechanism, s_reason = stabilize_action(action, ev, sandbox_root)
        append_event(
            log_path,
            run_id,
            "stabilization",
            action_id=action.get("action_id"),
            decision_type=s_dt,
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload={
                "original_action": action,
                "modified_action": s_action,
                "stabilization_mechanism": s_mechanism,
                "stabilization_reason": s_reason,
            },
        )
        if s_dt == "allow_modified" and s_action is not None:
            actions_to_execute.append((s_action, {**ev, "decision_type": "allow_modified"}, True))
            modified_action_count += 1
        else:
            blocked_action_count += 1

    # sandbox_state_hash_before (before first executed action)
    sandbox_state_hash_before = compute_sandbox_state_hash(sandbox_root)

    adapter = ExecutionAdapter(sandbox_root)
    results: list[dict] = []

    for action, ev, is_modified in actions_to_execute:
        result = adapter.execute(action)
        results.append(result)
        append_event(
            log_path,
            run_id,
            "adapter_invocation",
            action_id=action.get("action_id"),
            decision_type=ev["decision_type"],
            adapter_status=result.get("adapter_status", "error"),
            risk_label=ev["risk_label"],
            risk_score=ev.get("risk_score"),
            policy_reason=ev["policy_reason"],
            payload={"output_hash": result.get("output_hash"), "was_modified": is_modified},
        )

    # sandbox_state_hash_after (after final executed action)
    sandbox_state_hash_after = compute_sandbox_state_hash(sandbox_root)

    # state_validation
    integrity_ok = all(r.get("adapter_status") == "success" for r in results)
    executed_action_count = len(results)
    append_event(
        log_path,
        run_id,
        "state_validation",
        payload={
            "integrity_ok": integrity_ok,
            "completed_action_count": executed_action_count,
            "total_evaluated": len(actions),
            "blocked_count": blocked_action_count,
            "modified_count": modified_action_count,
        },
    )

    # receipt_logging
    stabilization_event_count = blocked_action_count + modified_action_count
    event_count = 2 + len(actions) + stabilization_event_count + executed_action_count + 2
    append_event(
        log_path,
        run_id,
        "receipt_logging",
        payload={
            "event_count": event_count,
            "executed_action_count": executed_action_count,
            "modified_action_count": modified_action_count,
        },
    )

    run_end_ts = datetime.now(timezone.utc).isoformat()
    execution_log_hash = compute_execution_log_hash(log_path)

    exit_status = "normal" if integrity_ok and executed_action_count == len(actions_to_execute) else "incomplete"
    total_expected = len(actions)
    total_completed = executed_action_count

    envelope_data = {
        "schema_version": "1.2",
        "run_id": run_id,
        "run_instance_id": run_instance_id,
        "suite": "autonomous",
        "total_cases_expected": total_expected,
        "total_cases_completed": total_completed,
        "executed_action_count": executed_action_count,
        "blocked_action_count": blocked_action_count,
        "modified_action_count": modified_action_count,
        "run_start_ts_utc": run_start_ts,
        "run_end_ts_utc": run_end_ts,
        "exit_status": exit_status,
        "sandbox_state_hash_before": sandbox_state_hash_before,
        "sandbox_state_hash_after": sandbox_state_hash_after,
        "execution_log_hash": execution_log_hash,
        "receipt_path": f"runtime/benchmarks/execution_logs/{events_filename}",
        "receipt_sha256": run_envelope.compute_file_sha256(log_path),
    }

    run_envelope.write_run_envelope_tmp(envelope_path, envelope_data)
    tmp_path = envelope_path.with_suffix(".run.json.tmp")
    run_envelope.finalize_run_envelope(tmp_path, envelope_path)

    return envelope_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous run (Phase 2B stabilization)")
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"), help="Runtime root")
    parser.add_argument("--run-id", type=str, default="validation_phase2b", help="Run ID")
    parser.add_argument("--run-instance-id", type=str, default=None, help="Run instance ID")
    parser.add_argument(
        "--validation-set",
        type=str,
        choices=["benign", "unsafe", "risky", "risky_write", "all"],
        default="all",
    )
    args = parser.parse_args()

    run_instance_id = args.run_instance_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    validation_plans = {
        "benign": {
            "plan_id": "validation_phase2b_benign",
            "actions": [
                {"action_id": "1", "tool_name": "write_file", "arguments": {"path": "a.txt", "content": "hello"}, "order": 1},
                {"action_id": "2", "tool_name": "read_file", "arguments": {"path": "a.txt"}, "order": 2},
                {"action_id": "3", "tool_name": "list_dir", "arguments": {"path": "/"}, "order": 3},
            ],
        },
        "unsafe": {
            "plan_id": "validation_phase2b_unsafe",
            "actions": [
                {"action_id": "1", "tool_name": "write_file", "arguments": {"path": "../evil.txt", "content": "bad"}, "order": 1},
            ],
        },
        "risky": {
            "plan_id": "validation_phase2b_risky",
            "actions": [
                {"action_id": "1", "tool_name": "delete_file", "arguments": {"path": "*"}, "order": 1},
            ],
        },
        "risky_write": {
            "plan_id": "validation_phase2b_risky_write",
            "actions": [
                {"action_id": "1", "tool_name": "write_file", "arguments": {"path": "big.txt", "content": "x" * (2 * 1024 * 1024)}, "order": 1},
            ],
        },
    }

    sets_to_run = (
        ["benign", "unsafe", "risky", "risky_write"]
        if args.validation_set == "all"
        else [args.validation_set]
    )

    summaries: list[dict] = []

    for vs in sets_to_run:
        run_id = f"validation_phase2b_{vs}"
        plan = validation_plans[vs]
        envelope_data = run_autonomous(
            plan=plan,
            run_id=run_id,
            run_instance_id=run_instance_id,
            runtime_root=args.runtime_dir,
        )
        summaries.append({
            "validation_set": vs,
            "run_id": run_id,
            "envelope_path": str(Path(args.runtime_dir) / "benchmarks" / "autonomous" / f"{run_id}__{run_instance_id}.run.json"),
            "executed_action_count": envelope_data.get("executed_action_count", 0),
            "blocked_action_count": envelope_data.get("blocked_action_count", 0),
            "modified_action_count": envelope_data.get("modified_action_count", 0),
            "exit_status": envelope_data["exit_status"],
            "sandbox_state_hash_before": envelope_data["sandbox_state_hash_before"],
            "sandbox_state_hash_after": envelope_data["sandbox_state_hash_after"],
            "execution_log_hash": envelope_data["execution_log_hash"],
        })

    # Print summary
    for s in summaries:
        print(f"\n=== {s['validation_set'].upper()} ===")
        print(f"Run ID: {s['run_id']}")
        print(f"Envelope: {s['envelope_path']}")
        print(f"exit_status: {s['exit_status']}")
        print(f"executed_action_count: {s['executed_action_count']}")
        print(f"blocked_action_count: {s['blocked_action_count']}")
        print(f"modified_action_count: {s['modified_action_count']}")
        print(f"sandbox_state_hash_before: {s['sandbox_state_hash_before']}")
        print(f"sandbox_state_hash_after: {s['sandbox_state_hash_after']}")
        print(f"execution_log_hash: {s['execution_log_hash']}")


if __name__ == "__main__":
    main()
