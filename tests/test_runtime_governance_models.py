from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.runtime_governance_models.models import (
    PRIMARY_RUNTIME_GOVERNANCE_MODELS,
    BridgePulseClassification,
    HealthAuthoritativeSnapshot,
    HealthEnrichmentSnapshot,
    RUNTIME_GOVERNANCE_SCHEMA_VERSION,
    RuntimeGovernanceBundle,
    RuntimeMultiplicityValidation,
    RuntimeServiceDeclaration,
)
from staging.work.runtime_governance_models.pipeline import (
    classify_bridge_transition,
    classify_health_loop_transition,
)


FIXTURE_DIR = Path("staging/work/runtime_governance_models/fixtures")
SCHEMA_DIR = Path("staging/work/runtime_governance_models/schemas")
FIXTURE_FILES = [
    "health_single_instance_compliant.json",
    "health_duplicate_launch_attempt.json",
    "health_stale_unknown_state.json",
    "health_cadence_correctness_validation.json",
    "health_enrichment_decoupling_behavior.json",
    "bridge_active_work_present.json",
    "bridge_empty_objectives_idle_mode.json",
    "bridge_duplicate_overseer_launch.json",
    "bridge_idle_pulse_classification_with_backoff.json",
    "bridge_idle_to_active_transition.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_bundle(name: str) -> RuntimeGovernanceBundle:
    return RuntimeGovernanceBundle.model_validate(_load_json(FIXTURE_DIR / name))


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_bundle_validates(fixture_name: str) -> None:
    bundle = _load_bundle(fixture_name)
    assert bundle.scenario_name
    assert bundle.service_declaration.schema_version == RUNTIME_GOVERNANCE_SCHEMA_VERSION


def test_schema_exports_exist_and_are_versioned() -> None:
    for artifact_type in PRIMARY_RUNTIME_GOVERNANCE_MODELS:
        payload = _load_json(SCHEMA_DIR / f"{artifact_type}.schema.json")
        assert payload["properties"]["schema_version"]["const"] == RUNTIME_GOVERNANCE_SCHEMA_VERSION


def test_service_declaration_requires_authoritative_role_in_expected_roles() -> None:
    payload = _load_json(FIXTURE_DIR / "health_single_instance_compliant.json")["service_declaration"]
    payload["expected_runtime_roles"] = ["health_enrichment_sampler"]
    with pytest.raises(ValidationError):
        RuntimeServiceDeclaration.model_validate(payload)


def test_health_authoritative_snapshot_requires_stale_unknown_pairing() -> None:
    payload = _load_json(FIXTURE_DIR / "health_stale_unknown_state.json")["health_authoritative_snapshot"]
    payload["freshness_state"] = "fresh"
    with pytest.raises(ValidationError):
        HealthAuthoritativeSnapshot.model_validate(payload)


def test_health_enrichment_snapshot_requires_authoritative_reference() -> None:
    payload = _load_json(FIXTURE_DIR / "health_enrichment_decoupling_behavior.json")
    del payload["health_authoritative_snapshot"]
    with pytest.raises(ValidationError):
        RuntimeGovernanceBundle.model_validate(payload)


def test_single_instance_health_loop_is_compliant() -> None:
    bundle = _load_bundle("health_single_instance_compliant.json")
    assert bundle.service_declaration.service_name == "station_health_loop"
    assert bundle.runtime_multiplicity_validation.validation_outcome == "topology_valid"
    assert bundle.health_authoritative_snapshot.cadence_compliant is True
    assert bundle.health_enrichment_snapshot.sampling_lane == "enrichment_path"


def test_duplicate_health_launch_is_classified_not_normalized() -> None:
    bundle = _load_bundle("health_duplicate_launch_attempt.json")
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "duplicate_writer_attempt"
    assert bundle.runtime_launch_notice is not None


def test_stale_unknown_state_is_explicit() -> None:
    bundle = _load_bundle("health_stale_unknown_state.json")
    auth = bundle.health_authoritative_snapshot
    assert auth.health_state == "unknown"
    assert auth.freshness_state == "stale"
    assert auth.stale_reason is not None


def test_cadence_correctness_scenario_exposes_noncompliance_without_topology_failure() -> None:
    bundle = _load_bundle("health_cadence_correctness_validation.json")
    auth = bundle.health_authoritative_snapshot
    assert auth.cadence_compliant is False
    assert bundle.runtime_multiplicity_validation.validation_outcome == "topology_valid"
    assert bundle.runtime_multiplicity_validation.posture_consequence == "warning_posture"


def test_enrichment_decoupling_behavior_is_schema_visible() -> None:
    bundle = _load_bundle("health_enrichment_decoupling_behavior.json")
    auth = bundle.health_authoritative_snapshot
    enrich = bundle.health_enrichment_snapshot
    assert auth.sampling_lane == "fast_path"
    assert enrich.sampling_lane == "enrichment_path"
    assert enrich.enrichment_interval_seconds > auth.declared_interval_seconds


def test_bridge_active_work_present_classifies_as_active() -> None:
    bundle = _load_bundle("bridge_active_work_present.json")
    pulse = bundle.bridge_pulse_classification
    assert pulse.pulse_class == "active"
    assert pulse.idle_mode_active is False
    assert pulse.objectives_count > 0
    assert bundle.runtime_multiplicity_validation.validation_outcome == "multiplicity_declared_and_compliant"


def test_bridge_empty_objectives_enters_visible_idle_mode() -> None:
    bundle = _load_bundle("bridge_empty_objectives_idle_mode.json")
    pulse = bundle.bridge_pulse_classification
    assert pulse.pulse_class == "idle"
    assert pulse.idle_mode_active is True
    assert pulse.idle_reason == "no_objectives_file"
    assert pulse.truthful_visibility_preserved is True


def test_duplicate_bridge_overseer_launch_is_classified() -> None:
    bundle = _load_bundle("bridge_duplicate_overseer_launch.json")
    assert bundle.runtime_multiplicity_validation.validation_outcome == "duplicate_concerning"
    assert bundle.runtime_multiplicity_noncompliance is not None
    assert bundle.runtime_multiplicity_noncompliance.noncompliance_type == "duplicate_overseer_attempt"


def test_bridge_idle_backoff_remains_visible_and_bounded() -> None:
    bundle = _load_bundle("bridge_idle_pulse_classification_with_backoff.json")
    pulse = bundle.bridge_pulse_classification
    assert pulse.pulse_class == "idle"
    assert pulse.backoff_active is True
    assert pulse.backoff_seconds > 0
    assert pulse.truthful_visibility_preserved is True


def test_transition_from_idle_to_active_reclassifies_cleanly() -> None:
    idle_bundle = _load_bundle("bridge_empty_objectives_idle_mode.json")
    transitioned = classify_bridge_transition(
        base_bundle=idle_bundle,
        pulse_update={
            "artifact_id": "bridge.transition.runtime",
            "timestamp_utc": "2026-03-31T19:40:00Z",
            "pulse_class": "active",
            "work_state": "objectives_present",
            "idle_reason": "none",
            "idle_mode_active": False,
            "backoff_active": False,
            "backoff_seconds": 0,
            "objectives_count": 1,
            "planned_tasks_count": 1,
            "dispatched_count": 1,
            "notes": "Objectives appeared; idle mode collapses immediately.",
        },
    )
    assert transitioned.bridge_pulse_classification.pulse_class == "active"
    assert transitioned.bridge_pulse_classification.idle_mode_active is False


def test_health_transition_helper_preserves_bundle_integrity() -> None:
    bundle = _load_bundle("health_single_instance_compliant.json")
    updated = classify_health_loop_transition(
        base_bundle=bundle,
        authoritative_update={
            "artifact_id": "health.transition.auth",
            "timestamp_utc": "2026-03-31T19:41:00Z",
            "observed_loop_elapsed_ms": 210,
            "observed_sleep_ms": 790,
            "cadence_compliant": True,
            "cpu_pct": 39,
            "ram_pct": 43,
        },
        enrichment_update={
            "artifact_id": "health.transition.enrich",
            "timestamp_utc": "2026-03-31T19:41:10Z",
            "authoritative_snapshot_ref": "health.transition.auth",
            "enrichment_sample_age_ms": 250,
            "top_processes": ["Code#27864", "powershell#35932"],
            "entropy_sources": ["Code#27864"],
            "notes": "Updated enrichment after fast-path sample.",
        },
    )
    assert updated.health_authoritative_snapshot.artifact_id == "health.transition.auth"
    assert updated.health_enrichment_snapshot.authoritative_snapshot_ref == "health.transition.auth"


def test_runtime_validation_requires_launch_notice_for_declared_compliance() -> None:
    payload = _load_json(FIXTURE_DIR / "bridge_active_work_present.json")["runtime_multiplicity_validation"]
    payload["required_launch_notice_refs"] = []
    with pytest.raises(ValidationError):
        RuntimeMultiplicityValidation.model_validate(payload)


def test_bridge_active_classification_cannot_claim_idle_mode() -> None:
    payload = _load_json(FIXTURE_DIR / "bridge_active_work_present.json")["bridge_pulse_classification"]
    payload["idle_mode_active"] = True
    with pytest.raises(ValidationError):
        BridgePulseClassification.model_validate(payload)
