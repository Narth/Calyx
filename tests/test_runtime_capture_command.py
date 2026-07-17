from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from staging.work.runtime_capture_adapter.models import (
    CapturedBridgePulse,
    CapturedProcessRow,
    CapturedStationHealth,
    RuntimeCaptureInput,
)
from staging.work.runtime_capture_adapter.operator_capture import (
    main,
    run_live_capture_command,
    run_replay_capture_command,
)


FIXTURE_DIR = Path("staging/work/runtime_capture_adapter/fixtures")


def _load_capture_fixture(name: str) -> RuntimeCaptureInput:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return RuntimeCaptureInput.model_validate(payload["capture_input"])


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_replay_command_writes_full_artifact_chain(tmp_path: Path) -> None:
    fixture = _load_capture_fixture("capture_bridge_declared_active.json")
    input_path = tmp_path / "capture_input.json"
    input_path.write_text(json.dumps(fixture.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    paths = run_replay_capture_command(input_path=input_path, artifacts_root=tmp_path / "artifacts")

    assert paths.raw_capture.exists()
    assert paths.canonical_snapshot.exists()
    assert paths.ingestion_trace.exists()
    assert paths.mapping_validation.exists()
    assert paths.normalization_result.exists()
    assert paths.classification_result.exists()
    assert paths.observer_emission.exists()

    bundles = sorted(paths.governance_bundle_dir.glob("*.json"))
    assert len(bundles) == 1
    bundle_payload = _load_json(bundles[0])
    assert bundle_payload["runtime_multiplicity_validation"]["validation_outcome"] == "multiplicity_declared_and_compliant"
    assert bundle_payload["bridge_pulse_classification"]["pulse_class"] == "active"


def test_live_command_uses_capture_helper_and_writes_raw_first(monkeypatch, tmp_path: Path) -> None:
    capture = RuntimeCaptureInput(
        schema_name="runtime.capture.input",
        schema_version="1.0.0",
        capture_id="runtime_capture.live.mocked",
        corr_id="runtime_capture.live.mocked",
        captured_at_utc=datetime(2026, 4, 2, 20, 30, 0, tzinfo=UTC),
        capture_mode="live_read_only",
        process_rows=[
            CapturedProcessRow(
                pid=35932,
                parent_pid=39060,
                process_name="powershell.exe",
                executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
                command_line=r"powershell -File C:\Calyx_Terminal\Scripts\station_health_loop.ps1",
                started_at_utc=datetime(2026, 4, 2, 16, 57, 9, tzinfo=UTC),
            )
        ],
        station_health=CapturedStationHealth(
            source_path=r"C:\Calyx_Terminal\runtime\station_health.json",
            captured_at_utc=datetime(2026, 4, 2, 20, 30, 0, tzinfo=UTC),
            health="pass",
            cpu_pct=41,
            ram_pct=44,
            interval_s=1.0,
            memory_pressure_tier=0,
            truth_state="fresh",
            top_processes=["Code#27864"],
            entropy_sources=["Code"],
            gpu_metrics_present=False,
        ),
        capture_notes="Mocked live capture for operator command test.",
    )

    monkeypatch.setattr(
        "staging.work.runtime_capture_adapter.operator_capture.capture_live_runtime_state",
        lambda **_kwargs: capture,
    )

    paths = run_live_capture_command(artifacts_root=tmp_path / "artifacts", repo_root=Path("C:/Calyx_Terminal"))

    raw_payload = _load_json(paths.raw_capture)
    assert raw_payload["schema_name"] == "runtime.capture.input"
    assert raw_payload["capture_mode"] == "live_read_only"

    validation_payload = _load_json(paths.mapping_validation)
    assert validation_payload["no_mutation_performed"] is True


def test_replay_command_writes_ambiguity_markers_without_inference(tmp_path: Path) -> None:
    fixture = _load_capture_fixture("capture_ambiguous_partial.json")
    input_path = tmp_path / "capture_input.json"
    input_path.write_text(json.dumps(fixture.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    paths = run_replay_capture_command(input_path=input_path, artifacts_root=tmp_path / "artifacts")

    markers = sorted(paths.ambiguity_dir.glob("*.json"))
    assert markers
    marker_types = {_load_json(path)["ambiguity_type"] for path in markers}
    assert "missing_command_line" in marker_types
    assert "missing_executable_path" in marker_types
    assert "no_matching_service_processes" in marker_types


def test_cli_main_replay_executes_without_runtime_mutation(tmp_path: Path) -> None:
    fixture = _load_capture_fixture("capture_health_single.json")
    input_path = tmp_path / "capture_input.json"
    input_path.write_text(json.dumps(fixture.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    exit_code = main(
        [
            "replay",
            "--input",
            str(input_path),
            "--artifacts-root",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0
    result = _load_json(tmp_path / "artifacts" / fixture.capture_id / "classification" / "runtime.capture.classification_result.json")
    assert result["mapping_validation"]["no_mutation_performed"] is True


def test_replay_command_is_consistent_with_existing_fixture_expectation(tmp_path: Path) -> None:
    fixture = _load_capture_fixture("capture_bridge_missing_notice.json")
    input_path = tmp_path / "capture_input.json"
    input_path.write_text(json.dumps(fixture.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")

    paths = run_replay_capture_command(input_path=input_path, artifacts_root=tmp_path / "artifacts")

    result = _load_json(paths.classification_result)
    bundle = result["observer_emission"]["governance_bundles"][0]
    assert bundle["runtime_multiplicity_validation"]["validation_outcome"] == "multiplicity_declared_but_noncompliant"
    assert bundle["runtime_multiplicity_noncompliance"]["noncompliance_type"] == "missing_launch_notice"
