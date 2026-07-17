from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.runtime_observer_simulation.models import (
    PRIMARY_RUNTIME_OBSERVER_MODELS,
    RuntimeObserverEmission,
    RuntimeObserverSnapshot,
    RUNTIME_OBSERVER_SCHEMA_VERSION,
)
from staging.work.runtime_observer_simulation.observer import simulate_runtime_observer


FIXTURE_DIR = Path("staging/work/runtime_observer_simulation/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_observer_simulation/schemas")
FIXTURE_FILES = [
    "observer_health_single.json",
    "observer_health_duplicate.json",
    "observer_bridge_declared_active.json",
    "observer_bridge_idle.json",
    "observer_bridge_missing_launch_notice.json",
    "observer_bridge_duplicate.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_fixture(name: str) -> tuple[RuntimeObserverSnapshot, RuntimeObserverEmission]:
    payload = _load_json(FIXTURE_DIR / name)
    snapshot = RuntimeObserverSnapshot.model_validate(payload["snapshot"])
    emission = RuntimeObserverEmission.model_validate(payload["emission"])
    return snapshot, emission


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_snapshot_and_emission_validate(fixture_name: str) -> None:
    snapshot, emission = _load_fixture(fixture_name)
    assert snapshot.snapshot_id == emission.snapshot_id
    assert emission.governance_bundles


def test_schema_exports_exist_and_are_versioned() -> None:
    for artifact_type in PRIMARY_RUNTIME_OBSERVER_MODELS:
        payload = _load_json(SCHEMA_DIR / f"{artifact_type}.schema.json")
        assert payload["properties"]["schema_version"]["const"] == RUNTIME_OBSERVER_SCHEMA_VERSION


def test_health_single_process_emits_topology_valid() -> None:
    _, emission = _load_fixture("observer_health_single.json")
    bundle = emission.governance_bundles[0]
    assert bundle.service_declaration.service_name == "station_health_loop"
    assert bundle.runtime_multiplicity_validation.validation_outcome == "topology_valid"
    assert bundle.health_authoritative_snapshot.cadence_compliant is True
    assert bundle.health_enrichment_snapshot is not None


def test_health_duplicate_processes_emit_duplicate_concerning() -> None:
    _, emission = _load_fixture("observer_health_duplicate.json")
    bundle = emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "duplicate_writer_attempt"


def test_bridge_declared_wrapper_child_active_is_compliant() -> None:
    _, emission = _load_fixture("observer_bridge_declared_active.json")
    bundle = emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "multiplicity_declared_and_compliant"
    assert bundle.runtime_launch_notice is not None
    assert bundle.bridge_pulse_classification.pulse_class == "active"


def test_bridge_idle_pair_without_notice_is_declared_but_noncompliant() -> None:
    _, emission = _load_fixture("observer_bridge_missing_launch_notice.json")
    bundle = emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "multiplicity_declared_but_noncompliant"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "missing_launch_notice"
    assert bundle.bridge_pulse_classification.pulse_class == "idle"


def test_bridge_duplicate_pairs_emit_duplicate_concerning() -> None:
    _, emission = _load_fixture("observer_bridge_duplicate.json")
    bundle = emission.governance_bundles[0]
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "duplicate_overseer_attempt"


def test_observer_regenerates_fixture_classifications_cleanly() -> None:
    snapshot, emission = _load_fixture("observer_bridge_idle.json")
    regenerated = simulate_runtime_observer(snapshot)
    assert regenerated.snapshot_id == emission.snapshot_id
    assert regenerated.governance_bundles[0].runtime_multiplicity_validation.validation_outcome == (
        emission.governance_bundles[0].runtime_multiplicity_validation.validation_outcome
    )
    assert regenerated.governance_bundles[0].bridge_pulse_classification.pulse_class == "idle"


def test_snapshot_requires_processes() -> None:
    payload = _load_json(FIXTURE_DIR / "observer_health_single.json")["snapshot"]
    payload["processes"] = []
    with pytest.raises(ValidationError):
        RuntimeObserverSnapshot.model_validate(payload)


def test_health_context_without_matching_process_raises() -> None:
    payload = _load_json(FIXTURE_DIR / "observer_health_single.json")["snapshot"]
    payload["processes"] = [
        {
            "pid": 999,
            "parent_pid": 1,
            "executable_path": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            "command_line": "powershell -File C:\\Calyx_Terminal\\Scripts\\unrelated.ps1",
            "started_at_utc": "2026-04-01T19:49:00Z",
        }
    ]
    snapshot = RuntimeObserverSnapshot.model_validate(payload)
    with pytest.raises(ValueError):
        simulate_runtime_observer(snapshot)


def test_bridge_active_vs_idle_is_derived_from_counts() -> None:
    payload = _load_json(FIXTURE_DIR / "observer_bridge_idle.json")["snapshot"]
    payload["bridge_context"]["objectives_count"] = 1
    payload["bridge_context"]["planned_tasks_count"] = 0
    payload["bridge_context"]["dispatched_count"] = 0
    snapshot = RuntimeObserverSnapshot.model_validate(payload)
    emission = simulate_runtime_observer(snapshot)
    assert emission.governance_bundles[0].bridge_pulse_classification.pulse_class == "active"
    assert emission.governance_bundles[0].bridge_pulse_classification.idle_mode_active is False
