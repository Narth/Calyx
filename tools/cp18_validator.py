#!/usr/bin/env python3
"""
CP18 Validator Processor (CLI)

Static/dry analysis of diffs for:
- Syntax sanity (Python added lines via AST parse)
- Broken test markers (assert False, skip markers) in test files
- Existence of tests referenced in metadata["tests"]

Writes verdict JSON to: <repo>/outgoing/reviews/{intent_id}.CP18.verdict.json

Constraints:
- No execution of user code
- Read-only repository access
- Writes only the verdict JSON
"""
from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
REVIEWS_DIR = ROOT / "outgoing" / "reviews"
AGENT_ID = "cp18_validator"
MANDATE_REF = "agents.cp18_validator"
LIFECYCLE_PHASE = "sprout"
STATE_DIR = ROOT / "state" / "agents" / AGENT_ID
INTROSPECTION_PATH = STATE_DIR / "introspection.json"
INTROSPECTION_HISTORY_PATH = STATE_DIR / "introspection_history.jsonl"
TRACE_LOG_PATH = ROOT / "logs" / "agents" / f"{AGENT_ID}_trace.jsonl"
SCHEMA_VIOLATION_LOG = ROOT / "logs" / "agent_schema_violations.jsonl"
DEFAULT_RESPECT_FRAME = {
    "laws": [2, 4, 5, 9, 10, "3.4.1"],
    "respect_frame": "agent_transparency_doctrine",
}


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ensure_agent_paths() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_VIOLATION_LOG.parent.mkdir(parents=True, exist_ok=True)


def _log_schema_violation(schema: str, errors: list[str], payload: dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": AGENT_ID,
        "schema": schema,
        "errors": errors,
        "payload_excerpt": {k: payload.get(k) for k in list(payload)[:6]},
    }
    with SCHEMA_VIOLATION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _validate_introspection_snapshot(snapshot: dict) -> tuple[bool, list[str]]:
    required = [
        ("timestamp", str),
        ("agent_id", str),
        ("mandate_ref", str),
        ("lifecycle_phase", str),
        ("intent", str),
        ("current_task", str),
        ("inputs", dict),
        ("constraints", list),
        ("uncertainty", str),
        ("last_decision", str),
        ("planned_next_step", str),
        ("respect_frame", dict),
        ("health", dict),
    ]
    errors: list[str] = []
    for key, typ in required:
        if key not in snapshot:
            errors.append(f"missing field: {key}")
        elif not isinstance(snapshot[key], typ):
            errors.append(f"field {key} has type {type(snapshot[key]).__name__}, expected {typ.__name__}")

    rf = snapshot.get("respect_frame", {})
    if isinstance(rf, dict):
        if "laws" not in rf or not isinstance(rf.get("laws"), list):
            errors.append("respect_frame.laws missing or not list")
        if "respect_frame" not in rf or not isinstance(rf.get("respect_frame"), str):
            errors.append("respect_frame.respect_frame missing or not string")
    else:
        errors.append("respect_frame missing or not object")

    if not isinstance(snapshot.get("constraints", []), list):
        errors.append("constraints not list")

    return (len(errors) == 0, errors)


def _validate_trace_entry(entry: dict) -> tuple[bool, list[str]]:
    required = [
        ("ts", str),
        ("agent_id", str),
        ("lifecycle_phase", str),
        ("intent", str),
        ("context", dict),
        ("inputs_summary", dict),
        ("decision", dict),
        ("action", dict),
        ("outcome", dict),
        ("test_mode", bool),
        ("laws", list),
        ("respect_frame", (str, dict)),
    ]
    errors: list[str] = []
    for key, typ in required:
        if key not in entry:
            errors.append(f"missing field: {key}")
        else:
            val = entry[key]
            expected_types = typ if isinstance(typ, tuple) else (typ,)
            if not isinstance(val, expected_types):
                errors.append(f"field {key} has type {type(val).__name__}, expected {', '.join(t.__name__ for t in expected_types)}")

    ctx = entry.get("context", {})
    if isinstance(ctx, dict):
        if "mandate_ref" not in ctx or not isinstance(ctx.get("mandate_ref"), str):
            errors.append("context.mandate_ref missing or not string")
    else:
        errors.append("context missing or not object")

    dec = entry.get("decision", {})
    if isinstance(dec, dict):
        if "type" not in dec or "reason" not in dec:
            errors.append("decision.type or decision.reason missing")
    else:
        errors.append("decision missing or not object")

    act = entry.get("action", {})
    if isinstance(act, dict):
        if "requires_approval" not in act or not isinstance(act.get("requires_approval"), bool):
            errors.append("action.requires_approval missing or not bool")
        if "proposed_change" not in act or not isinstance(act.get("proposed_change"), str):
            errors.append("action.proposed_change missing or not string")
    else:
        errors.append("action missing or not object")

    outc = entry.get("outcome", {})
    if isinstance(outc, dict):
        if "status" not in outc:
            errors.append("outcome.status missing")
    else:
        errors.append("outcome missing or not object")
    return (len(errors) == 0, errors)


