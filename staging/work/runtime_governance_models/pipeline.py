"""Deterministic staging helpers for runtime governance scenarios."""

from __future__ import annotations

from copy import deepcopy

from staging.work.runtime_governance_models.models import RuntimeGovernanceBundle


def load_runtime_governance_bundle(payload: dict) -> RuntimeGovernanceBundle:
    return RuntimeGovernanceBundle.model_validate(payload)


def classify_health_loop_transition(
    *,
    base_bundle: RuntimeGovernanceBundle,
    authoritative_update: dict,
    enrichment_update: dict | None = None,
) -> RuntimeGovernanceBundle:
    data = deepcopy(base_bundle.model_dump(mode="json"))
    data["health_authoritative_snapshot"].update(authoritative_update)
    if enrichment_update is not None:
        if data.get("health_enrichment_snapshot") is None:
            raise ValueError("cannot update absent health enrichment snapshot")
        data["health_enrichment_snapshot"].update(enrichment_update)
    return RuntimeGovernanceBundle.model_validate(data)

def classify_bridge_transition(
    *,
    base_bundle: RuntimeGovernanceBundle,
    pulse_update: dict,
) -> RuntimeGovernanceBundle:
    data = deepcopy(base_bundle.model_dump(mode="json"))
    if data.get("bridge_pulse_classification") is None:
        raise ValueError("cannot update absent bridge pulse classification")
    data["bridge_pulse_classification"].update(pulse_update)
    return RuntimeGovernanceBundle.model_validate(data)
