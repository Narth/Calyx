from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.runtime_capture_adapter.capture import capture_live_runtime_state, load_capture_input
from staging.work.runtime_capture_adapter.mapper import classify_capture, normalize_capture_to_snapshot
from staging.work.runtime_capture_adapter.models import (
    PRIMARY_RUNTIME_CAPTURE_MODELS,
    CapturedBridgePulse,
    CapturedProcessRow,
    CapturedStationHealth,
    RuntimeCaptureInput,
    RUNTIME_CAPTURE_SCHEMA_VERSION,
)


FIXTURE_DIR = Path("staging/work/runtime_capture_adapter/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_capture_adapter/schemas")
FIXTURE_FILES = [
    "capture_health_single.json",
    "capture_health_duplicate.json",
    "capture_bridge_declared_active.json",
    "capture_bridge_missing_notice.json",
    "capture_bridge_duplicate.json",
    "capture_ambiguous_partial.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_payloads_validate(fixture_name: str) -> None:
    payload = _load_json(FIXTURE_DIR / fixture_name)
    RuntimeCaptureInput.model_validate(payload["capture_input"])
    if "classified_result" in payload:
        assert payload["classified_result"]["schema_version"] == RUNTIME_CAPTURE_SCHEMA_VERSION
    if "normalization_result" in payload:
        assert payload["normalization_result"]["schema_version"] == RUNTIME_CAPTURE_SCHEMA_VERSION


def test_schema_exports_exist_and_are_versioned() -> None:
    for artifact_type in PRIMARY_RUNTIME_CAPTURE_MODELS:
        payload = _load_json(SCHEMA_DIR / f"{artifact_type}.schema.json")
        assert payload["properties"]["schema_version"]["const"] == RUNTIME_CAPTURE_SCHEMA_VERSION


def test_health_single_capture_maps_and_classifies() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_health_single.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    classified = classify_capture(capture)
    bundle = classified.observer_emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "topology_valid"
    assert bundle.health_authoritative_snapshot.cadence_compliant is True
    assert classified.mapping_validation.no_mutation_performed is True


def test_health_duplicate_capture_emits_ambiguity_and_duplicate_concerning() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_health_duplicate.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    classified = classify_capture(capture)
    bundle = classified.observer_emission.governance_bundles[0]
    ambiguity_types = {marker.ambiguity_type for marker in classified.normalization.ambiguity_markers}
    assert "health_cadence_unresolved" in ambiguity_types
    assert "health_expiry_sweep_unresolved" in ambiguity_types
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"


def test_bridge_declared_active_capture_maps_to_declared_compliance() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_bridge_declared_active.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    classified = classify_capture(capture)
    bundle = classified.observer_emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "multiplicity_declared_and_compliant"
    assert bundle.bridge_pulse_classification.pulse_class == "active"


def test_bridge_missing_notice_capture_maps_to_declared_but_noncompliant() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_bridge_missing_notice.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    classified = classify_capture(capture)
    bundle = classified.observer_emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "multiplicity_declared_but_noncompliant"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "missing_launch_notice"


def test_bridge_duplicate_capture_maps_to_duplicate_concerning() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_bridge_duplicate.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    classified = classify_capture(capture)
    bundle = classified.observer_emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "duplicate_overseer_attempt"


def test_ambiguous_partial_capture_normalizes_without_forced_classification() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_ambiguous_partial.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    normalization = normalize_capture_to_snapshot(capture)
    ambiguity_types = {marker.ambiguity_type for marker in normalization.ambiguity_markers}
    assert "missing_command_line" in ambiguity_types
    assert "missing_executable_path" in ambiguity_types
    assert "no_matching_service_processes" in ambiguity_types
    assert normalization.canonical_snapshot.health_context is None


def test_mapping_is_deterministic_for_same_input() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_bridge_declared_active.json")
    capture = RuntimeCaptureInput.model_validate(payload["capture_input"])
    first = normalize_capture_to_snapshot(capture)
    second = normalize_capture_to_snapshot(capture)
    assert first.canonical_snapshot.model_dump(mode="json") == second.canonical_snapshot.model_dump(mode="json")
    assert first.ingestion_trace.defaulted_fields == second.ingestion_trace.defaulted_fields


def test_load_capture_input_round_trips_file() -> None:
    path = FIXTURE_DIR / "capture_health_single.json"
    payload = _load_json(path)
    temp = Path("staging/work/runtime_capture_adapter/fixtures/_tmp_roundtrip_capture.json")
    temp.write_text(json.dumps(payload["capture_input"], indent=2) + "\n", encoding="utf-8")
    try:
        loaded = load_capture_input(temp)
        assert loaded.capture_id == "capture.health.single"
    finally:
        temp.unlink(missing_ok=True)


def test_capture_input_requires_process_rows() -> None:
    payload = _load_json(FIXTURE_DIR / "capture_health_single.json")["capture_input"]
    payload["process_rows"] = []
    with pytest.raises(ValidationError):
        RuntimeCaptureInput.model_validate(payload)


def test_live_capture_helper_is_read_only_and_builds_input(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path("C:/Calyx_Terminal")

    monkeypatch.setattr(
        "staging.work.runtime_capture_adapter.capture._capture_process_rows",
        lambda: [
            CapturedProcessRow(
                pid=35932,
                parent_pid=39060,
                process_name="powershell.exe",
                executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
                command_line=r"powershell -File C:\Calyx_Terminal\Scripts\station_health_loop.ps1",
                started_at_utc=datetime(2026, 4, 2, 16, 57, 9, tzinfo=UTC),
            )
        ],
    )
    monkeypatch.setattr("staging.work.runtime_capture_adapter.capture._capture_ports_by_pid", lambda: {})
    monkeypatch.setattr(
        "staging.work.runtime_capture_adapter.capture._read_station_health",
        lambda _path: CapturedStationHealth(
            source_path=r"C:\Calyx_Terminal\runtime\station_health.json",
            captured_at_utc=datetime(2026, 4, 2, 19, 0, 0, tzinfo=UTC),
            health="pass",
            cpu_pct=37,
            ram_pct=43,
            interval_s=1.0,
            memory_pressure_tier=0,
            truth_state="fresh",
            top_processes=["Code#1"],
            entropy_sources=["Code#1"],
            gpu_metrics_present=False,
        ),
    )
    monkeypatch.setattr("staging.work.runtime_capture_adapter.capture._read_bridge_pulse", lambda _path: None)

    capture = capture_live_runtime_state(repo_root=repo_root, capture_id="live.capture.test", corr_id="live.capture.test")
    assert capture.capture_mode == "live_read_only"
    assert capture.process_rows[0].pid == 35932
    assert capture.station_health is not None


def test_bridge_detail_parser_defaults_without_silent_failure() -> None:
    capture = RuntimeCaptureInput(
        schema_name="runtime.capture.input",
        schema_version="1.0.0",
        capture_id="capture.bridge.unresolved",
        corr_id="capture.bridge.unresolved",
        captured_at_utc=datetime(2026, 4, 2, 20, 0, 0, tzinfo=UTC),
        capture_mode="offline_replay",
        process_rows=[
            CapturedProcessRow(
                pid=35056,
                parent_pid=31764,
                process_name="python.exe",
                executable_path=r"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe",
                command_line=r"python -B -m calyx.cbo.bridge_overseer",
                started_at_utc=datetime(2026, 4, 2, 11, 48, 46, tzinfo=UTC),
            ),
            CapturedProcessRow(
                pid=35192,
                parent_pid=35056,
                process_name="python.exe",
                executable_path=r"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe",
                command_line=r"python -B -m calyx.cbo.bridge_overseer",
                started_at_utc=datetime(2026, 4, 2, 11, 48, 46, tzinfo=UTC),
            ),
        ],
        bridge_pulse=CapturedBridgePulse(
            source_path=r"C:\Calyx_Terminal\metrics\bridge_pulse.csv",
            captured_at_utc=datetime(2026, 4, 2, 20, 0, 0, tzinfo=UTC),
            phase="bridge_pulse",
            status="steady",
            details="resource_ok=1 policy_ok=1 tes_mean20=94.2",
        ),
        capture_notes="Bridge counts absent from details string.",
    )
    normalization = normalize_capture_to_snapshot(capture)
    ambiguity_types = {marker.ambiguity_type for marker in normalization.ambiguity_markers}
    assert "bridge_work_state_unresolved" in ambiguity_types
    assert "bridge_idle_reason_unresolved" in ambiguity_types
    assert normalization.canonical_snapshot.bridge_context.objectives_count == 0


def test_live_process_capture_skips_zero_pid_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "ProcessId": 0,
            "ParentProcessId": 0,
            "Name": "System Idle Process",
            "ExecutablePath": None,
            "CommandLine": None,
            "CreationDate": None,
        },
        {
            "ProcessId": 35932,
            "ParentProcessId": 39060,
            "Name": "powershell.exe",
            "ExecutablePath": r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            "CommandLine": r"powershell -File C:\Calyx_Terminal\Scripts\station_health_loop.ps1",
            "CreationDate": {"DateTime": "2026-04-02 16:57:09+00:00"},
        },
    ]

    class _Completed:
        stdout = json.dumps(payload)

    monkeypatch.setattr(
        "staging.work.runtime_capture_adapter.capture.subprocess.run",
        lambda *args, **kwargs: _Completed(),
    )

    from staging.work.runtime_capture_adapter.capture import _capture_process_rows

    rows = _capture_process_rows()
    assert len(rows) == 1
    assert rows[0].pid == 35932