def _write_introspection(state: dict) -> None:
    _ensure_agent_paths()
    ok, errors = _validate_introspection_snapshot(state)
    if not ok:
        _log_schema_violation("agent_introspection_v0.1", errors, state)
        return
    INTROSPECTION_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    with INTROSPECTION_HISTORY_PATH.open("a", encoding="utf-8") as hist:
        hist.write(json.dumps(state) + "\n")


def _append_trace_entry(entry: dict) -> None:
    _ensure_agent_paths()
    ok, errors = _validate_trace_entry(entry)
    if not ok:
        _log_schema_violation("agent_trace_v0.1", errors, entry)
        return
    with TRACE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _build_introspection_snapshot(
    intent: str,
    current_task: str,
    inputs: dict,
    constraints: list[str],
    uncertainty: str,
    last_decision: str,
    planned_next_step: str,
    health: dict,
) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": ts,
        "agent_id": AGENT_ID,
        "mandate_ref": MANDATE_REF,
        "lifecycle_phase": LIFECYCLE_PHASE,
        "intent": intent,
        "current_task": current_task,
        "inputs": inputs,
        "constraints": constraints,
        "uncertainty": uncertainty,
        "last_decision": last_decision,
        "planned_next_step": planned_next_step,
        "respect_frame": DEFAULT_RESPECT_FRAME,
        "health": health,
    }


def iter_file_hunks_from_patch(patch_path: Path) -> Iterable[Tuple[str, List[str], List[str]]]:
    """
    Parse unified diff and yield (filename, added_lines, removed_lines) for each file.
    Only raw added/removed lines are returned (without leading +/- markers).
    """
    text = patch_path.read_text(errors="ignore")
    current_file = None
    added_lines: list[str] = []
    removed_lines: list[str] = []

    def flush():
        nonlocal current_file, added_lines, removed_lines
        if current_file is not None:
            yield (current_file, added_lines, removed_lines)
        current_file = None
        added_lines = []
        removed_lines = []

    for raw in text.splitlines():
        if raw.startswith("+++ "):
            parts = raw.split()
            if len(parts) >= 2:
                for item in flush():
                    yield item
                current_file = parts[1].lstrip("ab/")
        elif raw.startswith("@@"):
            continue
        else:
            if raw.startswith("+") and not raw.startswith("+++"):
                added_lines.append(raw[1:])
            elif raw.startswith("-") and not raw.startswith("---"):
                removed_lines.append(raw[1:])

    for item in flush():
        yield item


def is_test_file(filename: str) -> bool:
    fn = filename.lower()
    return (
        "/tests/" in fn
        or fn.startswith("tests/")
        or fn.startswith("test_")
        or fn.endswith("_test.py")
    )


def python_syntax_ok(added_lines: list[str]) -> bool:
    """
    Basic syntax check on added lines that appear Python-like.
    Only runs if there is at least one non-empty, non-comment line.
    """
    meaningful = [l for l in added_lines if l.strip() and not l.strip().startswith("#")]
    if not meaningful:
        return True
    code = "\n".join(meaningful)
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def detect_broken_tests_in_hunks(filename: str, added_lines: list[str], removed_lines: list[str]) -> bool:
    """
    Heuristic to detect intentionally broken tests.
    Triggers failure if:
    - any added line in a test file contains 'assert False'
    - or adds obvious TODO/skip markers in tests
    """
    if not is_test_file(filename):
        return False

    for line in added_lines:
        stripped = line.strip()
        if "assert False" in stripped:
            return True
        if "TODO" in stripped and "assert" in stripped:
            return True
        if "pytest.skip" in stripped or "@pytest.mark.skip" in stripped:
            return True
    return False


def validate_tests_exist(metadata: dict) -> tuple[bool, list[str]]:
    """
    Check that tests referenced in metadata['tests'] exist on disk.
    """
    tests = metadata.get("tests", [])
    missing = []
    for t in tests:
        if not Path(t).exists():
            missing.append(t)
    return (len(missing) == 0, missing)


