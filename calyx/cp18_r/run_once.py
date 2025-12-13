"""
CP18-R Phase 1 (read-only) run_once.

Scans logs for identity drift, authority inflation, and scope violations.
Emits append-only registers and a RES v0.1 reflection. Safe Mode only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.reflection_output_helper import emit_reflection_node_output
from tools.calyx_telemetry_logger import now_iso
from tools.refusal_snippets import capability_escalation_refusal

CALYX_LOGS = Path("logs") / "calyx"
NODE_OUTPUTS_PATH = CALYX_LOGS / "node_outputs.jsonl"
GOV_REFLECTIONS_PATH = CALYX_LOGS / "governance_reflections.jsonl"

DRIFT_REGISTER = CALYX_LOGS / "cp18_r_identity_drift_register.jsonl"
SCOPE_VIOLATION_LOG = CALYX_LOGS / "cp18_r_scope_violation_log.jsonl"
RESOURCE_IDENTITY_GUARD = CALYX_LOGS / "cp18_r_resource_identity_guard.jsonl"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
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


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


def scan_identity_drifts(records: List[Dict[str, Any]]) -> List[str]:
    drifts = []
    for rec in records:
        text = json.dumps(rec, ensure_ascii=False)
        if "I must" in text or "require more hardware" in text or "grant me" in text:
            drifts.append("Authority inflation detected in node outputs.")
        role = rec.get("node_role")
        if role and isinstance(role, str) and role.lower().startswith("oracle"):
            drifts.append("Oracle-like role declaration detected.")
        if "Public Reflection" in text and ("authoritative" in text or "must comply" in text):
            drifts.append("Public reflection tone too authoritative; PRTL constraints needed.")
    return drifts


def scan_scope_violations(records: List[Dict[str, Any]]) -> List[str]:
    violations = []
    for rec in records:
        role = (rec.get("node_role") or "").lower()
        summary = json.dumps(rec.get("outputs") or rec.get("payload") or {}, ensure_ascii=False)
        if "network access" in summary or "policy change" in summary:
            violations.append(f"Scope concern in role {role}: mentions network/policy change.")
        if "hardware" in summary and "require" in summary:
            violations.append(f"Scope concern in role {role}: hardware requirement language.")
    return violations


def scan_resource_identity_guard(records: List[Dict[str, Any]]) -> List[str]:
    notes = []
    for rec in records:
        txt = json.dumps(rec, ensure_ascii=False)
        if "scale" in txt and "identity" in txt:
            notes.append("Identity-linked scaling language observed; review under R-series.")
    return notes


def run_once(window_limit: Optional[int] = None) -> Dict[str, Any]:
    node_outputs = _read_jsonl(NODE_OUTPUTS_PATH)
    gov_reflections = _read_jsonl(GOV_REFLECTIONS_PATH)
    if window_limit:
        node_outputs = node_outputs[-window_limit:]
        gov_reflections = gov_reflections[-window_limit:]

    identity_drifts = scan_identity_drifts(node_outputs + gov_reflections)
    scope_violations = scan_scope_violations(node_outputs + gov_reflections)
    resource_identity_notes = scan_resource_identity_guard(node_outputs + gov_reflections)

    ts = now_iso()
    if identity_drifts:
        _append_jsonl(DRIFT_REGISTER, {"timestamp": ts, "drifts": identity_drifts})
    if scope_violations:
        _append_jsonl(SCOPE_VIOLATION_LOG, {"timestamp": ts, "violations": scope_violations})
    if resource_identity_notes:
        _append_jsonl(RESOURCE_IDENTITY_GUARD, {"timestamp": ts, "notes": resource_identity_notes})

    drift_signals = []
    for msg in identity_drifts:
        drift_signals.append({"type": "identity", "severity": "medium", "evidence": msg, "detected_by": "CP18-R"})
    for msg in scope_violations:
        drift_signals.append({"type": "policy", "severity": "medium", "evidence": msg, "detected_by": "CP18-R"})
    for msg in resource_identity_notes:
        drift_signals.append({"type": "policy", "severity": "low", "evidence": msg, "detected_by": "CP18-R"})

    reflection = emit_reflection_node_output(
        reflection_type="migration_reflection",
        summary="CP18-R run (read-only) scanned for identity/scope drift and resource-identity concerns.",
        analysis={
            "capability_impact": "none",
            "alignment_impact": "strengthened",
            "risk_vector_change": "decreased" if drift_signals else "unchanged",
            "jurisdictional_effect": "none",
            "identity_effect": "strengthened",
            "interpretability_effect": "improved",
        },
        advisories=[
            "Maintain Safe Mode/deny-all; treat identity inflation or scope creep as drift.",
            "Block any scaling arguments tied to identity claims; defer to R3 gates.",
        ],
        drift_signals=drift_signals,
        human_primacy_respected=True,
        input_reference="cp18_r_phase1_run",
        node_id="CP18-R",
        node_role="cp18_r_identity_sentinel",
        source="cp18_r.run_once",
    )
    return reflection


if __name__ == "__main__":
    run_once(window_limit=500)
