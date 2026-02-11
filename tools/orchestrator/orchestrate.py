from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jsonschema import Draft202012Validator

from tools.orchestrator.workers import dispatch_task

ALLOWED_OPERATIONS = {"read", "write", "test", "report"}
ALLOWED_ROLES = {"test_steward", "refactor_steward", "schema_steward", "docs_steward"}
EXECUTE_ROLES = {"test_steward", "schema_steward", "docs_steward"}
EXECUTE_OPERATIONS = {"read", "test", "report"}
HARD_DENY_EXEC = {"curl", "wget", "invoke-webrequest", "invoke-restmethod", "git", "pip"}
HARD_DENY_ARGS = {
    "push",
    "fetch",
    "clone",
    "install",
    "invoke-webrequest",
    "invoke-restmethod",
    "curl",
    "wget",
    "git",
    "pip",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def read_plan(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_task(task: Dict[str, Any]) -> List[str]:
    errors = []
    required = {
        "task_id",
        "parent_id",
        "role",
        "inputs",
        "outputs",
        "allowed_operations",
        "max_runtime_seconds",
        "max_files_touched",
        "success_criteria",
        "required_evidence",
    }
    missing = required - set(task.keys())
    if missing:
        errors.append(f"missing_fields:{sorted(missing)}")
        return errors
    if task["role"] not in ALLOWED_ROLES:
        errors.append("invalid_role")
    ops = set(task.get("allowed_operations", []))
    if not ops.issubset(ALLOWED_OPERATIONS):
        errors.append("invalid_allowed_operations")
    if not isinstance(task.get("inputs"), list) or not isinstance(task.get("outputs"), list):
        errors.append("inputs_outputs_not_list")
    if task.get("max_runtime_seconds", 0) <= 0:
        errors.append("invalid_max_runtime_seconds")
    if task.get("max_files_touched", 0) < 0:
        errors.append("invalid_max_files_touched")
    if task.get("exec") and not isinstance(task.get("args"), list):
        errors.append("args_required_for_exec")
    return errors


def validate_jsonschema(plan: Dict[str, Any]) -> List[str]:
    schema_dir = REPO_ROOT / "governance" / "schemas"
    plan_schema_path = schema_dir / "orchestration_plan.schema.json"
    task_schema_path = schema_dir / "task_contract.schema.json"
    plan_schema = load_schema(plan_schema_path)
    task_schema = load_schema(task_schema_path)
    plan_schema_resolved = json.loads(json.dumps(plan_schema))
    if "properties" in plan_schema_resolved and "nodes" in plan_schema_resolved["properties"]:
        plan_schema_resolved["properties"]["nodes"]["items"] = task_schema

    errors = []
    plan_validator = Draft202012Validator(plan_schema_resolved)
    for err in sorted(plan_validator.iter_errors(plan), key=lambda e: e.path):
        errors.append(f"plan_schema:{'/'.join([str(p) for p in err.path])}:{err.message}")

    task_validator = Draft202012Validator(task_schema)
    for node in plan.get("nodes", []):
        for err in sorted(task_validator.iter_errors(node), key=lambda e: e.path):
            errors.append(f"task_schema:{node.get('task_id')}:{'/'.join([str(p) for p in err.path])}:{err.message}")

    return errors


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    errors = []
    for key in ("plan_id", "nodes", "edges", "global_budgets", "fail_policy"):
        if key not in plan:
            errors.append(f"missing_plan_field:{key}")
    if errors:
        return errors
    if plan["fail_policy"] not in {"fail_closed", "partial_allowed"}:
        errors.append("invalid_fail_policy")
    nodes = plan.get("nodes", [])
    task_ids = {node.get("task_id") for node in nodes}
    if None in task_ids:
        errors.append("task_id_missing")
    for node in nodes:
        errors.extend([f"{node.get('task_id')}:" + err for err in validate_task(node)])
    for edge in plan.get("edges", []):
        if edge.get("from") not in task_ids or edge.get("to") not in task_ids:
            errors.append("edge_references_unknown_task")
    return errors


def topological_sort(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    graph: Dict[str, Set[str]] = {node["task_id"]: set() for node in nodes}
    incoming: Dict[str, Set[str]] = {node["task_id"]: set() for node in nodes}
    for edge in edges:
        src = edge["from"]
        dst = edge["to"]
        graph[src].add(dst)
        incoming[dst].add(src)
    order: List[Dict[str, Any]] = []
    ready = [task_id for task_id, deps in incoming.items() if not deps]
    while ready:
        current = ready.pop(0)
        node = next(node for node in nodes if node["task_id"] == current)
        order.append(node)
        for neighbor in sorted(graph[current]):
            incoming[neighbor].discard(current)
            if not incoming[neighbor]:
                ready.append(neighbor)
    if len(order) != len(nodes):
        raise ValueError("cycle_detected")
    return order


def ensure_budgets(plan: Dict[str, Any]) -> Optional[str]:
    budgets = plan.get("global_budgets", {})
    total_files = budgets.get("total_files_changed", 0)
    if total_files < 0:
        return "invalid_total_files_changed"
    total_runtime = budgets.get("total_runtime_seconds", 0)
    if total_runtime <= 0:
        return "invalid_total_runtime_seconds"
    return None


def ensure_execute_constraints(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for node in plan.get("nodes", []):
        role = node.get("role")
        if role not in EXECUTE_ROLES:
            errors.append(f"execute_role_not_allowed:{node.get('task_id')}")
        ops = set(node.get("allowed_operations", []))
        if not ops.issubset(EXECUTE_OPERATIONS):
            errors.append(f"execute_ops_not_allowed:{node.get('task_id')}")
        if role in {"schema_steward", "docs_steward"} and node.get("exec"):
            if not ops.issubset({"read", "report"}):
                errors.append(f"execute_command_not_allowed:{node.get('task_id')}")
        if role == "test_steward" and not node.get("exec"):
            errors.append(f"execute_command_required:{node.get('task_id')}")
    return errors


def ensure_paths(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    allowed_prefixes = [REPO_ROOT / "logs" / "orchestrator", REPO_ROOT]
    for node in plan.get("nodes", []):
        for path_value in node.get("inputs", []) + node.get("outputs", []):
            candidate = (REPO_ROOT / path_value).resolve()
            if not any(candidate.is_relative_to(prefix.resolve()) for prefix in allowed_prefixes):
                errors.append(f"path_not_allowed:{node.get('task_id')}:{path_value}")
    return errors


def ensure_capabilities(plan: Dict[str, Any]) -> List[str]:
    policy_path = REPO_ROOT / "governance" / "policies" / "orchestrator_capabilities.json"
    policy = load_policy(policy_path)
    current_tier = policy.get("current_tier")
    tier = policy.get("tiers", {}).get(current_tier, {})
    allowed_ops = set(tier.get("allowed_operations", []))
    if not allowed_ops:
        return ["capabilities_not_configured"]
    errors: List[str] = []
    for node in plan.get("nodes", []):
        ops = set(node.get("allowed_operations", []))
        if not ops.issubset(allowed_ops):
            errors.append(f"capability_exceeded:{node.get('task_id')}")
    return errors


def ensure_command_policy(plan: Dict[str, Any]) -> List[str]:
    policy_path = REPO_ROOT / "governance" / "policies" / "orchestrator_command_allowlist.json"
    policy = load_policy(policy_path)
    errors: List[str] = []
    for node in plan.get("nodes", []):
        exec_name = node.get("exec")
        args = node.get("args", [])
        if not exec_name:
            continue
        exec_lower = exec_name.lower()
        if exec_lower in HARD_DENY_EXEC:
            errors.append(f"denied_by_policy:{node.get('task_id')}:exec_denied")
            continue
        if any(arg.lower() in HARD_DENY_ARGS for arg in args):
            errors.append(f"denied_by_policy:{node.get('task_id')}:arg_denied")
            continue
        role_policy = policy.get(node.get("role"), [])
        matched = False
        for allow in role_policy:
            if exec_lower != allow.get("exec", "").lower():
                continue
            prefixes = allow.get("required_arg_prefixes", [])
            if prefixes and args[: len(prefixes)] != prefixes:
                continue
            forbidden = set(flag.lower() for flag in allow.get("forbidden_flags", []))
            if any(arg.lower() in forbidden for arg in args):
                continue
            allowed_paths = [str((REPO_ROOT / p).resolve()) for p in allow.get("allowed_script_paths", [])]
            script_args = [arg for arg in args if arg.endswith((".py", ".ps1"))]
            if allowed_paths and any(str((REPO_ROOT / arg).resolve()) not in allowed_paths for arg in script_args):
                continue
            matched = True
            break
        if not matched:
            errors.append(f"denied_by_policy:{node.get('task_id')}:command_not_allowed")
    return errors


def substitute_args(args: List[str], correlation_id: str, plan_id: str) -> List[str]:
    replaced = []
    for arg in args:
        replaced.append(
            arg.replace("{correlation_id}", correlation_id).replace("{plan_id}", plan_id)
        )
    return replaced


def run_command(
    command: List[str],
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
    no_progress_seconds: int,
) -> Dict[str, Any]:
    import subprocess

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    outcome = "failed"
    exit_code = -1

    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        last_progress = time.time()
        last_size = 0
        while True:
            if process.poll() is not None:
                break
            elapsed = time.time() - start
            if timeout_seconds and elapsed >= timeout_seconds:
                outcome = "timeout"
                process.kill()
                break
            if no_progress_seconds:
                current_size = 0
                if stdout_path.exists():
                    current_size += stdout_path.stat().st_size
                if stderr_path.exists():
                    current_size += stderr_path.stat().st_size
                if current_size != last_size:
                    last_size = current_size
                    last_progress = time.time()
                if time.time() - last_progress >= no_progress_seconds:
                    outcome = "no_progress"
                    process.kill()
                    break
            time.sleep(1)

        process.wait()
        exit_code = process.returncode
        if outcome not in {"timeout", "no_progress"}:
            outcome = "success" if exit_code == 0 else "failed"

    duration = time.time() - start
    return {
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_seconds": duration,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def hash_artifacts(paths: List[str]) -> Dict[str, str]:
    hashes = {}
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            hashes[path_str] = sha256_file(path)
    return hashes


def orchestrate(plan_path: Path, mode: str) -> int:
    plan = read_plan(plan_path)
    log_path = Path("logs/orchestrator/orchestrator_log.jsonl")
    correlation_id = hashlib.sha256(plan_path.read_bytes()).hexdigest()[:12]
    validation_errors = validate_plan(plan)
    validation_errors.extend(validate_jsonschema(plan))
    budget_error = ensure_budgets(plan)
    if budget_error:
        validation_errors.append(budget_error)
    validation_errors.extend(ensure_paths(plan))
    validation_errors.extend(ensure_capabilities(plan))
    validation_errors.extend(ensure_command_policy(plan))

    if mode == "execute":
        validation_errors.extend(ensure_execute_constraints(plan))

    if validation_errors:
        write_jsonl(
            log_path,
            {
                "ts_utc": utc_now(),
                "event": "plan_rejected",
                "plan_id": plan.get("plan_id"),
                "correlation_id": correlation_id,
                "errors": validation_errors,
            },
        )
        print("PLAN INVALID")
        for err in validation_errors:
            print(f"- {err}")
        return 1

    write_jsonl(
        log_path,
        {
            "ts_utc": utc_now(),
            "event": "plan_validated",
            "plan_id": plan.get("plan_id"),
            "correlation_id": correlation_id,
        },
    )

    if mode == "dry-run":
        print(f"Plan validated: {plan.get('plan_id')}")
        for node in topological_sort(plan["nodes"], plan["edges"]):
            print(f"- {node['task_id']} ({node['role']})")
        return 0

    total_runtime_budget = plan["global_budgets"]["total_runtime_seconds"]
    total_files_budget = plan["global_budgets"]["total_files_changed"]
    runtime_used = 0.0
    files_touched = 0

    ordered_nodes = topological_sort(plan["nodes"], plan["edges"])
    for node in ordered_nodes:
        task_id = node["task_id"]
        task_dir = Path("logs/orchestrator/tasks") / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = task_dir / "stdout.log"
        stderr_path = task_dir / "stderr.log"
        write_jsonl(
            log_path,
            {
                "ts_utc": utc_now(),
                "event": "task_start",
                "plan_id": plan.get("plan_id"),
                "task_id": task_id,
                "correlation_id": correlation_id,
            },
        )

        command_result = None
        if node.get("exec"):
            command_result = run_command(
                [node["exec"]]
                + substitute_args(node.get("args", []), correlation_id, plan.get("plan_id")),
                node["max_runtime_seconds"],
                stdout_path,
                stderr_path,
                node.get("no_progress_seconds", 0),
            )
        else:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            command_result = {
                "outcome": "skipped",
                "exit_code": 0,
                "duration_seconds": 0.0,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
            }

        task_result = dispatch_task(node, task_dir, command_result)
        runtime_used += command_result["duration_seconds"]
        files_touched += task_result.get("files_touched", 0)
        artifact_hashes = hash_artifacts(task_result.get("artifacts", []))

        write_jsonl(
            log_path,
            {
                "ts_utc": utc_now(),
                "event": "task_end",
                "plan_id": plan.get("plan_id"),
                "task_id": task_id,
                "correlation_id": correlation_id,
                "outcome": command_result["outcome"],
                "exit_code": command_result["exit_code"],
                "artifacts": task_result.get("artifacts", []),
                "artifact_hashes": artifact_hashes,
            },
        )

        if command_result["outcome"] not in {"success", "skipped"} and plan["fail_policy"] == "fail_closed":
            return 1
        if runtime_used > total_runtime_budget:
            return 1
        if files_touched > total_files_budget:
            return 1

    write_jsonl(
        log_path,
        {
            "ts_utc": utc_now(),
            "event": "plan_complete",
            "plan_id": plan.get("plan_id"),
            "correlation_id": correlation_id,
            "runtime_used": runtime_used,
            "files_touched": files_touched,
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Station Calyx Orchestrator")
    parser.add_argument("plan", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    mode_value = "dry-run" if args.dry_run else "execute"
    return orchestrate(args.plan, mode_value)


if __name__ == "__main__":
    raise SystemExit(main())
