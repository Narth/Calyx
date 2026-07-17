"""Deterministic operator-facing runtime summary generation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from staging.work.runtime_capture_adapter.models import RuntimeCaptureClassificationResult, RuntimeCaptureInput
from staging.work.runtime_governance_models.models import RuntimeGovernanceBundle
from staging.work.runtime_operator_summary.models import (
    OperatorAmbiguityRecord,
    OperatorAttributionGap,
    OperatorExpectationSignal,
    OperatorGovernancePosture,
    OperatorStationRuntimeProcess,
    OperatorStationRuntimeView,
    OperatorSystemLoadSnapshot,
    OperatorTopProcess,
    OperatorWorkstationLoadView,
    RuntimeOperatorSummary,
)


def generate_runtime_operator_summary(
    capture: RuntimeCaptureInput,
    classified: RuntimeCaptureClassificationResult,
) -> RuntimeOperatorSummary:
    bundles = classified.observer_emission.governance_bundles
    load_snapshot = _build_load_snapshot(capture, bundles)
    top_processes = _build_top_processes(capture, bundles)
    governance_posture = [_build_governance_posture(bundle) for bundle in bundles]
    ambiguities = [
        OperatorAmbiguityRecord(
            service_name=marker.service_name,
            ambiguity_type=marker.ambiguity_type,
            notes=marker.notes,
        )
        for marker in classified.normalization.ambiguity_markers
    ]

    workstation_load_view = OperatorWorkstationLoadView(
        system_load_snapshot=load_snapshot,
        top_processes=top_processes,
        observed_process_count=len(capture.process_rows),
        notes=[
            "Whole-workstation view is unfiltered and reflects captured machine state, not just Station-governed runtime.",
            "Top processes are sourced from health enrichment or captured station health when available.",
        ],
    )
    station_runtime_view = _build_station_runtime_view(capture, governance_posture, bundles)
    attribution_gaps = _build_attribution_gaps(classified, station_runtime_view, bundles)
    expectation_signals = _build_expectation_signals(load_snapshot, governance_posture, ambiguities, bundles)
    system_load_condition = _derive_system_load_condition(load_snapshot)
    governance_compliance_condition = _derive_governance_compliance_condition(governance_posture, attribution_gaps)
    operator_risk_signal, operator_risk_reasoning = _derive_operator_risk(
        load_snapshot=load_snapshot,
        governance_posture=governance_posture,
        workstation_top_processes=top_processes,
        attribution_gaps=attribution_gaps,
        system_load_condition=system_load_condition,
        governance_compliance_condition=governance_compliance_condition,
        expectation_signals=expectation_signals,
    )

    return RuntimeOperatorSummary(
        schema_name="runtime.operator.summary",
        schema_version="1.1.0",
        summary_id=f"{capture.capture_id}.operator_summary",
        capture_id=capture.capture_id,
        corr_id=capture.corr_id,
        generated_at_utc=classified.classified_at_utc,
        source_capture_mode=capture.capture_mode,
        workstation_load_view=workstation_load_view,
        station_runtime_view=station_runtime_view,
        attribution_gaps=attribution_gaps,
        system_load_snapshot=workstation_load_view.system_load_snapshot,
        top_processes=workstation_load_view.top_processes,
        governance_posture=station_runtime_view.governance_posture,
        expectation_signals=expectation_signals,
        ambiguities=ambiguities,
        system_load_condition=system_load_condition,
        governance_compliance_condition=governance_compliance_condition,
        operator_risk_signal=operator_risk_signal,
        operator_risk_reasoning=operator_risk_reasoning,
        notes="Operator summary is a staging-only visibility surface derived from capture and governance artifacts without runtime mutation.",
    )


def load_runtime_operator_summary_inputs(
    capture_path: Path,
    classification_path: Path,
) -> tuple[RuntimeCaptureInput, RuntimeCaptureClassificationResult]:
    capture = RuntimeCaptureInput.model_validate_json(capture_path.read_text(encoding="utf-8"))
    classified = RuntimeCaptureClassificationResult.model_validate_json(classification_path.read_text(encoding="utf-8"))
    return capture, classified


def generate_runtime_operator_summary_from_paths(
    capture_path: Path,
    classification_path: Path,
) -> RuntimeOperatorSummary:
    capture, classified = load_runtime_operator_summary_inputs(capture_path, classification_path)
    return generate_runtime_operator_summary(capture, classified)


def _build_load_snapshot(
    capture: RuntimeCaptureInput,
    bundles: list[RuntimeGovernanceBundle],
) -> OperatorSystemLoadSnapshot:
    health_bundle = next((bundle for bundle in bundles if bundle.service_declaration.service_name == "station_health_loop"), None)
    if health_bundle is not None and health_bundle.health_authoritative_snapshot is not None:
        auth = health_bundle.health_authoritative_snapshot
        enrich = health_bundle.health_enrichment_snapshot
        return OperatorSystemLoadSnapshot(
            cpu_pct=auth.cpu_pct,
            ram_pct=auth.ram_pct,
            memory_pressure_tier=auth.memory_pressure_tier,
            gpu_metrics_present=enrich.gpu_metrics_present if enrich is not None else capture.station_health.gpu_metrics_present if capture.station_health else None,
            vram_metrics_available=False,
            health_state=auth.health_state,
            freshness_state=auth.freshness_state,
            source_surface=auth.truth_contract_surface,
            notes="System load derived from the authoritative health snapshot; GPU presence reflects enrichment or captured station health when available.",
        )
    if capture.station_health is not None:
        return OperatorSystemLoadSnapshot(
            cpu_pct=capture.station_health.cpu_pct,
            ram_pct=capture.station_health.ram_pct,
            memory_pressure_tier=capture.station_health.memory_pressure_tier,
            gpu_metrics_present=capture.station_health.gpu_metrics_present,
            vram_metrics_available=False,
            health_state=capture.station_health.health,
            freshness_state=capture.station_health.truth_state,
            source_surface=capture.station_health.source_path,
            notes="System load derived directly from captured station health because no authoritative governance bundle was present.",
        )
    return OperatorSystemLoadSnapshot(
        cpu_pct=None,
        ram_pct=None,
        memory_pressure_tier=None,
        gpu_metrics_present=None,
        vram_metrics_available=False,
        health_state=None,
        freshness_state=None,
        source_surface="runtime.capture.input",
        notes="System load was unavailable in the capture input; summary preserves that absence explicitly.",
    )


def _build_top_processes(
    capture: RuntimeCaptureInput,
    bundles: list[RuntimeGovernanceBundle],
) -> list[OperatorTopProcess]:
    health_bundle = next((bundle for bundle in bundles if bundle.service_declaration.service_name == "station_health_loop"), None)
    source = "station_health_capture"
    labels: list[str] = []
    if health_bundle is not None and health_bundle.health_enrichment_snapshot is not None:
        labels = health_bundle.health_enrichment_snapshot.top_processes
        source = "health_enrichment_snapshot"
    elif capture.station_health is not None:
        labels = capture.station_health.top_processes
    process_index = {row.pid: row for row in capture.process_rows}
    entries: list[OperatorTopProcess] = []
    for rank, label in enumerate(labels, start=1):
        process_name, pid = _parse_top_process_label(label)
        matched = process_index.get(pid) if pid is not None else None
        entries.append(
            OperatorTopProcess(
                rank=rank,
                source=source,
                process_label=label,
                pid=pid,
                executable_path=matched.executable_path if matched is not None else None,
                command_line=matched.command_line if matched is not None else None,
                governed_surface=_governed_surface_for_command(matched.command_line if matched is not None else None),
                notes=None if matched is not None else f"No captured process row resolved for {process_name}.",
            )
        )
    return entries


def _build_governance_posture(bundle: RuntimeGovernanceBundle) -> OperatorGovernancePosture:
    validation = bundle.runtime_multiplicity_validation
    noncompliance = bundle.runtime_multiplicity_noncompliance
    notes = [validation.classification_notes]
    if noncompliance is not None:
        notes.append(noncompliance.notes)
    if bundle.health_authoritative_snapshot is not None:
        notes.append(
            f"Health is {bundle.health_authoritative_snapshot.health_state} with {bundle.health_authoritative_snapshot.freshness_state} freshness."
        )
    if bundle.bridge_pulse_classification is not None:
        notes.append(
            f"Bridge pulse is {bundle.bridge_pulse_classification.pulse_class} with work_state={bundle.bridge_pulse_classification.work_state}."
        )
    return OperatorGovernancePosture(
        service_name=bundle.service_declaration.service_name,
        topology_class=bundle.service_declaration.topology_class,
        multiplicity_posture=bundle.service_declaration.multiplicity_posture,
        authoritative_runtime_role=bundle.service_declaration.authoritative_runtime_role,
        observed_process_count=len(validation.observed_process_identities),
        validation_outcome=validation.validation_outcome,
        posture_consequence=validation.posture_consequence,
        noncompliance_type=noncompliance.noncompliance_type if noncompliance is not None else None,
        noncompliance_severity=noncompliance.severity if noncompliance is not None else None,
        health_state=bundle.health_authoritative_snapshot.health_state if bundle.health_authoritative_snapshot is not None else None,
        freshness_state=bundle.health_authoritative_snapshot.freshness_state if bundle.health_authoritative_snapshot is not None else None,
        pulse_class=bundle.bridge_pulse_classification.pulse_class if bundle.bridge_pulse_classification is not None else None,
        idle_reason=bundle.bridge_pulse_classification.idle_reason if bundle.bridge_pulse_classification is not None else None,
        notes=notes,
    )


def _build_station_runtime_view(
    capture: RuntimeCaptureInput,
    governance_posture: list[OperatorGovernancePosture],
    bundles: list[RuntimeGovernanceBundle],
) -> OperatorStationRuntimeView:
    known_pids: dict[int, tuple[str | None, list[str]]] = {}
    for bundle in bundles:
        validation = bundle.runtime_multiplicity_validation
        for identity in validation.observed_process_identities:
            known_pids[identity.pid] = (
                bundle.service_declaration.service_name,
                [f"Observed in governance validation artifact {validation.artifact_id}."],
            )

    processes: list[OperatorStationRuntimeProcess] = []
    for row in capture.process_rows:
        if row.pid in known_pids:
            service_name, evidence_notes = known_pids[row.pid]
            processes.append(
                OperatorStationRuntimeProcess(
                    pid=row.pid,
                    executable_path=row.executable_path,
                    command_line=row.command_line,
                    station_membership="known_governed_service",
                    service_name=service_name,
                    evidence_notes=evidence_notes,
                )
            )
            continue

        membership = _candidate_station_membership(row.command_line, row.executable_path)
        if membership is not None:
            processes.append(
                OperatorStationRuntimeProcess(
                    pid=row.pid,
                    executable_path=row.executable_path,
                    command_line=row.command_line,
                    station_membership=membership,
                    service_name=None,
                    evidence_notes=_candidate_station_evidence(row.command_line, row.executable_path, membership),
                )
            )

    return OperatorStationRuntimeView(
        processes=processes,
        governance_posture=governance_posture,
        notes=[
            "Station runtime view is a strict evidence-backed subset of the workstation process capture.",
            "Known governed processes come from runtime multiplicity validation artifacts.",
            "Candidate or ambiguous Station membership is shown only when command-line or executable-path evidence points at Calyx surfaces.",
        ],
    )


def _build_attribution_gaps(
    classified: RuntimeCaptureClassificationResult,
    station_runtime_view: OperatorStationRuntimeView,
    bundles: list[RuntimeGovernanceBundle],
) -> list[OperatorAttributionGap]:
    gaps: list[OperatorAttributionGap] = []
    for bundle in bundles:
        validation = bundle.runtime_multiplicity_validation
        noncompliance = bundle.runtime_multiplicity_noncompliance
        if noncompliance is not None and noncompliance.noncompliance_type == "missing_launch_notice":
            gaps.append(
                OperatorAttributionGap(
                    gap_type="missing_launch_notice",
                    service_name=bundle.service_declaration.service_name,
                    severity="warn",
                    reasoning=noncompliance.notes,
                    evidence_refs=[validation.artifact_id, noncompliance.artifact_id],
                    affected_process_ids=[item.pid for item in validation.observed_process_identities],
                )
            )
        if validation.validation_outcome == "duplicate_concerning":
            gaps.append(
                OperatorAttributionGap(
                    gap_type="topology_mismatch",
                    service_name=bundle.service_declaration.service_name,
                    severity="risk",
                    reasoning=validation.classification_notes,
                    evidence_refs=[validation.artifact_id],
                    affected_process_ids=[item.pid for item in validation.observed_process_identities],
                )
            )

    capture_refs: dict[tuple[str, str], list[str]] = defaultdict(list)
    capture_pids: dict[tuple[str, str], list[int]] = defaultdict(list)
    service_refs: dict[tuple[str, str], list[str]] = defaultdict(list)
    service_pids: dict[tuple[str, str], list[int]] = defaultdict(list)
    for marker in classified.normalization.ambiguity_markers:
        key = (marker.service_name, marker.ambiguity_type)
        pid = _pid_from_marker_id(marker.marker_id)
        if marker.service_name == "capture_layer":
            capture_refs[key].append(marker.marker_id)
            if pid is not None:
                capture_pids[key].append(pid)
        else:
            service_refs[key].append(marker.marker_id)
            if pid is not None:
                service_pids[key].append(pid)

    for key, refs in sorted(capture_refs.items()):
        service_name, ambiguity_type = key
        gaps.append(
            OperatorAttributionGap(
                gap_type="missing_command_line_data" if ambiguity_type == "missing_command_line" else "missing_executable_path_data",
                service_name=service_name,
                severity="warn",
                reasoning=(
                    f"{len(refs)} captured processes are missing command-line data."
                    if ambiguity_type == "missing_command_line"
                    else f"{len(refs)} captured processes are missing executable-path data."
                ),
                evidence_refs=refs,
                affected_process_ids=sorted(capture_pids[key]),
            )
        )

    gap_type_map = {
        "health_cadence_unresolved": "health_cadence_unresolved",
        "health_expiry_sweep_unresolved": "health_expiry_sweep_unresolved",
        "bridge_idle_reason_unresolved": "bridge_idle_reason_unresolved",
        "bridge_work_state_unresolved": "bridge_work_state_unresolved",
        "no_matching_service_processes": "unresolved_parent_child_relationship",
    }
    for key, refs in sorted(service_refs.items()):
        service_name, ambiguity_type = key
        gaps.append(
            OperatorAttributionGap(
                gap_type=gap_type_map[ambiguity_type],
                service_name=service_name,
                severity="warn",
                reasoning=f"{service_name} has unresolved capture evidence for {ambiguity_type}.",
                evidence_refs=refs,
                affected_process_ids=sorted(service_pids[key]),
            )
        )

    for proc in station_runtime_view.processes:
        if proc.station_membership == "candidate_unattributed":
            gaps.append(
                OperatorAttributionGap(
                    gap_type="undeclared_runtime_process",
                    service_name="capture_layer",
                    severity="info",
                    reasoning=f"Process PID {proc.pid} shows Station-related evidence but is not mapped to a declared governed service.",
                    evidence_refs=[f"process_row:{proc.pid}"],
                    affected_process_ids=[proc.pid],
                )
            )
        elif proc.station_membership == "ambiguous_station_membership":
            gaps.append(
                OperatorAttributionGap(
                    gap_type="unresolved_parent_child_relationship",
                    service_name="capture_layer",
                    severity="warn",
                    reasoning=f"Process PID {proc.pid} has incomplete Station-attribution evidence.",
                    evidence_refs=[f"process_row:{proc.pid}"],
                    affected_process_ids=[proc.pid],
                )
            )
    return gaps


def _build_expectation_signals(
    load_snapshot: OperatorSystemLoadSnapshot,
    posture: list[OperatorGovernancePosture],
    ambiguities: list[OperatorAmbiguityRecord],
    bundles: list[RuntimeGovernanceBundle],
) -> list[OperatorExpectationSignal]:
    signals: list[OperatorExpectationSignal] = []
    for entry in posture:
        if entry.validation_outcome == "duplicate_concerning":
            signals.append(
                OperatorExpectationSignal(
                    signal_type="duplicate_concerning",
                    service_name=entry.service_name,
                    severity="risk",
                    reasoning=f"{entry.service_name} runtime shape conflicts with its declared multiplicity posture.",
                )
            )
        elif entry.validation_outcome in ("multiplicity_declared_but_noncompliant", "undeclared_multiplicity"):
            signals.append(
                OperatorExpectationSignal(
                    signal_type="multiplicity_noncompliance",
                    service_name=entry.service_name,
                    severity="warn" if entry.validation_outcome == "multiplicity_declared_but_noncompliant" else "risk",
                    reasoning=f"{entry.service_name} does not fully match its declared multiplicity contract.",
                )
            )
        if entry.service_name == "station_health_loop":
            if entry.health_state == "fail":
                signals.append(
                    OperatorExpectationSignal(
                        signal_type="health_fail",
                        service_name="station_health_loop",
                        severity="critical",
                        reasoning="Authoritative station health reported fail.",
                    )
                )
            if entry.freshness_state == "stale":
                signals.append(
                    OperatorExpectationSignal(
                        signal_type="health_stale",
                        service_name="station_health_loop",
                        severity="risk",
                        reasoning="Station health truth is stale, reducing confidence in current status.",
                    )
                )
            if entry.freshness_state == "unknown":
                signals.append(
                    OperatorExpectationSignal(
                        signal_type="health_unknown",
                        service_name="station_health_loop",
                        severity="critical",
                        reasoning="Station health freshness is unknown.",
                    )
                )
            bundle = next((item for item in bundles if item.service_declaration.service_name == "station_health_loop"), None)
            if bundle is not None and bundle.health_authoritative_snapshot is not None and not bundle.health_authoritative_snapshot.cadence_compliant:
                signals.append(
                    OperatorExpectationSignal(
                        signal_type="cadence_noncompliant",
                        service_name="station_health_loop",
                        severity="warn",
                        reasoning="Observed health-loop cadence did not meet the declared interval.",
                    )
                )
        if entry.service_name == "bridge_overseer" and entry.pulse_class == "idle":
            signals.append(
                OperatorExpectationSignal(
                    signal_type="idle_bridge_visible",
                    service_name="bridge_overseer",
                    severity="info",
                    reasoning=f"Bridge overseer is idle with reason={entry.idle_reason}; this is visible, not hidden.",
                )
            )
    for ambiguity in ambiguities:
        if ambiguity.service_name in ("station_health_loop", "bridge_overseer"):
            signals.append(
                OperatorExpectationSignal(
                    signal_type="governed_ambiguity_present",
                    service_name=ambiguity.service_name,
                    severity="warn",
                    reasoning=f"{ambiguity.service_name} captured ambiguity: {ambiguity.ambiguity_type}.",
                )
            )
    if load_snapshot.cpu_pct is not None and load_snapshot.cpu_pct >= 75:
        signals.append(
            OperatorExpectationSignal(
                signal_type="load_elevated",
                service_name="system",
                severity="warn" if load_snapshot.cpu_pct < 90 else "risk",
                reasoning=f"Observed CPU load is elevated at {load_snapshot.cpu_pct}%.",
            )
        )
    if load_snapshot.ram_pct is not None and load_snapshot.ram_pct >= 80:
        signals.append(
            OperatorExpectationSignal(
                signal_type="load_elevated",
                service_name="system",
                severity="warn" if load_snapshot.ram_pct < 90 else "risk",
                reasoning=f"Observed RAM load is elevated at {load_snapshot.ram_pct}%.",
            )
        )
    return signals


def _derive_system_load_condition(load_snapshot: OperatorSystemLoadSnapshot) -> str:
    values = [value for value in (load_snapshot.cpu_pct, load_snapshot.ram_pct) if value is not None]
    if not values:
        return "unknown"
    if max(values) >= 90:
        return "high"
    if max(values) >= 75 or load_snapshot.health_state == "warn":
        return "elevated"
    return "normal"


def _derive_governance_compliance_condition(
    posture: list[OperatorGovernancePosture],
    attribution_gaps: list[OperatorAttributionGap],
) -> str:
    if any(item.validation_outcome == "duplicate_concerning" for item in posture):
        return "critical"
    if any(item.validation_outcome in ("multiplicity_declared_but_noncompliant", "undeclared_multiplicity") for item in posture):
        return "noncompliant"
    if any(gap.severity in ("warn", "risk", "critical") for gap in attribution_gaps):
        return "ambiguous"
    return "compliant"


def _derive_operator_risk(
    *,
    load_snapshot: OperatorSystemLoadSnapshot,
    governance_posture: list[OperatorGovernancePosture],
    workstation_top_processes: list[OperatorTopProcess],
    attribution_gaps: list[OperatorAttributionGap],
    system_load_condition: str,
    governance_compliance_condition: str,
    expectation_signals: list[OperatorExpectationSignal],
) -> tuple[str, list[str]]:
    reasons = [
        f"System load condition: {system_load_condition.upper()}" + (
            f" (CPU {load_snapshot.cpu_pct}% / RAM {load_snapshot.ram_pct}%)."
            if load_snapshot.cpu_pct is not None or load_snapshot.ram_pct is not None
            else "."
        ),
        _load_origin_reason(workstation_top_processes),
        f"Governance compliance condition: {governance_compliance_condition.upper()}.",
    ]

    if any(sig.severity == "critical" for sig in expectation_signals):
        reasons.extend(signal.reasoning for signal in expectation_signals if signal.severity == "critical")
        return "CRITICAL", reasons
    if governance_compliance_condition == "critical":
        reasons.extend(_top_gap_reasons(attribution_gaps, {"risk", "critical"}))
        return "RISK", reasons
    if governance_compliance_condition == "noncompliant":
        reasons.extend(_top_gap_reasons(attribution_gaps, {"warn", "risk", "critical"}))
        return "UNEXPECTED", reasons
    if system_load_condition == "high":
        return "RISK", reasons
    if governance_compliance_condition == "ambiguous":
        reasons.extend(_top_gap_reasons(attribution_gaps, {"warn", "risk"}))
        return "ELEVATED", reasons
    if system_load_condition == "elevated":
        return "ELEVATED", reasons
    return "NORMAL", reasons + ["Observed governed surfaces are compliant and no elevated machine-load condition was detected."]


def _load_origin_reason(workstation_top_processes: list[OperatorTopProcess]) -> str:
    governed = [proc for proc in workstation_top_processes if proc.governed_surface is not None]
    if not workstation_top_processes:
        return "Primary load source is unresolved because no top-process sample was available."
    if not governed:
        return "Primary sampled load is currently dominated by non-governed processes."
    if len(governed) == len(workstation_top_processes):
        return "Primary sampled load is currently dominated by governed Station processes."
    return "Primary sampled load is mixed between governed Station processes and non-governed processes."


def _top_gap_reasons(gaps: list[OperatorAttributionGap], severities: set[str]) -> list[str]:
    return [gap.reasoning for gap in gaps if gap.severity in severities][:3]


def _candidate_station_membership(command_line: str | None, executable_path: str | None) -> str | None:
    cmd = (command_line or "").lower()
    exe = (executable_path or "").lower()
    markers = ("c:\\calyx_terminal", "\\.venv_cbohub311\\", "cbo_hub", "calyx.cbo", "\\scripts\\")
    evidence_count = sum(1 for marker in markers if marker in cmd or marker in exe)
    if evidence_count == 0:
        return None
    if not command_line or not executable_path:
        return "ambiguous_station_membership"
    return "candidate_unattributed"


def _candidate_station_evidence(command_line: str | None, executable_path: str | None, membership: str) -> list[str]:
    notes: list[str] = []
    if command_line and "c:\\calyx_terminal" in command_line.lower():
        notes.append("Command line references the Calyx repository path.")
    if executable_path and ("c:\\calyx_terminal" in executable_path.lower() or "\\.venv_cbohub311\\" in executable_path.lower()):
        notes.append("Executable path references a Calyx-local runtime path.")
    if command_line and ("cbo_hub" in command_line.lower() or "calyx.cbo" in command_line.lower()):
        notes.append("Command line references a Calyx Python module.")
    if membership == "ambiguous_station_membership":
        notes.append("Station membership remains ambiguous because command-line or executable-path evidence is incomplete.")
    return notes or ["Process shows partial Station-related evidence."]


def _parse_top_process_label(label: str) -> tuple[str, int | None]:
    if "#" not in label:
        return label, None
    name, pid_part = label.rsplit("#", 1)
    try:
        return name, int(pid_part)
    except ValueError:
        return label, None


def _governed_surface_for_command(command_line: str | None) -> str | None:
    lowered = (command_line or "").lower()
    if "station_health_loop.ps1" in lowered:
        return "station_health_loop"
    if "calyx.cbo.bridge_overseer" in lowered:
        return "bridge_overseer"
    return None


def _pid_from_marker_id(marker_id: str) -> int | None:
    maybe_pid = marker_id.rsplit(".", 1)[-1]
    try:
        return int(maybe_pid)
    except ValueError:
        return None
