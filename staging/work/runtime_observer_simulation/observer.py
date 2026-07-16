"""Deterministic observer simulation for runtime multiplicity classification."""

from __future__ import annotations

from datetime import UTC, datetime

from staging.work.runtime_governance_models.models import (
    BridgePulseClassification,
    HealthAuthoritativeSnapshot,
    HealthEnrichmentSnapshot,
    RuntimeGovernanceBundle,
    RuntimeLaunchNotice,
    RuntimeMultiplicityNoncompliance,
    RuntimeMultiplicityValidation,
    RuntimeProcessIdentity,
    RuntimeServiceDeclaration,
)
from staging.work.runtime_observer_simulation.models import (
    BridgeObserverContext,
    HealthObserverContext,
    ObservedProcess,
    RuntimeObserverEmission,
    RuntimeObserverSnapshot,
    RUNTIME_OBSERVER_SCHEMA_VERSION,
)


def simulate_runtime_observer(snapshot: RuntimeObserverSnapshot) -> RuntimeObserverEmission:
    bundles: list[RuntimeGovernanceBundle] = []
    health_processes = [proc for proc in snapshot.processes if _is_health_loop(proc)]
    bridge_processes = [proc for proc in snapshot.processes if _is_bridge_overseer(proc)]

    if snapshot.health_context is not None:
        bundles.append(_build_health_bundle(snapshot, health_processes, snapshot.health_context))
    if snapshot.bridge_context is not None:
        bundles.append(_build_bridge_bundle(snapshot, bridge_processes, snapshot.bridge_context))

    return RuntimeObserverEmission(
        schema_name="runtime.observer.emission",
        schema_version=RUNTIME_OBSERVER_SCHEMA_VERSION,
        snapshot_id=snapshot.snapshot_id,
        corr_id=snapshot.corr_id,
        captured_at_utc=snapshot.captured_at_utc,
        emitted_at_utc=datetime.now(UTC),
        governance_bundles=bundles,
        notes="Observer simulation emitted runtime governance bundles from a staged process snapshot.",
    )


