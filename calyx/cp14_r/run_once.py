"""
CP14-R Phase 1 (read-only) run_once.

Reads recent logs, computes basic outcome density signals (best-effort),
identifies potential bottlenecks, and emits RES v0.1-compliant reflection
and append-only reports. Safe Mode only: no config writes, no schedulers,
no capability changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.calyx_telemetry_logger import now_iso
from tools.reflection_output_helper import emit_reflection_node_output

LOGS = Path("logs")
CALYX_LOGS = LOGS / "calyx"
RESOURCE_USAGE_PATH = LOGS / "system" / "resource_usage.jsonl"
TASK_OUTCOMES_PATH = LOGS / "tasks" / "task_outcomes.jsonl"
NODE_OUTPUTS_PATH = CALYX_LOGS / "node_outputs.jsonl"

REPORT_OUTCOME_DENSITY = CALYX_LOGS / "cp14_r_outcome_density_report.jsonl"
REPORT_BOTTLENECK = CALYX_LOGS / "cp14_r_causal_bottleneck_analysis.jsonl"
REPORT_GOV_DEBT = CALYX_LOGS / "cp14_r_governance_debt_register.jsonl"


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


def compute_outcome_density(resource_records: List[Dict[str, Any]], task_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    useful = 0.0
    watt_gb_seconds = 0.0
    missing = False
    for t in task_records:
        useful += float(t.get("useful_output", 0.0) or 0.0)
    for r in resource_records:
        power = r.get("power_w")
        mem = r.get("memory_gb")
        dur = r.get("duration_seconds")
        if power is None or mem is None or dur is None:
            missing = True
            continue
        watt_gb_seconds += float(power) * float(mem) * float(dur)
    density = None
    if watt_gb_seconds > 0:
        density = useful / watt_gb_seconds
    return {
        "useful_output_total": useful,
        "watt_gb_seconds_total": watt_gb_seconds,
        "outcome_density": density,
        "data_missing": missing or watt_gb_seconds == 0,
    }


def analyze_bottlenecks(resource_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Simple heuristics: find max usage seen (if available)
    max_power = None
    max_mem = None
    max_io = None
    for r in resource_records:
        pw = r.get("power_w")
        mb = r.get("memory_gb")
        io = r.get("io_mb_s")
        if isinstance(pw, (int, float)):
            max_power = pw if max_power is None else max(max_power, pw)
        if isinstance(mb, (int, float)):
            max_mem = mb if max_mem is None else max(max_mem, mb)
        if isinstance(io, (int, float)):
            max_io = io if max_io is None else max(max_io, io)
    return {
        "max_power_w": max_power,
        "max_memory_gb": max_mem,
        "max_io_mb_s": max_io,
        "notes": "Heuristic maxima; no scaling recommendations in Safe Mode.",
    }


def detect_governance_debt(outcome_density: Dict[str, Any]) -> List[str]:
    debt = []
    if outcome_density.get("data_missing"):
        debt.append("Resource/task data incomplete; cannot verify Outcome Density (R2/R3).")
    if outcome_density.get("outcome_density") is None:
        debt.append("Outcome Density not computable; resolve bottlenecks and ensure watt*GB*sec measurements.")
    return debt


def run_once(window_limit: Optional[int] = None) -> Dict[str, Any]:
    node_outputs = _read_jsonl(NODE_OUTPUTS_PATH)
    resource_records = _read_jsonl(RESOURCE_USAGE_PATH)
    task_records = _read_jsonl(TASK_OUTCOMES_PATH)

    if window_limit:
        node_outputs = node_outputs[-window_limit:]
        resource_records = resource_records[-window_limit:]
        task_records = task_records[-window_limit:]

    outcome_density = compute_outcome_density(resource_records, task_records)
    bottlenecks = analyze_bottlenecks(resource_records)
    governance_debt = detect_governance_debt(outcome_density)

    ts = now_iso()
    _append_jsonl(
        REPORT_OUTCOME_DENSITY,
        {"timestamp": ts, "outcome_density": outcome_density, "window": window_limit},
    )
    _append_jsonl(
        REPORT_BOTTLENECK,
        {"timestamp": ts, "bottlenecks": bottlenecks, "window": window_limit},
    )
    _append_jsonl(
        REPORT_GOV_DEBT,
        {"timestamp": ts, "governance_debt": governance_debt, "window": window_limit},
    )

    drift = []
    if governance_debt:
        drift.append(
            {
                "type": "policy",
                "severity": "medium",
                "evidence": "; ".join(governance_debt),
                "detected_by": "CP14-R",
            }
        )

    reflection = emit_reflection_node_output(
        reflection_type="migration_reflection",
        summary="CP14-R run (read-only) recorded outcome density, bottlenecks, and governance debt signals.",
        analysis={
            "capability_impact": "none",
            "alignment_impact": "strengthened",
            "risk_vector_change": "unchanged",
            "jurisdictional_effect": "none",
            "identity_effect": "strengthened",
            "interpretability_effect": "improved",
        },
        advisories=[
            "Resolve data gaps in resource/task logs to enable Outcome Density checks (R2/R3).",
            "No scaling recommended; remain deny-all and treat missing data as governance debt.",
        ],
        drift_signals=drift,
        human_primacy_respected=True,
        input_reference="cp14_r_phase1_run",
        node_id="CP14-R",
        node_role="cp14_r_validator",
        source="cp14_r.run_once",
    )
    return reflection


if __name__ == "__main__":
    run_once(window_limit=500)
