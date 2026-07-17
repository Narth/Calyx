"""Deterministic staging-only runtime reconciliation engine."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
import json

from staging.work.runtime_observer_simulation.models import ObservedProcess, RuntimeObserverSnapshot
from staging.work.runtime_reconciliation.models import (
    EquivalentResident,
    RuntimeDuplicateDetected,
    RuntimeIdentityMarker,
    RuntimeLaunchRefused,
    RuntimeReconciliationBundle,
    RuntimeReconciliationOperatorView,
    RuntimeReconciliationRequest,
    RuntimeReconciliationResult,
    RuntimeServiceDeclaration,
)


def build_default_service_declarations() -> dict[str, RuntimeServiceDeclaration]:
    return {
        "station_health_loop": RuntimeServiceDeclaration(
            schema_name="runtime.service_declaration.reconciliation",
            schema_version="1.0.0",
            declaration_id="runtime.decl.station_health_loop",
            service_name="station_health_loop",
            expected_topology_class="single_process",
            multiplicity_posture="single_instance_only",
            permitted_multiplicity_count=1,
            equivalence_matchers=[
                {
                    "matching_kind": "powershell_script_path",
                    "required_tokens": ["station_health_loop.ps1"],
                    "match_against": "command_line",
                }
            ],
            manual_override_allowed=True,
            expected_identity_markers=[
                RuntimeIdentityMarker(
                    schema_name="runtime.runtime_identity_marker",
                    schema_version="1.0.0",
                    marker_id="runtime.marker.station_health_loop.script",
                    service_name="station_health_loop",
                    marker_kind="powershell_script_path",
                    marker_value="station_health_loop.ps1",
                    notes="PowerShell-hosted loop should be attributable by script path.",
                )
            ],
            notes="Single authoritative health writer expected.",
        ),
        "bridge_overseer": RuntimeServiceDeclaration(
            schema_name="runtime.service_declaration.reconciliation",
            schema_version="1.0.0",
            declaration_id="runtime.decl.bridge_overseer",
            service_name="bridge_overseer",
            expected_topology_class="wrapper_child_runtime_pair",
            multiplicity_posture="single_wrapper_child_pair_only",
            permitted_multiplicity_count=1,
            equivalence_matchers=[
                {
                    "matching_kind": "python_module",
                    "required_tokens": ["-m calyx.cbo.bridge_overseer"],
                    "match_against": "command_line",
                }
            ],
            manual_override_allowed=True,
            expected_identity_markers=[
                RuntimeIdentityMarker(
                    schema_name="runtime.runtime_identity_marker",
                    schema_version="1.0.0",
                    marker_id="runtime.marker.bridge_overseer.module",
                    service_name="bridge_overseer",
                    marker_kind="python_module",
                    marker_value="calyx.cbo.bridge_overseer",
                    notes="Python module identifies overseer runtime.",
                )
            ],
            notes="One logical wrapper-child overseer pair allowed in steady state.",
        ),
        "navigator_triage_loop": _ps_single("navigator_triage_loop", "navigator_triage_loop.ps1"),
        "cp6_cp7_loop": _ps_single("cp6_cp7_loop", "cp6_cp7_loop.ps1"),
        "energy_churn_cp9_loop": _ps_single("energy_churn_cp9_loop", "energy_churn_cp9_loop.ps1"),
        "service_failure_watch": _ps_single("service_failure_watch", "service_failure_watch.ps1"),
        "cli_avatar": RuntimeServiceDeclaration(
            schema_name="runtime.service_declaration.reconciliation",
            schema_version="1.0.0",
            declaration_id="runtime.decl.cli_avatar",
            service_name="cli_avatar",
            expected_topology_class="wrapper_child_runtime_pair",
            multiplicity_posture="single_wrapper_child_pair_only",
            permitted_multiplicity_count=1,
            equivalence_matchers=[
                {
                    "matching_kind": "python_module",
                    "required_tokens": ["-m cbo_hub.cli_avatar.main"],
                    "match_against": "command_line",
                }
            ],
            manual_override_allowed=True,
            expected_identity_markers=[
                RuntimeIdentityMarker(
                    schema_name="runtime.runtime_identity_marker",
                    schema_version="1.0.0",
                    marker_id="runtime.marker.cli_avatar.module",
                    service_name="cli_avatar",
                    marker_kind="python_module",
                    marker_value="cbo_hub.cli_avatar.main",
                    notes="CLI avatar runtime identified by module launch string.",
                )
            ],
            notes="One logical wrapper-child CLI avatar pair allowed in steady state.",
        ),
        "test_bounded_worker": RuntimeServiceDeclaration(
            schema_name="runtime.service_declaration.reconciliation",
            schema_version="1.0.0",
            declaration_id="runtime.decl.test_bounded_worker",
            service_name="test_bounded_worker",
            expected_topology_class="single_process",
            multiplicity_posture="bounded_multi_instance",
            permitted_multiplicity_count=2,
            equivalence_matchers=[
                {
                    "matching_kind": "command_token",
                    "required_tokens": ["test_bounded_worker"],
                    "match_against": "command_line",
                }
            ],
            manual_override_allowed=False,
            notes="Test-only bounded multiplicity declaration for staging coverage.",
        ),
    }


def reconcile_runtime_request(
    request: RuntimeReconciliationRequest,
    snapshot: RuntimeObserverSnapshot,
    declarations: dict[str, RuntimeServiceDeclaration] | None = None,
    evaluated_at_utc: datetime | None = None,
) -> RuntimeReconciliationBundle:
    declarations = declarations or build_default_service_declarations()
    declaration = declarations[request.declared_service_target]

    exact_matches = [proc for proc in snapshot.processes if _matches_declaration(proc, declaration)]
    ambiguous_candidates = [proc for proc in snapshot.processes if _is_ambiguous_candidate(proc, declaration)]
    residents = _build_equivalent_residents(declaration, exact_matches)
    topology_match_state = _topology_state(declaration, residents, ambiguous_candidates)
    ambiguity_conditions = _ambiguity_conditions(ambiguous_candidates, declaration, residents)
    disposition, reasoning = _decide(declaration, residents, ambiguity_conditions)

    now = evaluated_at_utc or datetime.now(UTC)
    result = RuntimeReconciliationResult(
        schema_name="runtime.reconciliation.result",
        schema_version="1.0.0",
        result_id=f"{request.request_id}.result",
        corr_id=request.corr_id,
        request_ref=request.request_id,
        declaration_ref=declaration.declaration_id,
        snapshot_ref=snapshot.snapshot_id,
        evaluated_at_utc=now,
        matching_posture_used=declaration.multiplicity_posture,
        permitted_multiplicity_count=declaration.permitted_multiplicity_count,
        equivalent_residents=residents,
        resident_count=len(residents),
        topology_match_state=topology_match_state,
        ambiguity_conditions=ambiguity_conditions,
        disposition=disposition,
        resulting_reasoning=reasoning,
    )

    duplicate_detected = _build_duplicate_detected(request, result, declaration)
    launch_refused = _build_launch_refused(request, result, declaration)
    operator_view = RuntimeReconciliationOperatorView(
        schema_name="runtime.reconciliation.operator_view",
        schema_version="1.0.0",
        artifact_id=f"{request.request_id}.operator_view",
        corr_id=request.corr_id,
        request_ref=request.request_id,
        result_ref=result.result_id,
        service_name=declaration.service_name,
        requested_disposition=result.disposition,
        resident_count=result.resident_count,
        resident_process_ids=sorted({pid for resident in residents for pid in resident.member_process_ids}),
        evidence_support=_build_operator_evidence(declaration, residents, ambiguous_candidates),
        ambiguity_conditions=ambiguity_conditions,
        notes="Operator-readable explanation of reconciliation result.",
    )

    return RuntimeReconciliationBundle(
        scenario_name=request.request_id,
        description=f"Runtime reconciliation for {declaration.service_name}.",
        snapshot=snapshot,
        declaration=declaration,
        request=request,
        result=result,
        duplicate_detected=duplicate_detected,
        launch_refused=launch_refused,
        operator_view=operator_view,
    )


def load_snapshot(path: Path) -> RuntimeObserverSnapshot:
    return RuntimeObserverSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))


def reconcile_runtime_request_from_paths(
    request: RuntimeReconciliationRequest,
    snapshot_path: Path,
    declarations: dict[str, RuntimeServiceDeclaration] | None = None,
    evaluated_at_utc: datetime | None = None,
) -> RuntimeReconciliationBundle:
    return reconcile_runtime_request(
        request=request,
        snapshot=load_snapshot(snapshot_path),
        declarations=declarations,
        evaluated_at_utc=evaluated_at_utc,
    )


def _ps_single(service_name: str, script_name: str) -> RuntimeServiceDeclaration:
    return RuntimeServiceDeclaration(
        schema_name="runtime.service_declaration.reconciliation",
        schema_version="1.0.0",
        declaration_id=f"runtime.decl.{service_name}",
        service_name=service_name,
        expected_topology_class="single_process",
        multiplicity_posture="single_instance_only",
        permitted_multiplicity_count=1,
        equivalence_matchers=[
            {
                "matching_kind": "powershell_script_path",
                "required_tokens": [script_name],
                "match_against": "command_line",
            }
        ],
        manual_override_allowed=True,
        expected_identity_markers=[
            RuntimeIdentityMarker(
                schema_name="runtime.runtime_identity_marker",
                schema_version="1.0.0",
                marker_id=f"runtime.marker.{service_name}.script",
                service_name=service_name,
                marker_kind="powershell_script_path",
                marker_value=script_name,
                notes="PowerShell-hosted loop should be attributable by script path.",
            )
        ],
        notes=f"Single resident {service_name} loop expected.",
    )


def _matches_declaration(process: ObservedProcess, declaration: RuntimeServiceDeclaration) -> bool:
    command = process.command_line.lower()
    executable = process.executable_path.lower()
    for matcher in declaration.equivalence_matchers:
        tokens = [token.lower() for token in matcher.required_tokens]
        haystacks = []
        if matcher.match_against in ("command_line", "either"):
            haystacks.append(command)
        if matcher.match_against in ("executable_path", "either"):
            haystacks.append(executable)
        if all(any(token in haystack for haystack in haystacks) for token in tokens):
            return True
    return False


def _is_ambiguous_candidate(process: ObservedProcess, declaration: RuntimeServiceDeclaration) -> bool:
    command = process.command_line.lower()
    executable = process.executable_path.lower()
    if declaration.expected_topology_class == "single_process":
        if "powershell.exe" in executable and "unknown-command://" in command:
            return True
        if "powershell.exe" in executable and "powershell" in command and ".ps1" not in command:
            return True
    if declaration.expected_topology_class == "wrapper_child_runtime_pair":
        if "python" in executable and "unknown-command://" in command:
            return True
    return False


def _build_equivalent_residents(
    declaration: RuntimeServiceDeclaration,
    exact_matches: list[ObservedProcess],
) -> list[EquivalentResident]:
    if not exact_matches:
        return []
    if declaration.expected_topology_class == "single_process":
        residents = []
        for process in sorted(exact_matches, key=lambda item: item.pid):
            residents.append(
                EquivalentResident(
                    resident_id=f"{declaration.service_name}.resident.{process.pid}",
                    service_name=declaration.service_name,
                    member_process_ids=[process.pid],
                    topology_class="single_process",
                    evidence_fields=["command_line", "executable_path"],
                    matched_tokens=_matched_tokens_for_process(process, declaration),
                    notes="Single-process resident matched by declaration markers.",
                )
            )
        return residents

    by_pid = {proc.pid: proc for proc in exact_matches}
    groups: dict[int, list[ObservedProcess]] = defaultdict(list)
    for process in exact_matches:
        root_pid = process.parent_pid if process.parent_pid in by_pid else process.pid
        groups[root_pid].append(process)

    residents = []
    for root_pid, members in sorted(groups.items(), key=lambda item: item[0]):
        member_pids = sorted({proc.pid for proc in members})
        topology = "wrapper_child_runtime_pair" if len(member_pids) == 2 else "single_process"
        evidence = ["command_line", "parent_pid"]
        residents.append(
            EquivalentResident(
                resident_id=f"{declaration.service_name}.resident.{root_pid}",
                service_name=declaration.service_name,
                member_process_ids=member_pids,
                topology_class=topology,
                evidence_fields=evidence,
                matched_tokens=sorted({token for proc in members for token in _matched_tokens_for_process(proc, declaration)}),
                notes="Resident grouped by wrapper-child lineage." if topology == "wrapper_child_runtime_pair" else "Single unmatched resident in pair-class service.",
            )
        )
    return residents


def _matched_tokens_for_process(process: ObservedProcess, declaration: RuntimeServiceDeclaration) -> list[str]:
    matches: list[str] = []
    text = f"{process.command_line.lower()} {process.executable_path.lower()}"
    for matcher in declaration.equivalence_matchers:
        for token in matcher.required_tokens:
            if token.lower() in text:
                matches.append(token)
    return sorted(set(matches))


def _topology_state(
    declaration: RuntimeServiceDeclaration,
    residents: list[EquivalentResident],
    ambiguous_candidates: list[ObservedProcess],
) -> str:
    if ambiguous_candidates and not residents:
        return "ambiguous_host"
    if not residents:
        return "matches_expected"
    if declaration.expected_topology_class == "single_process":
        if len(residents) > 1:
            return "duplicate_peer_detected"
        return "matches_expected" if residents[0].topology_class == "single_process" else "topology_mismatch"
    if declaration.expected_topology_class == "wrapper_child_runtime_pair":
        if len(residents) > 1:
            return "duplicate_peer_detected"
        return "matches_expected" if residents[0].topology_class == "wrapper_child_runtime_pair" else "topology_mismatch"
    return "matches_expected"


def _ambiguity_conditions(
    ambiguous_candidates: list[ObservedProcess],
    declaration: RuntimeServiceDeclaration,
    residents: list[EquivalentResident],
) -> list[str]:
    conditions: list[str] = []
    if declaration.multiplicity_posture == "unclassified_no_launch_without_review":
        conditions.append("unclassified_service_target")
    if ambiguous_candidates:
        conditions.append("host_process_ambiguous")
        conditions.append("insufficient_identity_evidence")
    if declaration.expected_topology_class == "wrapper_child_runtime_pair" and residents:
        for resident in residents:
            if resident.topology_class != "wrapper_child_runtime_pair":
                conditions.append("topology_ambiguous")
                break
    return sorted(set(conditions))


def _decide(
    declaration: RuntimeServiceDeclaration,
    residents: list[EquivalentResident],
    ambiguity_conditions: list[str],
) -> tuple[str, list[str]]:
    reasoning: list[str] = []
    if "unclassified_service_target" in ambiguity_conditions:
        reasoning.append("Service target remains unclassified for launch and must fail closed.")
        return "ambiguous_runtime_blocked", reasoning
    if ambiguity_conditions and not residents:
        reasoning.append("Potential host processes exist but identity evidence is insufficient to trust equivalence.")
        return "ambiguous_runtime_blocked", reasoning

    resident_count = len(residents)
    allowed = declaration.permitted_multiplicity_count
    posture = declaration.multiplicity_posture

    if posture in {"single_instance_only", "single_wrapper_child_pair_only"}:
        if resident_count == 0:
            reasoning.append("No equivalent resident detected; new launch is permitted.")
            return "permit_new_launch", reasoning
        if resident_count == 1:
            reasoning.append("Equivalent resident already exists within singleton posture; attach or reuse instead of duplicating.")
            return "attach_to_existing_runtime", reasoning
        reasoning.append("Equivalent residents exceed singleton posture; duplicate runtime must be refused.")
        return "refuse_duplicate_launch", reasoning

    if posture in {"bounded_multi_instance", "bounded_multi_pair"}:
        if resident_count < allowed:
            reasoning.append("Equivalent residents remain below declared multiplicity bound.")
            return "permit_declared_multiplicity", reasoning
        reasoning.append("Equivalent residents meet or exceed declared multiplicity bound; new residency must be refused.")
        return "refuse_duplicate_launch", reasoning

    reasoning.append("Launch posture cannot be trusted.")
    return "ambiguous_runtime_blocked", reasoning


def _build_duplicate_detected(
    request: RuntimeReconciliationRequest,
    result: RuntimeReconciliationResult,
    declaration: RuntimeServiceDeclaration,
) -> RuntimeDuplicateDetected | None:
    if result.resident_count <= 1 and result.disposition != "refuse_duplicate_launch":
        return None
    failure_class = "undeclared_multiplicity"
    if declaration.expected_topology_class == "wrapper_child_runtime_pair":
        failure_class = "duplicate_wrapper_child_pair"
    if declaration.multiplicity_posture in {"single_instance_only", "single_wrapper_child_pair_only"}:
        failure_class = "singleton_violation" if declaration.expected_topology_class == "single_process" else "duplicate_wrapper_child_pair"
    return RuntimeDuplicateDetected(
        schema_name="runtime.duplicate.runtime_detected",
        schema_version="1.0.0",
        artifact_id=f"{request.request_id}.duplicate_detected",
        corr_id=request.corr_id,
        request_ref=request.request_id,
        result_ref=result.result_id,
        service_name=declaration.service_name,
        failure_class=failure_class,
        equivalent_resident_count=result.resident_count,
        notes="Undeclared or excess equivalent residents detected during staging reconciliation.",
    )


def _build_launch_refused(
    request: RuntimeReconciliationRequest,
    result: RuntimeReconciliationResult,
    declaration: RuntimeServiceDeclaration,
) -> RuntimeLaunchRefused | None:
    if result.disposition not in {"refuse_duplicate_launch", "ambiguous_runtime_blocked"}:
        return None
    refusal_reason = "duplicate_runtime" if result.disposition == "refuse_duplicate_launch" else "ambiguous_runtime"
    if "unclassified_service_target" in result.ambiguity_conditions:
        refusal_reason = "unclassified_service_target"
    return RuntimeLaunchRefused(
        schema_name="runtime.launch.refused",
        schema_version="1.0.0",
        artifact_id=f"{request.request_id}.launch_refused",
        corr_id=request.corr_id,
        request_ref=request.request_id,
        result_ref=result.result_id,
        service_name=declaration.service_name,
        refusal_reason=refusal_reason,
        notes="Governed staging reconciliation refused the requested launch.",
    )


def _build_operator_evidence(
    declaration: RuntimeServiceDeclaration,
    residents: list[EquivalentResident],
    ambiguous_candidates: list[ObservedProcess],
) -> list[str]:
    evidence = [f"service={declaration.service_name}", f"expected_topology={declaration.expected_topology_class}"]
    if residents:
        evidence.append(f"equivalent_residents={len(residents)}")
        for resident in residents:
            evidence.append(f"resident:{resident.resident_id}:pids={','.join(str(pid) for pid in resident.member_process_ids)}")
    if ambiguous_candidates:
        evidence.append(f"ambiguous_candidates={len(ambiguous_candidates)}")
    return evidence
