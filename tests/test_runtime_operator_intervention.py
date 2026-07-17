from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.runtime_capture_adapter.mapper import classify_capture
from staging.work.runtime_capture_adapter.models import RuntimeCaptureClassificationResult, RuntimeCaptureInput
from staging.work.runtime_operator_intervention.models import RuntimeOperatorIntervention
from staging.work.runtime_operator_intervention.protocol import (
    build_intervention_receipt,
    build_intervention_receipt_from_paths,
)
from staging.work.runtime_operator_summary.models import RuntimeOperatorSummary


FIXTURE_DIR = Path("staging/work/runtime_operator_intervention/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_operator_intervention/schemas")
SUMMARY_FIXTURE_DIR = Path("staging/work/runtime_operator_summary/fixtures")
CAPTURE_FIXTURE_DIR = Path("staging/work/runtime_capture_adapter/fixtures")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_summary() -> RuntimeOperatorSummary:
    return RuntimeOperatorSummary.model_validate(_load_json(SUMMARY_FIXTURE_DIR / "operator_summary_live_operator_smoke.json"))


def _load_classification() -> RuntimeCaptureClassificationResult:
    payload = _load_json(CAPTURE_FIXTURE_DIR / "capture_bridge_duplicate.json")
    return classify_capture(RuntimeCaptureInput.model_validate(payload["capture_input"]))


def test_fixtures_validate() -> None:
    for name in [
        "operator_intervention_observe_only.json",
        "operator_intervention_soft_targeted.json",
        "operator_intervention_hard_station_halt.json",
    ]:
        RuntimeOperatorIntervention.model_validate(_load_json(FIXTURE_DIR / name))


def test_schema_export_exists_and_is_versioned() -> None:
    payload = _load_json(SCHEMA_DIR / "runtime_operator_intervention.schema.json")
    assert payload["properties"]["schema_version"]["const"] == "1.0.0"


def test_observe_tier_requires_observe_only_action() -> None:
    payload = _load_json(FIXTURE_DIR / "operator_intervention_observe_only.json")
    payload["action_taken"]["action_type"] = "inspect_process"
    with pytest.raises(ValidationError):
        RuntimeOperatorIntervention.model_validate(payload)


def test_soft_intervention_requires_targeted_action() -> None:
    payload = _load_json(FIXTURE_DIR / "operator_intervention_soft_targeted.json")
    payload["action_taken"]["relevant_process_ids"] = []
    with pytest.raises(ValidationError):
        RuntimeOperatorIntervention.model_validate(payload)


def test_protected_process_termination_requires_override() -> None:
    summary = _load_summary()
    classification = _load_classification()
    with pytest.raises(ValidationError):
        build_intervention_receipt(
            summary=summary,
            classification=classification,
            intervention_id="runtime.intervention.invalid.protected",
            intervention_tier="tier_1_soft_intervention",
            action_type="terminate_process",
            operator_reasoning="Improper protected target test.",
            observed_processes=[
                {
                    "pid": 999,
                    "process_name": "WmiPrvSE.exe",
                    "command_line": "WmiPrvSE.exe",
                    "service_name": None,
                    "governance_role": None,
                    "notes": "Protected process fixture.",
                }
            ],
            commands_executed=["Stop-Process -Id 999"],
        )


def test_blind_python_kill_pattern_is_blocked() -> None:
    summary = _load_summary()
    classification = _load_classification()
    with pytest.raises(ValidationError):
        build_intervention_receipt(
            summary=summary,
            classification=classification,
            intervention_id="runtime.intervention.invalid.blind",
            intervention_tier="tier_1_soft_intervention",
            action_type="terminate_multiple_processes",
            operator_reasoning="Improper blind kill test.",
            observed_processes=[
                {
                    "pid": 21520,
                    "process_name": "python.exe",
                    "command_line": "python -B -m calyx.cbo.bridge_overseer",
                    "service_name": "bridge_overseer",
                    "governance_role": "bridge_cycle_owner",
                    "notes": "Representative process.",
                }
            ],
            commands_executed=["taskkill /IM python.exe /F"],
        )


def test_intervention_requires_summary_and_classification_refs() -> None:
    payload = _load_json(FIXTURE_DIR / "operator_intervention_soft_targeted.json")
    payload["observed_evidence"] = [
        item for item in payload["observed_evidence"] if item["artifact_type"] != "runtime.capture.classification_result"
    ]
    with pytest.raises(ValidationError):
        RuntimeOperatorIntervention.model_validate(payload)


def test_generation_from_paths_matches_direct_generation(tmp_path: Path) -> None:
    summary = _load_summary()
    classification = _load_classification()
    summary_path = tmp_path / "summary.json"
    classification_path = tmp_path / "classification.json"
    summary_path.write_text(json.dumps(summary.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    classification_path.write_text(json.dumps(classification.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    observed_processes = [
        {
            "pid": 14152,
            "process_name": "powershell.exe",
            "command_line": "powershell -File Scripts\\station_health_loop.ps1",
            "service_name": "station_health_loop",
            "governance_role": "duplicate_peer",
            "notes": "Representative duplicate process.",
        }
    ]
    fixed_now = datetime(2026, 4, 4, 20, 0, 0, tzinfo=UTC)
    direct = build_intervention_receipt(
        summary=summary,
        classification=classification,
        intervention_id="runtime.intervention.compare",
        intervention_tier="tier_1_soft_intervention",
        action_type="terminate_process",
        operator_reasoning="Comparison fixture.",
        observed_processes=observed_processes,
        commands_executed=["Stop-Process -Id 14152"],
        timestamp_utc=fixed_now,
    )
    by_path = build_intervention_receipt_from_paths(
        summary_path=summary_path,
        classification_path=classification_path,
        intervention_id="runtime.intervention.compare",
        intervention_tier="tier_1_soft_intervention",
        action_type="terminate_process",
        operator_reasoning="Comparison fixture.",
        observed_processes=observed_processes,
        commands_executed=["Stop-Process -Id 14152"],
        timestamp_utc=fixed_now,
    )
    assert direct.model_dump(mode="json") == by_path.model_dump(mode="json")
