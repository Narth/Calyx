#!/usr/bin/env python3
"""
CP14 Sentinel Processor (CLI)

Static-only scan of unified diffs for:
- Secrets (AWS keys, private keys, tokens)
- Forbidden patterns (shell=True, eval, exec)
- Risky imports (subprocess, os.system, paramiko)

Writes verdict JSON to: <repo>/outgoing/reviews/{intent_id}.CP14.verdict.json

Constraints:
- No code execution
- Read-only inputs
- Writes only the verdict JSON
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Tuple

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"
REVIEWS_DIR = ROOT / "outgoing" / "reviews"
AGENT_ID = "cp14_validator"
MANDATE_REF = "agents.cp14_validator"
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
        if "laws" not in rf or not isinstance(rf["laws"], list):
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
    """
    Persist the current introspection snapshot and append to history.
    """
    _ensure_agent_paths()
    ok, errors = _validate_introspection_snapshot(state)
    if not ok:
        _log_schema_violation("agent_introspection_v0.1", errors, state)
        return

    serialized = json.dumps(state, indent=2)
    INTROSPECTION_PATH.write_text(serialized, encoding="utf-8")
    with INTROSPECTION_HISTORY_PATH.open("a", encoding="utf-8") as hist:
        hist.write(json.dumps(state) + "\n")


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


def _append_trace_entry(entry: dict) -> None:
    _ensure_agent_paths()
    ok, errors = _validate_trace_entry(entry)
    if not ok:
        _log_schema_violation("agent_trace_v0.1", errors, entry)
        return
    with TRACE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# Patterns to look for in ADDED lines of the patch
SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
    r"-----BEGIN( RSA)? PRIVATE KEY-----",
    r"(?i)aws_secret",
    r"(?i)api[_-]?key\s*=\s*['\"][0-9A-Za-z_\-]{16,}['\"]",
    r"(?i)token\s*=\s*['\"][0-9A-Za-z_\-]{16,}['\"]",
]

FORBIDDEN_PATTERNS = [
    r"shell\s*=\s*True",
    r"\beval\s*\(",
    r"\bexec\s*\(",
]

RISKY_IMPORTS = [
    "import subprocess",
    "from subprocess import",
    "os.system(",
    "import paramiko",
]


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def iter_added_lines_from_patch(patch_path: Path) -> Iterable[Tuple[str, str]]:
    """
    Yield (filename, line) for added lines in a unified diff.
    Only lines starting with '+' that are not '+++' headers.
    """
    current_file = None
    for raw in patch_path.read_text(errors="ignore").splitlines():
        if raw.startswith("+++ "):
            parts = raw.split()
            if len(parts) >= 2:
                current_file = parts[1].lstrip("ab/")
        elif raw.startswith("@@"):
            continue
        elif raw.startswith("+") and not raw.startswith("+++"):
            yield (current_file or "<unknown>", raw[1:])


def scan_added_line(filename: str, line: str):
    findings = []

    for pattern in SECRET_PATTERNS:
        for match in re.finditer(pattern, line):
            findings.append(
                {
                    "type": "secret_leak",
                    "path": filename,
                    "snippet": match.group(0),
                }
            )

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, line):
            findings.append(
                {
                    "type": "forbidden_pattern",
                    "pattern": pattern,
                    "path": filename,
                    "snippet": line.strip(),
                }
            )

    for imp in RISKY_IMPORTS:
        if imp in line:
            findings.append(
                {
                    "type": "risky_import",
                    "import": imp,
                    "path": filename,
                    "snippet": line.strip(),
                }
            )

    return findings


def _resolve_artifact_path(artifacts: dict, keys: list[str], fallback: Path) -> Path:
    for k in keys:
        v = artifacts.get(k)
        if not v:
            continue
        p = v if isinstance(v, Path) else Path(str(v))
        if not p.is_absolute():
            p = ROOT / p
        return p
    return fallback


def _syscall_risk_from_findings(findings: list[dict]) -> str:
    if not findings:
        return "LOW"
    for f in findings:
        if f.get("type") in {"secret_leak", "forbidden_pattern"}:
            return "HIGH"
    return "MED"


def review_proposal(intent_id: str, artifacts: dict) -> dict:
    """
    Review proposal using CP14 processor.

    Constraints (per Request A): static/dry only; write only to outgoing/reviews.

    Args:
        intent_id: Intent ID
        artifacts: Paths and metadata (supports keys like diff/patch/change_patch, metadata, proposals_dir, reviews_dir)

    Returns:
        Verdict dictionary per CGPT spec.
    """
    proposals_dir = _resolve_artifact_path(artifacts, ["proposals_dir"], PROPOSALS_DIR)
    reviews_dir = _resolve_artifact_path(artifacts, ["reviews_dir"], REVIEWS_DIR)

    base = proposals_dir / intent_id
    patch_path = _resolve_artifact_path(
        artifacts,
        ["diff", "patch", "change_patch", "patch_path"],
        base / "change.patch",
    )
    metadata_path = _resolve_artifact_path(
        artifacts,
        ["metadata", "metadata_path"],
        base / "metadata.json",
    )

    lines_scanned = 0
    all_findings: list[dict] = []
    for filename, line in iter_added_lines_from_patch(patch_path):
        lines_scanned += 1
        all_findings.extend(scan_added_line(filename, line))

    verdict = "FAIL" if all_findings else "PASS"
    out = {
        "intent_id": intent_id,
        "verdict": verdict,
        "findings": all_findings,
        "network_egress": "DENIED",
        "syscall_risk": _syscall_risk_from_findings(all_findings),
        "lines_scanned": lines_scanned,
        "inputs": {
            "patch_path": str(patch_path),
            "metadata_path": str(metadata_path),
        },
    }

    reviews_dir.mkdir(parents=True, exist_ok=True)
    (reviews_dir / f"{intent_id}.CP14.verdict.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def run_cp14(patch_path: Path, metadata_path: Path, intent_id: str, *, test_mode: bool = False):
    metadata = load_metadata(metadata_path)
    constraints = [
        "static diff scan only (no execution)",
        "no network egress (enable_network prohibited)",
        "no repo writes",
        "no daemons/schedulers",
    ]
    inputs_summary = {
        "patch_path": str(patch_path),
        "metadata_path": str(metadata_path),
        "metadata_keys": sorted(metadata.keys()) if isinstance(metadata, dict) else [],
    }
    intent_label = f"validate diff for {intent_id}"

    preflight = _build_introspection_snapshot(
        intent=intent_label,
        current_task="static diff scan (init)",
        inputs=inputs_summary,
        constraints=constraints,
        uncertainty="scan not yet run",
        last_decision="initialized",
        planned_next_step="scan patch for secrets/forbidden patterns",
        health={"status": "ok"},
    )
    _write_introspection(preflight)

    added_lines = 0
    all_findings = []
    out_path: Path | None = None
    verdict = "ERROR"
    error: str | None = None

    try:
        for filename, line in iter_added_lines_from_patch(patch_path):
            added_lines += 1
            all_findings.extend(scan_added_line(filename, line))

        verdict = "FAIL" if all_findings else "PASS"
        out = {
            "intent_id": intent_id,
            "verdict": verdict,
            "findings": all_findings,
            "network_egress": "DENIED",
            "syscall_risk": _syscall_risk_from_findings(all_findings),
            "lines_scanned": added_lines,
        }

        REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REVIEWS_DIR / f"{intent_id}.CP14.verdict.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out_path
    except Exception as exc:  # pragma: no cover - defensive path
        error = f"{exc}"
        verdict = "ERROR"
        raise
    finally:
        uncertainty_note = "findings require Architect review" if verdict == "FAIL" else "no blocking findings"
        if error:
            uncertainty_note = f"exception during scan: {error}"

        final_snapshot = _build_introspection_snapshot(
            intent=intent_label,
            current_task="static diff scan (complete)",
            inputs={**inputs_summary, "added_lines": added_lines},
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
            "inputs_summary": {**inputs_summary, "added_lines": added_lines},
            "decision": {
                "type": "run",
                "reason": "static diff scan",
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
            "outcome": {"status": verdict, "errors": error, "verdict_path": str(out_path) if out_path else None},
            "test_mode": test_mode,
            **DEFAULT_RESPECT_FRAME,
        }
        _append_trace_entry(trace_entry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP14 Sentinel Processor (static scan)")
    parser.add_argument("--patch", required=True, help="Path to change.patch")
    parser.add_argument("--metadata", required=True, help="Path to metadata.json")
    parser.add_argument("--intent-id", required=True, help="Intent ID string")
    parser.add_argument("--test-mode", action="store_true", help="Label this run as test_mode for trace logging")
    args = parser.parse_args(argv)

    run_cp14(Path(args.patch), Path(args.metadata), args.intent_id, test_mode=args.test_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