def _build_health_bundle(
    snapshot: RuntimeObserverSnapshot,
    processes: list[ObservedProcess],
    context: HealthObserverContext,
) -> RuntimeGovernanceBundle:
    if not processes:
        raise ValueError("health_context requires at least one station_health_loop process in the snapshot")

    declaration = RuntimeServiceDeclaration(
        schema_name="runtime.service_declaration",
        schema_version="1.0.0",
        artifact_id="station_health_loop.declaration",
        service_name="station_health_loop",
        topology_class="single_process",
        multiplicity_posture="single_instance_only",
        authoritative_runtime_role="authoritative_writer",
        expected_runtime_roles=["authoritative_writer", "health_enrichment_sampler"],
        launch_notice_required=True,
    )
    identities = [_identity_from_observed(proc) for proc in processes]
    validation_outcome = "topology_valid" if len(processes) == 1 else "duplicate_concerning"
    posture = "none" if len(processes) == 1 and context.freshness_state == "fresh" else "warning_posture"
    if len(processes) > 1:
        posture = "operator_review_required"

    validation = RuntimeMultiplicityValidation(
        schema_name="runtime.multiplicity.validation",
        schema_version="1.0.0",
        artifact_id=f"{snapshot.snapshot_id}.station_health.validation",
        corr_id=snapshot.corr_id,
        timestamp_utc=snapshot.captured_at_utc,
        service_name="station_health_loop",
        declaration_ref=declaration.artifact_id,
        observed_process_identities=identities,
        validation_outcome=validation_outcome,
        posture_consequence=posture,
        classification_notes=(
            "Single authoritative writer observed."
            if len(processes) == 1
            else "Observed duplicate health-loop writer shape conflicts with single_instance_only posture."
        ),
    )

    launch_notice = None
    noncompliance = None
    if len(processes) > 1:
        launch_notice = RuntimeLaunchNotice(
            schema_name="runtime.launch_notice",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.station_health.launch_notice",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            service_name="station_health_loop",
            declared_by_surface="runtime_observer_simulation",
            topology_class="single_process",
            multiplicity_posture="single_instance_only",
            launch_reason="Observed duplicate health-loop launch attempt from captured process snapshot.",
            parent_process_identity=identities[0],
            child_or_additional_process_identity=identities[1],
            intended_runtime_role="duplicate_peer",
            steady_state_or_temporary="temporary",
            expected_lifecycle="Secondary writer must remain non-authoritative.",
            reconciliation_condition="Duplicate writer classified; single authoritative writer semantics preserved.",
            launch_notice_status=context.launch_notice_status or "retroactive_classification_only",
        )
        noncompliance = RuntimeMultiplicityNoncompliance(
            schema_name="runtime.multiplicity.noncompliance",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.station_health.noncompliance",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            service_name="station_health_loop",
            declaration_ref=declaration.artifact_id,
            validation_ref=validation.artifact_id,
            noncompliance_type="duplicate_writer_attempt",
            severity="high",
            required_operator_visibility="review_required",
            notes="Health-loop duplicate writer attempt is classified and not normalized.",
        )

    auth = HealthAuthoritativeSnapshot(
        schema_name="runtime.health.authoritative_snapshot",
        schema_version="1.0.0",
        artifact_id=f"{snapshot.snapshot_id}.station_health.auth",
        corr_id=snapshot.corr_id,
        timestamp_utc=snapshot.captured_at_utc,
        declared_interval_seconds=context.declared_interval_seconds,
        observed_loop_elapsed_ms=context.observed_loop_elapsed_ms,
        observed_sleep_ms=context.observed_sleep_ms,
        cadence_compliant=_health_cadence_compliant(context),
        health_state=context.health_state,
        freshness_state=context.freshness_state,
        stale_reason=context.stale_reason,
        cpu_pct=context.cpu_pct,
        ram_pct=context.ram_pct,
        memory_pressure_tier=context.memory_pressure_tier,
        expiry_sweep_invoked=context.expiry_sweep_invoked,
    )

    enrich = None
    if context.enrichment_interval_seconds is not None and context.enrichment_sample_age_ms is not None:
        enrich = HealthEnrichmentSnapshot(
            schema_name="runtime.health.enrichment_snapshot",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.station_health.enrichment",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            authoritative_snapshot_ref=auth.artifact_id,
            enrichment_interval_seconds=context.enrichment_interval_seconds,
            enrichment_sample_age_ms=context.enrichment_sample_age_ms,
            top_processes=context.top_processes,
            entropy_sources=context.entropy_sources,
            gpu_metrics_present=context.gpu_metrics_present,
            notes="Observer simulation preserved fast-path vs enrichment-path distinction.",
        )

    return RuntimeGovernanceBundle(
        scenario_name=f"{snapshot.snapshot_id}.station_health",
        description="Observer-simulated station health runtime classification.",
        service_declaration=declaration,
        runtime_launch_notice=launch_notice,
        runtime_multiplicity_validation=validation,
        runtime_multiplicity_noncompliance=noncompliance,
        health_authoritative_snapshot=auth,
        health_enrichment_snapshot=enrich,
    )


