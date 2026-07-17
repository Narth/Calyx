from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
import pytest

from staging.work.runtime_reconciliation.engine import (
    build_default_service_declarations,
    reconcile_runtime_request,
    reconcile_runtime_request_from_paths,
)
from staging.work.runtime_reconciliation.models import (
    PRIMARY_RUNTIME_RECONCILIATION_MODELS,
    RuntimeReconciliationBundle,
    RuntimeReconciliationRequest,
)
from staging.work.runtime_observer_simulation.models import RuntimeObserverSnapshot


FIXTURE_DIR = Path("staging/work/runtime_reconciliation/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_reconciliation/schemas")
FIXTURE_FILES = [
    "singleton_no_resident_permit.json",
    "singleton_existing_attach.json",
    "bounded_below_max_permit.json",
    "bounded_exceeds_max_refuse.json",
    "wrapper_child_pair_attach.json",
    "ambiguous_powershell_block.json",
    "undeclared_duplicate_detected.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_fixture(name: str) -> tuple[RuntimeObserverSnapshot, RuntimeReconciliationRequest, RuntimeReconciliationBundle]:
    payload = _load_json(FIXTURE_DIR / name)
    snapshot = RuntimeObserverSnapshot.model_validate(payload["snapshot"])
    request = RuntimeReconciliationRequest.model_validate(payload["request"])
    bundle = RuntimeReconciliationBundle.model_validate(payload["bundle"])
    return snapshot, request, bundle


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_bundle_validates(fixture_name: str) -> None:
    _, _, bundle = _load_fixture(fixture_name)
    assert bundle.operator_view.requested_disposition == bundle.result.disposition


def test_schema_exports_exist_and_are_versioned() -> None:
    for artifact_type in PRIMARY_RUNTIME_RECONCILIATION_MODELS:
        payload = _load_json(SCHEMA_DIR / f"{artifact_type}.schema.json")
        assert payload["properties"]["schema_version"]["const"] == "1.0.0"


def test_singleton_no_resident_permits_new_launch() -> None:
    _, _, bundle = _load_fixture("singleton_no_resident_permit.json")
    assert bundle.result.disposition == "permit_new_launch"
    assert bundle.duplicate_detected is None
    assert bundle.launch_refused is None


def test_singleton_existing_resident_attaches() -> None:
    _, _, bundle = _load_fixture("singleton_existing_attach.json")
    assert bundle.result.disposition == "attach_to_existing_runtime"
    assert bundle.result.resident_count == 1


def test_bounded_multiplicity_below_max_is_allowed() -> None:
    _, _, bundle = _load_fixture("bounded_below_max_permit.json")
    assert bundle.result.disposition == "permit_declared_multiplicity"
    assert bundle.result.resident_count == 1


def test_bounded_multiplicity_exceeding_max_is_refused() -> None:
    _, _, bundle = _load_fixture("bounded_exceeds_max_refuse.json")
    assert bundle.result.disposition == "refuse_duplicate_launch"
    assert bundle.launch_refused is not None


def test_wrapper_child_pair_is_one_logical_resident() -> None:
    _, _, bundle = _load_fixture("wrapper_child_pair_attach.json")
    assert bundle.result.disposition == "attach_to_existing_runtime"
    assert bundle.result.resident_count == 1
    assert bundle.result.equivalent_residents[0].topology_class == "wrapper_child_runtime_pair"


def test_ambiguous_powershell_runtime_is_blocked() -> None:
    _, _, bundle = _load_fixture("ambiguous_powershell_block.json")
    assert bundle.result.disposition == "ambiguous_runtime_blocked"
    assert "host_process_ambiguous" in bundle.result.ambiguity_conditions
    assert bundle.launch_refused is not None


def test_undeclared_duplicate_emits_duplicate_artifact() -> None:
    _, _, bundle = _load_fixture("undeclared_duplicate_detected.json")
    assert bundle.result.disposition == "refuse_duplicate_launch"
    assert bundle.duplicate_detected is not None
    assert bundle.launch_refused is not None


def test_reconcile_from_paths_matches_direct_generation(tmp_path: Path) -> None:
    snapshot, request, _ = _load_fixture("singleton_existing_attach.json")
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    fixed_now = datetime(2026, 4, 4, 19, 0, 6, tzinfo=UTC)
    direct = reconcile_runtime_request(
        request=request,
        snapshot=snapshot,
        declarations=build_default_service_declarations(),
        evaluated_at_utc=fixed_now,
    )
    by_path = reconcile_runtime_request_from_paths(
        request=request,
        snapshot_path=snapshot_path,
        declarations=build_default_service_declarations(),
        evaluated_at_utc=fixed_now,
    )
    assert direct.model_dump(mode="json") == by_path.model_dump(mode="json")


def test_request_requires_declared_service_target() -> None:
    payload = _load_json(FIXTURE_DIR / "singleton_no_resident_permit.json")["request"]
    payload["declared_service_target"] = "not_a_service"
    with pytest.raises(ValidationError):
        RuntimeReconciliationRequest.model_validate(payload)
