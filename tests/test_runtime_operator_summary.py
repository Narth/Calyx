from __future__ import annotations

import json
from pathlib import Path

from staging.work.runtime_capture_adapter.mapper import classify_capture
from staging.work.runtime_capture_adapter.models import RuntimeCaptureInput
from staging.work.runtime_operator_summary.models import RuntimeOperatorSummary
from staging.work.runtime_operator_summary.summary import (
    generate_runtime_operator_summary,
    generate_runtime_operator_summary_from_paths,
)


CAPTURE_FIXTURE_DIR = Path("staging/work/runtime_capture_adapter/fixtures")
SUMMARY_FIXTURE_DIR = Path("staging/work/runtime_operator_summary/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_operator_summary/schemas")


def _load_capture(name: str) -> RuntimeCaptureInput:
    payload = json.loads((CAPTURE_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return RuntimeCaptureInput.model_validate(payload["capture_input"])


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_summary_fixtures_validate() -> None:
    for name in [
        "operator_summary_health_single.json",
        "operator_summary_health_duplicate.json",
        "operator_summary_bridge_missing_notice.json",
        "operator_summary_health_fail_stale.json",
    ]:
        RuntimeOperatorSummary.model_validate(_load_json(SUMMARY_FIXTURE_DIR / name))


def test_schema_export_exists_and_is_versioned() -> None:
    payload = _load_json(SCHEMA_DIR / "runtime_operator_summary.schema.json")
    assert payload["properties"]["schema_version"]["const"] == "1.1.0"


def test_health_single_summary_is_normal_and_traceable() -> None:
    capture = _load_capture("capture_health_single.json")
    summary = generate_runtime_operator_summary(capture, classify_capture(capture))
    assert summary.operator_risk_signal == "NORMAL"
    assert summary.system_load_snapshot.health_state == "pass"
    assert summary.top_processes
    assert summary.workstation_load_view.top_processes == summary.top_processes
    assert summary.station_runtime_view.governance_posture == summary.governance_posture
    assert summary.system_load_condition == "normal"
    assert summary.governance_compliance_condition == "compliant"


def test_health_duplicate_summary_is_risk_and_preserves_governed_ambiguity() -> None:
    capture = _load_capture("capture_health_duplicate.json")
    summary = generate_runtime_operator_summary(capture, classify_capture(capture))
    assert summary.operator_risk_signal == "RISK"
    assert any(item.validation_outcome == "duplicate_concerning" for item in summary.governance_posture)
    assert any(item.ambiguity_type == "health_cadence_unresolved" for item in summary.ambiguities)
    assert any(gap.gap_type == "topology_mismatch" for gap in summary.attribution_gaps)


def test_bridge_missing_notice_summary_is_unexpected() -> None:
    capture = _load_capture("capture_bridge_missing_notice.json")
    summary = generate_runtime_operator_summary(capture, classify_capture(capture))
    assert summary.operator_risk_signal == "UNEXPECTED"
    assert any(item.validation_outcome == "multiplicity_declared_but_noncompliant" for item in summary.governance_posture)
    assert any(signal.signal_type == "multiplicity_noncompliance" for signal in summary.expectation_signals)
    assert summary.governance_compliance_condition == "noncompliant"
    assert any(gap.gap_type == "missing_launch_notice" for gap in summary.attribution_gaps)


def test_health_fail_stale_summary_is_critical() -> None:
    payload = _load_json(SUMMARY_FIXTURE_DIR / "operator_summary_health_fail_stale.json")
    summary = RuntimeOperatorSummary.model_validate(payload)
    assert summary.operator_risk_signal == "CRITICAL"
    assert any(signal.signal_type == "health_fail" for signal in summary.expectation_signals)
    assert summary.system_load_condition in ("normal", "elevated", "high", "unknown")


def test_summary_generation_is_deterministic_for_same_inputs(tmp_path: Path) -> None:
    capture = _load_capture("capture_health_single.json")
    classified = classify_capture(capture)
    first = generate_runtime_operator_summary(capture, classified)
    second = generate_runtime_operator_summary(capture, classified)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_summary_from_paths_matches_direct_generation(tmp_path: Path) -> None:
    capture = _load_capture("capture_health_single.json")
    classified = classify_capture(capture)
    capture_path = tmp_path / "capture.json"
    classified_path = tmp_path / "classified.json"
    capture_path.write_text(json.dumps(capture.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    classified_path.write_text(json.dumps(classified.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    by_path = generate_runtime_operator_summary_from_paths(capture_path, classified_path)
    direct = generate_runtime_operator_summary(capture, classified)
    assert by_path.model_dump(mode="json") == direct.model_dump(mode="json")


def test_station_runtime_view_is_subset_or_candidate_set() -> None:
    capture = _load_capture("capture_bridge_missing_notice.json")
    summary = generate_runtime_operator_summary(capture, classify_capture(capture))
    capture_pids = {row.pid for row in capture.process_rows}
    summary_pids = {row.pid for row in summary.station_runtime_view.processes}
    assert summary_pids.issubset(capture_pids)
    assert any(row.station_membership == "known_governed_service" for row in summary.station_runtime_view.processes)


def test_live_summary_preserves_capture_layer_gaps_without_guessing() -> None:
    payload = _load_json(SUMMARY_FIXTURE_DIR / "operator_summary_live_operator_smoke.json")
    summary = RuntimeOperatorSummary.model_validate(payload)
    assert any(gap.gap_type == "missing_command_line_data" for gap in summary.attribution_gaps)
    assert any(gap.gap_type == "missing_executable_path_data" for gap in summary.attribution_gaps)
    assert any("System load condition:" in reason for reason in summary.operator_risk_reasoning)
    assert any("Governance compliance condition:" in reason for reason in summary.operator_risk_reasoning)
