"""Deterministic mapper from raw capture input to canonical observer snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
import re

from staging.work.runtime_capture_adapter.models import (
    CapturedBridgePulse,
    CapturedProcessRow,
    CapturedStationHealth,
    RuntimeCaptureAmbiguityMarker,
    RuntimeCaptureClassificationResult,
    RuntimeCaptureIngestionTrace,
    RuntimeCaptureInput,
    RuntimeCaptureMappingValidation,
    RuntimeCaptureNormalizationResult,
)
from staging.work.runtime_observer_simulation.models import (
    BridgeObserverContext,
    HealthObserverContext,
    ObservedProcess,
    RuntimeObserverSnapshot,
)
from staging.work.runtime_observer_simulation.observer import simulate_runtime_observer


def normalize_capture_to_snapshot(capture: RuntimeCaptureInput) -> RuntimeCaptureNormalizationResult:
    defaulted_fields: list[str] = []
    dropped_fields: list[str] = []
    ambiguity_markers: list[RuntimeCaptureAmbiguityMarker] = []
    observed_processes: list[ObservedProcess] = []

    for row in capture.process_rows:
        if not row.command_line:
            ambiguity_markers.append(
                _marker(capture, row, "capture_layer", "missing_command_line", f"Process PID {row.pid} missing command line; service matching may be incomplete.")
            )
            dropped_fields.append(f"process_rows[{row.pid}].command_line")
        if not row.executable_path:
            ambiguity_markers.append(
                _marker(capture, row, "capture_layer", "missing_executable_path", f"Process PID {row.pid} missing executable path; path fidelity is incomplete.")
            )
            defaulted_fields.append(f"process_rows[{row.pid}].executable_path")
        observed_processes.append(
            ObservedProcess(
                pid=row.pid,
                parent_pid=row.parent_pid,
                executable_path=row.executable_path or f"unknown://pid/{row.pid}",
                command_line=row.command_line or f"unknown-command://pid/{row.pid}",
                started_at_utc=row.started_at_utc,
            )
        )

    health_process_present = any(_is_health_loop(row) for row in capture.process_rows)
    bridge_process_present = any(_is_bridge_overseer(row) for row in capture.process_rows)

    health_context = _map_health_context(capture, ambiguity_markers, defaulted_fields) if health_process_present else None
    bridge_context = _map_bridge_context(capture, ambiguity_markers, defaulted_fields) if bridge_process_present else None

    if capture.station_health is not None and not health_process_present:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "station_health_loop",
                "no_matching_service_processes",
                "Station health artifact was captured but no matching station_health_loop process row was present.",
            )
        )
    if capture.bridge_pulse is not None and not bridge_process_present:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "bridge_overseer",
                "no_matching_service_processes",
                "Bridge pulse artifact was captured but no matching bridge_overseer process row was present.",
            )
        )

    snapshot = RuntimeObserverSnapshot(
        schema_name="runtime.observer.process_snapshot",
        schema_version="1.0.0",
        snapshot_id=capture.capture_id,
        corr_id=capture.corr_id,
        captured_at_utc=capture.captured_at_utc,
        observer_mode="staging_only",
        processes=observed_processes,
        health_context=health_context,
        bridge_context=bridge_context,
        capture_notes=capture.capture_notes,
    )

    trace = RuntimeCaptureIngestionTrace(
        schema_name="runtime.capture.ingestion_trace",
        schema_version="1.0.0",
        trace_id=f"{capture.capture_id}.trace",
        corr_id=capture.corr_id,
        capture_id=capture.capture_id,
        timestamp_utc=datetime.now(UTC),
        source_process_count=len(capture.process_rows),
        mapped_process_count=len(observed_processes),
        defaulted_fields=defaulted_fields,
        dropped_fields=dropped_fields,
        notes="Deterministic raw capture to canonical observer snapshot mapping.",
    )

    return RuntimeCaptureNormalizationResult(
        schema_name="runtime.capture.normalization_result",
        schema_version="1.0.0",
        capture_id=capture.capture_id,
        corr_id=capture.corr_id,
        normalized_at_utc=datetime.now(UTC),
        canonical_snapshot=snapshot,
        ingestion_trace=trace,
        ambiguity_markers=ambiguity_markers,
    )


def classify_capture(capture: RuntimeCaptureInput) -> RuntimeCaptureClassificationResult:
    normalization = normalize_capture_to_snapshot(capture)
    emission = simulate_runtime_observer(normalization.canonical_snapshot)
    validation = RuntimeCaptureMappingValidation(
        schema_name="runtime.capture.mapping_validation",
        schema_version="1.0.0",
        validation_id=f"{capture.capture_id}.validation",
        corr_id=capture.corr_id,
        capture_id=capture.capture_id,
        timestamp_utc=datetime.now(UTC),
        snapshot_schema_valid=True,
        observer_emission_valid=True,
        no_mutation_performed=True,
        notes="Capture normalized and classified without mutating live runtime state.",
    )
    return RuntimeCaptureClassificationResult(
        schema_name="runtime.capture.classification_result",
        schema_version="1.0.0",
        capture_id=capture.capture_id,
        corr_id=capture.corr_id,
        classified_at_utc=datetime.now(UTC),
        normalization=normalization,
        observer_emission=emission,
        mapping_validation=validation,
    )


def _map_health_context(
    capture: RuntimeCaptureInput,
    ambiguity_markers: list[RuntimeCaptureAmbiguityMarker],
    defaulted_fields: list[str],
) -> HealthObserverContext | None:
    health = capture.station_health
    if health is None:
        return None

    declared_interval = health.interval_s or 1.0
    if health.interval_s is None:
        defaulted_fields.append("station_health.interval_s")

    loop_elapsed_ms = health.loop_elapsed_ms
    loop_sleep_ms = health.loop_sleep_ms
    launch_notice_status = "launch_adjacent_declared"
    if loop_elapsed_ms is None or loop_sleep_ms is None:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "station_health_loop",
                "health_cadence_unresolved",
                "Live capture did not provide loop elapsed/sleep timing; cadence fields were derived from declared interval for snapshot compatibility.",
            )
        )
        loop_elapsed_ms = 0
        loop_sleep_ms = int(round(declared_interval * 1000))
        defaulted_fields.extend(["station_health.loop_elapsed_ms", "station_health.loop_sleep_ms"])
        launch_notice_status = "retroactive_classification_only"

    expiry_sweep_invoked = health.expiry_sweep_invoked
    if expiry_sweep_invoked is None:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "station_health_loop",
                "health_expiry_sweep_unresolved",
                "Live capture did not provide expiry sweep evidence; set false without claiming invocation.",
            )
        )
        expiry_sweep_invoked = False
        defaulted_fields.append("station_health.expiry_sweep_invoked")

    enrichment_interval_seconds = 10.0 if (health.top_processes or health.entropy_sources) else None
    enrichment_age_ms = None
    if enrichment_interval_seconds is not None:
        enrichment_age_ms = max(0, int((capture.captured_at_utc - health.captured_at_utc).total_seconds() * 1000))

    freshness_state = "fresh"
    if health.truth_state == "stale":
        freshness_state = "stale"
    elif health.truth_state == "unknown" or health.health == "unknown":
        freshness_state = "unknown"

    return HealthObserverContext(
        declared_interval_seconds=declared_interval,
        observed_loop_elapsed_ms=loop_elapsed_ms,
        observed_sleep_ms=loop_sleep_ms,
        health_state=health.health,
        freshness_state=freshness_state,
        stale_reason=health.stale_reason,
        cpu_pct=health.cpu_pct,
        ram_pct=health.ram_pct,
        memory_pressure_tier=health.memory_pressure_tier,
        expiry_sweep_invoked=expiry_sweep_invoked,
        enrichment_interval_seconds=enrichment_interval_seconds,
        enrichment_sample_age_ms=enrichment_age_ms,
        top_processes=health.top_processes,
        entropy_sources=health.entropy_sources,
        gpu_metrics_present=health.gpu_metrics_present,
        launch_notice_status=launch_notice_status,
    )


def _map_bridge_context(
    capture: RuntimeCaptureInput,
    ambiguity_markers: list[RuntimeCaptureAmbiguityMarker],
    defaulted_fields: list[str],
) -> BridgeObserverContext | None:
    pulse = capture.bridge_pulse
    if pulse is None:
        return None

    parsed = _parse_bridge_details(pulse.details)
    objectives_count = parsed["objectives_count"]
    planned_tasks_count = parsed["planned_tasks_count"]
    dispatched_count = parsed["dispatched_count"]

    work_state = pulse.work_state_hint
    if work_state is None:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "bridge_overseer",
                "bridge_work_state_unresolved",
                "Bridge work_state hint absent; mapped deterministically from pulse counts.",
            )
        )
        if objectives_count > 0:
            work_state = "objectives_present"
        else:
            work_state = "objectives_empty"
        defaulted_fields.append("bridge_pulse.work_state_hint")

    idle_reason = pulse.idle_reason_hint
    if idle_reason is None and objectives_count == 0 and planned_tasks_count == 0 and dispatched_count == 0:
        ambiguity_markers.append(
            _simple_marker(
                capture,
                "bridge_overseer",
                "bridge_idle_reason_unresolved",
                "Bridge idle reason hint absent; mapped deterministically from work_state.",
            )
        )
        idle_reason = "no_objectives_file" if work_state == "objectives_absent" else "empty_objectives_file"
        defaulted_fields.append("bridge_pulse.idle_reason_hint")

    launch_notice_status = pulse.launch_notice_status_hint
    return BridgeObserverContext(
        objectives_count=objectives_count,
        planned_tasks_count=planned_tasks_count,
        dispatched_count=dispatched_count,
        work_state=work_state,
        idle_reason=idle_reason,
        backoff_active=False,
        backoff_seconds=0,
        truthful_visibility_preserved=True,
        launch_notice_status=launch_notice_status,
    )


def _parse_bridge_details(details: str) -> dict[str, int]:
    def _extract(label: str) -> int:
        match = re.search(rf"{label}=(\d+)", details)
        return int(match.group(1)) if match else 0

    return {
        "objectives_count": _extract("objectives"),
        "planned_tasks_count": _extract("tasks"),
        "dispatched_count": _extract("dispatched"),
    }


def _is_health_loop(row: CapturedProcessRow) -> bool:
    return "station_health_loop.ps1" in (row.command_line or "").lower()


def _is_bridge_overseer(row: CapturedProcessRow) -> bool:
    return "calyx.cbo.bridge_overseer" in (row.command_line or "").lower()


def _marker(
    capture: RuntimeCaptureInput,
    row: CapturedProcessRow,
    service_name: str,
    ambiguity_type: str,
    notes: str,
) -> RuntimeCaptureAmbiguityMarker:
    return RuntimeCaptureAmbiguityMarker(
        schema_name="runtime.capture.ambiguity_marker",
        schema_version="1.0.0",
        marker_id=f"{capture.capture_id}.marker.{ambiguity_type}.{row.pid}",
        corr_id=capture.corr_id,
        capture_id=capture.capture_id,
        service_name=service_name,
        ambiguity_type=ambiguity_type,
        notes=notes,
    )


def _simple_marker(
    capture: RuntimeCaptureInput,
    service_name: str,
    ambiguity_type: str,
    notes: str,
) -> RuntimeCaptureAmbiguityMarker:
    return RuntimeCaptureAmbiguityMarker(
        schema_name="runtime.capture.ambiguity_marker",
        schema_version="1.0.0",
        marker_id=f"{capture.capture_id}.marker.{ambiguity_type}",
        corr_id=capture.corr_id,
        capture_id=capture.capture_id,
        service_name=service_name,
        ambiguity_type=ambiguity_type,
        notes=notes,
    )