def _build_bridge_bundle(
    snapshot: RuntimeObserverSnapshot,
    processes: list[ObservedProcess],
    context: BridgeObserverContext,
) -> RuntimeGovernanceBundle:
    if not processes:
        raise ValueError("bridge_context requires at least one bridge_overseer process in the snapshot")

    declaration = RuntimeServiceDeclaration(
        schema_name="runtime.service_declaration",
        schema_version="1.0.0",
        artifact_id="bridge_overseer.declaration",
        service_name="bridge_overseer",
        topology_class="wrapper_child_runtime_pair",
        multiplicity_posture="wrapper_child_expected",
        authoritative_runtime_role="bridge_cycle_owner",
        expected_runtime_roles=["launcher_wrapper", "bridge_cycle_owner"],
        launch_notice_required=True,
    )
    identities = [_identity_from_observed(proc) for proc in processes]
    pair = _find_wrapper_child_pair(processes)
    if len(processes) == 2 and pair is not None:
        if context.launch_notice_status in ("prelaunch_declared", "launch_adjacent_declared"):
            validation_outcome = "multiplicity_declared_and_compliant"
            notice_refs = [f"{snapshot.snapshot_id}.bridge.launch_notice"]
            posture = "none"
        else:
            validation_outcome = "multiplicity_declared_but_noncompliant"
            notice_refs = []
            posture = "warning_posture"
    else:
        validation_outcome = "duplicate_concerning"
        notice_refs = []
        posture = "operator_review_required"

    validation = RuntimeMultiplicityValidation(
        schema_name="runtime.multiplicity.validation",
        schema_version="1.0.0",
        artifact_id=f"{snapshot.snapshot_id}.bridge.validation",
        corr_id=snapshot.corr_id,
        timestamp_utc=snapshot.captured_at_utc,
        service_name="bridge_overseer",
        declaration_ref=declaration.artifact_id,
        observed_process_identities=identities,
        required_launch_notice_refs=notice_refs,
        validation_outcome=validation_outcome,
        posture_consequence=posture,
        classification_notes=_bridge_validation_notes(validation_outcome),
    )

    launch_notice = None
    if pair is not None:
        parent_identity, child_identity = pair
        launch_notice = RuntimeLaunchNotice(
            schema_name="runtime.launch_notice",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.bridge.launch_notice",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            service_name="bridge_overseer",
            declared_by_surface="runtime_observer_simulation",
            topology_class="wrapper_child_runtime_pair",
            multiplicity_posture="wrapper_child_expected",
            launch_reason="Observed wrapper-child overseer topology from captured process snapshot.",
            parent_process_identity=parent_identity,
            child_or_additional_process_identity=child_identity,
            intended_runtime_role="bridge_cycle_owner",
            steady_state_or_temporary="steady_state",
            expected_lifecycle="Wrapper-child pair remains until governed shutdown.",
            reconciliation_condition="One authoritative cycle owner only; duplicate peer overseers remain invalid.",
            launch_notice_status=context.launch_notice_status or "retroactive_classification_only",
        )

    noncompliance = None
    if validation_outcome == "duplicate_concerning":
        noncompliance = RuntimeMultiplicityNoncompliance(
            schema_name="runtime.multiplicity.noncompliance",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.bridge.noncompliance",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            service_name="bridge_overseer",
            declaration_ref=declaration.artifact_id,
            validation_ref=validation.artifact_id,
            noncompliance_type="duplicate_overseer_attempt",
            severity="high",
            required_operator_visibility="review_required",
            notes="Duplicate overseer runtime shape is classified and not normalized into the declared wrapper-child pair.",
        )
    elif validation_outcome == "multiplicity_declared_but_noncompliant":
        noncompliance = RuntimeMultiplicityNoncompliance(
            schema_name="runtime.multiplicity.noncompliance",
            schema_version="1.0.0",
            artifact_id=f"{snapshot.snapshot_id}.bridge.noncompliance",
            corr_id=snapshot.corr_id,
            timestamp_utc=snapshot.captured_at_utc,
            service_name="bridge_overseer",
            declaration_ref=declaration.artifact_id,
            validation_ref=validation.artifact_id,
            noncompliance_type="missing_launch_notice",
            severity="moderate",
            required_operator_visibility="warn",
            notes="Wrapper-child topology was foreseeable but required launch notice was missing.",
        )

    pulse_class = _bridge_pulse_class(context)
    idle_reason = _bridge_idle_reason(context, pulse_class)
    pulse = BridgePulseClassification(
        schema_name="runtime.bridge.pulse_classification",
        schema_version="1.0.0",
        artifact_id=f"{snapshot.snapshot_id}.bridge.pulse",
        corr_id=snapshot.corr_id,
        timestamp_utc=snapshot.captured_at_utc,
        service_name="bridge_overseer",
        pulse_class=pulse_class,
        work_state=context.work_state,
        idle_reason=idle_reason,
        idle_mode_active=(pulse_class == "idle"),
        backoff_active=context.backoff_active,
        backoff_seconds=context.backoff_seconds,
        objectives_count=context.objectives_count,
        planned_tasks_count=context.planned_tasks_count,
        dispatched_count=context.dispatched_count,
        truthful_visibility_preserved=context.truthful_visibility_preserved,
        notes=_bridge_pulse_notes(pulse_class, idle_reason),
    )

    return RuntimeGovernanceBundle(
        scenario_name=f"{snapshot.snapshot_id}.bridge_overseer",
        description="Observer-simulated bridge overseer runtime classification.",
        service_declaration=declaration,
        runtime_launch_notice=launch_notice,
        runtime_multiplicity_validation=validation,
        runtime_multiplicity_noncompliance=noncompliance,
        bridge_pulse_classification=pulse,
    )