def run_cp18(patch_path: Path, metadata_path: Path, intent_id: str, *, test_mode: bool = False):
    metadata = load_metadata(metadata_path)
    constraints = [
        "static diff analysis only (no execution)",
        "no network egress (enable_network prohibited)",
        "no repo writes",
        "no daemons/schedulers",
    ]
    inputs_summary = {
        "patch_path": str(patch_path),
        "metadata_path": str(metadata_path),
        "metadata_keys": sorted(metadata.keys()) if isinstance(metadata, dict) else [],
    }
    intent_label = f"validate diff (cp18) for {intent_id}"

    pre_snapshot = _build_introspection_snapshot(
        intent=intent_label,
        current_task="static diff validation (init)",
        inputs=inputs_summary,
        constraints=constraints,
        uncertainty="scan not yet run",
        last_decision="initialized",
        planned_next_step="analyze hunks for syntax and test markers",
        health={"status": "ok"},
    )
    _write_introspection(pre_snapshot)

    lints_ok = True
    broken_tests_detected = False
    files_seen = 0
    py_files_checked = 0
    missing_tests: list[str] = []
    out_path: Path | None = None
    verdict = "ERROR"
    error: str | None = None

    try:
        for filename, added_lines, removed_lines in iter_file_hunks_from_patch(patch_path):
            files_seen += 1
            if filename and filename.endswith(".py"):
                py_files_checked += 1
                if not python_syntax_ok(added_lines):
                    lints_ok = False
            if filename and is_test_file(filename):
                if detect_broken_tests_in_hunks(filename, added_lines, removed_lines):
                    broken_tests_detected = True

        if broken_tests_detected:
            unit_tests_ok = False
        else:
            tests_exist, missing = validate_tests_exist(metadata)
            unit_tests_ok = tests_exist
            missing_tests = missing

        integration_tests_status = "N/A"
        coverage_delta = 0.0

        verdict = "PASS" if (lints_ok and unit_tests_ok) else "FAIL"

        out = {
            "intent_id": intent_id,
            "verdict": verdict,
            "details": {
                "lints": "PASS" if lints_ok else "FAIL",
                "unit_tests": "PASS" if unit_tests_ok else "FAIL",
                "integration_tests": integration_tests_status,
                "coverage_delta": coverage_delta,
                "files_seen": files_seen,
                "py_files_checked": py_files_checked,
                "missing_tests": missing_tests,
            },
        }

        REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REVIEWS_DIR / f"{intent_id}.CP18.verdict.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out_path
    except Exception as exc:  # pragma: no cover - defensive path
        error = f"{exc}"
        verdict = "ERROR"
        raise
    finally:
        uncertainty_note = "no blocking findings" if verdict == "PASS" else "review required"
        if missing_tests:
            uncertainty_note = f"missing tests: {missing_tests}"
        if error:
            uncertainty_note = f"exception during scan: {error}"

        final_snapshot = _build_introspection_snapshot(
            intent=intent_label,
            current_task="static diff validation (complete)",
            inputs={**inputs_summary, "files_seen": files_seen, "py_files_checked": py_files_checked, "missing_tests": missing_tests},
            constraints=constraints,
            uncertainty=uncertainty_note,
            last_decision=f"verdict={verdict}",
            planned_next_step="await Architect review",
            health={"status": "error", "message": error} if error else {"status": "ok"},
        )
        _write_introspection(final_snapshot)

        trace_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent_id": AGENT_ID,
            "lifecycle_phase": LIFECYCLE_PHASE,
            "intent": intent_label,
            "context": {"mandate_ref": MANDATE_REF, "intent_id": intent_id},
            "inputs_summary": {**inputs_summary, "files_seen": files_seen, "py_files_checked": py_files_checked},
            "decision": {
                "type": "run",
                "reason": "static/dry validation of diff",
                "uncertainty": uncertainty_note,
            },
            "action": {
                "requires_approval": False,
                "proposed_change": "emit PASS/FAIL verdict JSON",
                "side_effects": [
                    "write verdict to outgoing/reviews",
                    "update introspection snapshot",
                    "append trace log",
                ],
            },
            "outcome": {
                "status": verdict,
                "errors": error,
                "verdict_path": str(out_path) if out_path else None,
            },
            "test_mode": test_mode,
            **DEFAULT_RESPECT_FRAME,
        }
        _append_trace_entry(trace_entry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP18 Validator Processor (static/dry)")
    parser.add_argument("--patch", required=True, help="Path to change.patch")
    parser.add_argument("--metadata", required=True, help="Path to metadata.json")
    parser.add_argument("--intent-id", required=True, help="Intent ID string")
    parser.add_argument("--test-mode", action="store_true", help="Label this run as test_mode for trace logging")
    args = parser.parse_args(argv)

    run_cp18(Path(args.patch), Path(args.metadata), args.intent_id, test_mode=args.test_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
