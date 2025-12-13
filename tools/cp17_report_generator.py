#!/usr/bin/env python3
"""
CP17 Report Generator - Auto-Report for Intents
Part of Capability Evolution Phase 1
Generates human-readable summaries and checklists
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

AGENT_ID = "cp17_report_generator"
MANDATE_REF = "agents.cp17_report_generator"
LIFECYCLE_PHASE = "sprout"

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"
REVIEWS_DIR = ROOT / "outgoing" / "reviews"
REPORTS_DIR = ROOT / "outgoing" / "reports"
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


def generate_report(intent_id: str):
    """Generate CP17 report for intent"""
    return generate_report_with_transparency(intent_id, test_mode=False)


def generate_report_with_transparency(intent_id: str, test_mode: bool):
    constraints = [
        "read-only inputs (proposals, metadata, verdicts)",
        "no network egress",
        "no repo writes",
        "no daemons/schedulers",
    ]
    intent_label = f"generate report for {intent_id}"

    intent_dir = PROPOSALS_DIR / intent_id
    intent_file = intent_dir / "intent.json"
    meta_file = intent_dir / "metadata.json"
    cp14_file = REVIEWS_DIR / f"{intent_id}.CP14.verdict.json"
    cp18_file = REVIEWS_DIR / f"{intent_id}.CP18.verdict.json"

    inputs_summary = {
        "intent_path": str(intent_file),
        "metadata_path": str(meta_file),
        "cp14_verdict_path": str(cp14_file),
        "cp18_verdict_path": str(cp18_file),
    }

    pre_snapshot = _build_introspection_snapshot(
        intent=intent_label,
        current_task="report generation (init)",
        inputs=inputs_summary,
        constraints=constraints,
        uncertainty="inputs not yet validated",
        last_decision="initialized",
        planned_next_step="load inputs and compose report",
        health={"status": "ok"},
    )
    _write_introspection(pre_snapshot)

    status = "ERROR"
    error: str | None = None
    report_path: Path | None = None

    # Load intent
    if not intent_file.exists():
        error = f"Intent file not found: {intent_file}"
    else:
        try:
            intent = json.loads(intent_file.read_text(encoding="utf-8-sig"))
            meta = {}
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8-sig"))

            cp14_verdict = {}
            if cp14_file.exists():
                cp14_verdict = json.loads(cp14_file.read_text(encoding="utf-8-sig"))

            cp18_verdict = {}
            if cp18_file.exists():
                cp18_verdict = json.loads(cp18_file.read_text(encoding="utf-8-sig"))

            # Generate report
            report_dir = REPORTS_DIR / intent_id
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / "SUMMARY.md"

            report_content = f"""# Intent Review Summary
**Intent ID:** {intent_id}
**Status:** {intent.get('status', 'unknown')}
**Goal:** {intent.get('goal', 'N/A')}

---

## Change Scope
"""

            for change in intent.get('change_set', []):
                report_content += f"- {change}\n"

            report_content += f"""
---

## Diff Metrics
- **Files Changed:** {meta.get('files_changed', 0)}
- **Lines Added:** {meta.get('lines_added', 0)}
- **Lines Removed:** {meta.get('lines_removed', 0)}
- **Total Lines:** {meta.get('total_lines', 0)}

---

## CP14 Security Scan Results
**Verdict:** {cp14_verdict.get('verdict', 'UNKNOWN')}
**Findings:** {len(cp14_verdict.get('findings', []))}

"""

            if cp14_verdict.get('findings'):
                report_content += "### Findings:\n"
                for finding in cp14_verdict['findings']:
                    report_content += f"- **{finding.get('type', 'unknown')}:** {finding.get('pattern', finding.get('path', 'N/A'))}\n"
            else:
                report_content += "No security issues detected.\n"

            report_content += f"""
---

## CP18 Validation Results
**Verdict:** {cp18_verdict.get('verdict', 'UNKNOWN')}
**Details:**

"""

            details = cp18_verdict.get('details', {})
            report_content += f"- **Lints:** {details.get('lints', 'N/A')}\n"
            report_content += f"- **Unit Tests:** {details.get('unit_tests', 'N/A')}\n"
            report_content += f"- **Integration Tests:** {details.get('integration_tests', 'N/A')}\n"

            if details.get('style_issues'):
                report_content += "\n### Style Issues:\n"
                for issue in details['style_issues']:
                    report_content += f"- {issue.get('type', 'unknown')}\n"

            if details.get('test_warnings'):
                report_content += "\n### Test Warnings:\n"
                for warning in details['test_warnings']:
                    report_content += f"- {warning.get('type', 'unknown')}\n"

            if intent.get('arbitration_note'):
                report_content += f"""
---

## CP16 Arbitration Note
{intent['arbitration_note']}

"""

            report_content += f"""
---

## Human Review Checklist

- [ ] Goal is clear and minimal-change?
- [ ] Diff within limits (500 lines max)?
- [ ] Reverse patch present?
- [ ] CP14 verdict reviewed: **{cp14_verdict.get('verdict', 'UNKNOWN')}**
- [ ] CP18 verdict reviewed: **{cp18_verdict.get('verdict', 'UNKNOWN')}**
- [ ] Tests referenced appropriately?
- [ ] Rollback plan acceptable?
- [ ] Security findings addressed (if any)?
- [ ] Validation issues addressed (if any)?

---

## Decision

**Proposed Status:** {intent.get('status', 'unknown')}

**Approve for archive (still no execution)?**

Decision: [ ] APPROVE / [ ] REJECT

Signed: _________________ Date: _________________

---

*Generated by CP17 Scribe*
"""
            report_file.write_text(report_content, encoding="utf-8")
            print(f"Report generated: {report_file}")
            report_path = report_file
            status = "PASS"
        except Exception as exc:  # pragma: no cover - defensive
            error = f"{exc}"
            status = "ERROR"

    uncertainty_note = "report generated successfully" if status == "PASS" else (error or "report generation failed")
    final_snapshot = _build_introspection_snapshot(
        intent=intent_label,
        current_task="report generation (complete)",
        inputs={**inputs_summary, "report_path": str(report_path) if report_path else None},
        constraints=constraints,
        uncertainty=uncertainty_note,
        last_decision=f"status={status}",
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
        "inputs_summary": inputs_summary,
        "decision": {
            "type": "run",
            "reason": "generate summary report",
            "uncertainty": uncertainty_note,
        },
        "action": {
            "requires_approval": False,
            "proposed_change": "emit CP17 summary report",
            "side_effects": [
                "write report to outgoing/reports",
                "update introspection snapshot",
                "append trace log",
            ],
        },
        "outcome": {"status": status, "errors": error, "report_path": str(report_path) if report_path else None},
        "test_mode": test_mode,
        **DEFAULT_RESPECT_FRAME,
    }
    _append_trace_entry(trace_entry)
    return status == "PASS"


def main():
    parser = argparse.ArgumentParser(description="CP17 Report Generator")
    parser.add_argument("--intent-id", required=True, help="Intent ID")
    parser.add_argument("--test-mode", action="store_true", help="Label this run as test_mode for trace logging")
    
    args = parser.parse_args()
    
    generate_report_with_transparency(args.intent_id, test_mode=args.test_mode)


if __name__ == "__main__":
    main()