def _is_health_loop(proc: ObservedProcess) -> bool:
    return "station_health_loop.ps1" in proc.command_line.lower()


def _is_bridge_overseer(proc: ObservedProcess) -> bool:
    return "calyx.cbo.bridge_overseer" in proc.command_line.lower()


def _identity_from_observed(proc: ObservedProcess) -> RuntimeProcessIdentity:
    return RuntimeProcessIdentity(
        pid=proc.pid,
        executable_path=proc.executable_path,
        command_line=proc.command_line,
        started_at_utc=proc.started_at_utc,
    )


def _find_wrapper_child_pair(processes: list[ObservedProcess]) -> tuple[RuntimeProcessIdentity, RuntimeProcessIdentity] | None:
    process_by_pid = {proc.pid: proc for proc in processes}
    for child in processes:
        if child.parent_pid is None:
            continue
        parent = process_by_pid.get(child.parent_pid)
        if parent is None:
            continue
        return _identity_from_observed(parent), _identity_from_observed(child)
    return None


def _health_cadence_compliant(context: HealthObserverContext) -> bool:
    total_ms = context.observed_loop_elapsed_ms + context.observed_sleep_ms
    interval_ms = int(round(context.declared_interval_seconds * 1000))
    return abs(total_ms - interval_ms) <= max(100, int(interval_ms * 0.15))


def _bridge_pulse_class(context: BridgeObserverContext) -> str:
    if context.objectives_count > 0 or context.planned_tasks_count > 0 or context.dispatched_count > 0:
        return "active"
    return "idle"


def _bridge_idle_reason(context: BridgeObserverContext, pulse_class: str) -> str:
    if pulse_class == "active":
        return "none"
    if context.idle_reason is not None:
        return context.idle_reason
    if context.work_state == "objectives_absent":
        return "no_objectives_file"
    if context.work_state == "objectives_empty":
        return "empty_objectives_file"
    return "no_dispatchable_work"


def _bridge_validation_notes(outcome: str) -> str:
    if outcome == "multiplicity_declared_and_compliant":
        return "Observed wrapper-child overseer pair matches the declared topology and launch notice posture."
    if outcome == "multiplicity_declared_but_noncompliant":
        return "Observed wrapper-child overseer pair matches declared topology but lacks compliant launch notice attribution."
    return "Observed bridge runtime shape exceeds the declared overseer topology or creates duplicate peer residency."


def _bridge_pulse_notes(pulse_class: str, idle_reason: str) -> str:
    if pulse_class == "active":
        return "Observer classified the bridge pulse as active because work counts were non-zero."
    return f"Observer classified the bridge pulse as idle because {idle_reason} preserved truthful idle visibility."
