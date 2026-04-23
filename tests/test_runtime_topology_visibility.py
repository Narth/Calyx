from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from staging.work.runtime_capture_adapter.models import CapturedPort, CapturedProcessRow, RuntimeCaptureInput

from calyx.governance.runtime_topology import (
    build_runtime_topology_snapshot,
    write_runtime_topology_artifacts,
)


def _capture(*rows: CapturedProcessRow) -> RuntimeCaptureInput:
    return RuntimeCaptureInput(
        schema_name="runtime.capture.input",
        schema_version="1.0.0",
        capture_id="runtime.topology.test",
        corr_id="runtime.topology.test",
        captured_at_utc=datetime(2026, 4, 15, 20, 0, 0, tzinfo=UTC),
        capture_mode="offline_replay",
        process_rows=list(rows),
        capture_notes="Topology visibility unit test capture.",
    )


def test_listener_service_pair_collapses_to_one_logical_instance() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=1001,
            parent_pid=400,
            process_name="python.exe",
            executable_path=r"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe",
            command_line=r'"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe" -B -m uvicorn cbo_hub.dev_harness.app:app --host 127.0.0.1 --port 7777',
            started_at_utc=datetime(2026, 4, 15, 19, 0, 0, tzinfo=UTC),
        ),
        CapturedProcessRow(
            pid=1002,
            parent_pid=1001,
            process_name="python.exe",
            executable_path=r"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe",
            command_line=r'"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe" -B -m uvicorn cbo_hub.dev_harness.app:app --host 127.0.0.1 --port 7777',
            started_at_utc=datetime(2026, 4, 15, 19, 0, 1, tzinfo=UTC),
            ports=[CapturedPort(local_address="127.0.0.1", local_port=7777, state="Listen")],
        ),
        CapturedProcessRow(
            pid=1003,
            parent_pid=1001,
            process_name="conhost.exe",
            executable_path=r"C:\WINDOWS\system32\conhost.exe",
            command_line=r"\??\C:\WINDOWS\system32\conhost.exe 0x4",
            started_at_utc=datetime(2026, 4, 15, 19, 0, 1, tzinfo=UTC),
        ),
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    service = snapshot["services"]["dev_harness"]

    assert service["observed_instance_count"] == 1
    assert service["multiplicity_state"] == "singleton_expected"
    assert service["authoritative_runtime"]["pid"] == 1002
    assert service["observed_instances"][0]["members"][0]["runtime_class"] == "launcher_wrapper"
    assert any(member["runtime_class"] == "effective_service_runtime" for member in service["observed_instances"][0]["members"])
    observed = {row["pid"]: row for row in snapshot["observed_runtime"]}
    assert observed[1001]["matched_identity"] == "Dev Harness Python service wrapper"
    assert observed[1001]["identity_status"] == "named"
    assert observed[1001]["identity_confidence"] == "high"
    assert observed[1001]["authority_posture"] == "declared_wrapper_non_authoritative"
    assert observed[1002]["matched_identity"] == "Dev Harness"
    assert observed[1002]["authority_posture"] == "authoritative"


def test_duplicate_singleton_loops_are_flagged_critical() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=2001,
            parent_pid=900,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\navigator_triage_loop.ps1',
            started_at_utc=datetime(2026, 4, 15, 18, 0, 0, tzinfo=UTC),
        ),
        CapturedProcessRow(
            pid=2002,
            parent_pid=901,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\navigator_triage_loop.ps1',
            started_at_utc=datetime(2026, 4, 15, 18, 5, 0, tzinfo=UTC),
        ),
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    service = snapshot["services"]["navigator_triage_loop"]

    assert service["multiplicity_state"] == "duplicate_concerning"
    assert service["risk_level"] == "CRITICAL"
    assert service["topology_ambiguous"] is True
    assert "multiple_authoritative_candidates" in service["anomaly_flags"]


def test_non_listener_wrapper_child_pair_is_visible_without_false_duplicate_alarm() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=3001,
            parent_pid=700,
            process_name="python.exe",
            executable_path=r"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe",
            command_line=r'"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe" -B -m calyx.cbo.bridge_overseer',
            started_at_utc=datetime(2026, 4, 15, 17, 0, 0, tzinfo=UTC),
        ),
        CapturedProcessRow(
            pid=3002,
            parent_pid=3001,
            process_name="python.exe",
            executable_path=r"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe",
            command_line=r'"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe" -B -m calyx.cbo.bridge_overseer',
            started_at_utc=datetime(2026, 4, 15, 17, 0, 1, tzinfo=UTC),
        ),
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    service = snapshot["services"]["bridge_overseer"]

    assert service["observed_instance_count"] == 1
    assert service["multiplicity_state"] == "duplicate_runtime_pair_non_listener"
    assert service["risk_level"] == "LOW"
    assert service["authoritative_runtime"]["pid"] == 3002


def test_station_related_unmapped_runtime_marks_partial_classification() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=4001,
            parent_pid=500,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\custom_station_probe.ps1',
            started_at_utc=datetime(2026, 4, 15, 17, 30, 0, tzinfo=UTC),
        )
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)

    assert snapshot["classification_status"] == "partial"
    assert snapshot["classification_gaps"][0]["type"] == "undeclared_station_runtime"
    observed = next(row for row in snapshot["observed_runtime"] if row["pid"] == 4001)
    assert observed["station_related"] is True
    assert observed["declared_service"] is None
    assert observed["identity_status"] == "uncertain"
    assert observed["matched_identity"] == "uncertain"
    assert observed["declared_status"] == "undeclared_station_related"


def test_artifact_writer_emits_snapshot_and_receipt(tmp_path: Path) -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=5001,
            parent_pid=410,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\service_failure_watch.ps1',
            started_at_utc=datetime(2026, 4, 15, 16, 0, 0, tzinfo=UTC),
        )
    )

    result = write_runtime_topology_artifacts(
        repo_root=tmp_path,
        capture=capture,
        emitted_at_utc=datetime(2026, 4, 15, 20, 0, 0, tzinfo=UTC),
        force_stale=True,
        stale_reason="test_force_stale",
    )

    snapshot_path = Path(result["snapshot_path"])
    receipt_path = Path(result["receipt_path"])
    assert snapshot_path.exists()
    assert receipt_path.exists()

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "station.runtime_topology_snapshot.v2"
    assert payload["truth_state"] == "stale"
    assert payload["stale_reason"] == "test_force_stale"
    assert payload["state_summary"]["runtime_topology_truth_state"] == "stale"
    assert "operator_runtime_table" in payload
    assert payload["operator_runtime_table"][0]["matched_identity"] == "Service failure watch"


def test_auxiliary_patch_and_observer_processes_do_not_count_as_unresolved_debt() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=6001,
            parent_pid=6100,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\station_patch_sunrise.ps1',
            started_at_utc=datetime(2026, 4, 15, 20, 10, 0, tzinfo=UTC),
        ),
        CapturedProcessRow(
            pid=6002,
            parent_pid=6001,
            process_name="python.exe",
            executable_path=r"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe",
            command_line=r'python C:\Calyx_Terminal\Scripts\runtime_topology_snapshot.py --repo-root C:\Calyx_Terminal',
            started_at_utc=datetime(2026, 4, 15, 20, 10, 1, tzinfo=UTC),
        ),
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)

    assert snapshot["classification_status"] == "complete"
    assert snapshot["unresolved_station_related_pids"] == []
    assert snapshot["auxiliary_runtime_families"]["station_patch_window"]["observed_process_count"] == 1
    assert snapshot["auxiliary_runtime_families"]["runtime_truth_observer"]["observed_process_count"] == 1
    observed = {row["pid"]: row for row in snapshot["observed_runtime"]}
    assert observed[6001]["auxiliary_family"] == "station_patch_window"
    assert observed[6002]["auxiliary_family"] == "runtime_truth_observer"
    assert observed[6001]["matched_identity"] == "PowerShell patch sunrise script"
    assert observed[6002]["matched_identity"] == "Runtime topology snapshot observer"
    assert observed[6001]["declared_status"] == "declared_auxiliary"
    assert observed[6002]["authority_posture"] == "auxiliary_non_authoritative"


def test_external_known_runtime_is_named_without_authority() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=7001,
            parent_pid=1,
            process_name="ollama.exe",
            executable_path=r"C:\Users\jncr0\AppData\Local\Programs\Ollama\ollama.exe",
            command_line=r'C:\Users\jncr0\AppData\Local\Programs\Ollama\ollama.exe serve',
            started_at_utc=datetime(2026, 4, 15, 20, 12, 0, tzinfo=UTC),
            ports=[CapturedPort(local_address="127.0.0.1", local_port=11434, state="Listen")],
        )
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)

    observed = next(row for row in snapshot["observed_runtime"] if row["pid"] == 7001)
    assert observed["matched_identity"] == "Ollama"
    assert observed["identity_status"] == "named"
    assert observed["identity_confidence"] == "high"
    assert observed["authority_posture"] == "external_non_authoritative"
    assert observed["declared_status"] == "not_declared"


def test_named_vs_authoritative_remain_distinct() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=7101,
            parent_pid=400,
            process_name="python.exe",
            executable_path=r"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe",
            command_line=r'"C:\Calyx_Terminal\.venv_cbohub311\Scripts\python.exe" -m calyx.cbo.discord_gateway',
            started_at_utc=datetime(2026, 4, 15, 20, 13, 0, tzinfo=UTC),
        ),
        CapturedProcessRow(
            pid=7102,
            parent_pid=7101,
            process_name="python.exe",
            executable_path=r"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe",
            command_line=r'"C:\Users\jncr0\AppData\Local\Programs\Python\Python311\python.exe" -m calyx.cbo.discord_gateway',
            started_at_utc=datetime(2026, 4, 15, 20, 13, 1, tzinfo=UTC),
            ports=[CapturedPort(remote_address="162.159.0.1", remote_port=443, state="Established")],
        ),
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    observed = {row["pid"]: row for row in snapshot["observed_runtime"]}

    assert observed[7101]["matched_identity"] == "Discord gateway Python service wrapper"
    assert observed[7101]["identity_status"] == "named"
    assert observed[7101]["authority_posture"] == "declared_wrapper_non_authoritative"
    assert observed[7102]["matched_identity"] == "Discord gateway"
    assert observed[7102]["authority_posture"] == "authoritative"


def test_ambiguous_multi_signal_identity_resolves_to_uncertain() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=7201,
            parent_pid=100,
            process_name="cmd.exe",
            executable_path=r"C:\WINDOWS\System32\cmd.exe",
            command_line=r'"C:\WINDOWS\System32\cmd.exe" /C openclaw-launch && "C:\Users\jncr0\AppData\Local\Programs\Ollama\ollama app.exe"',
            started_at_utc=datetime(2026, 4, 15, 20, 14, 0, tzinfo=UTC),
        )
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    observed = next(row for row in snapshot["observed_runtime"] if row["pid"] == 7201)

    assert observed["identity_status"] == "uncertain"
    assert observed["matched_identity"] == "uncertain"
    assert "competing identity signals" in observed["identity_basis"]
    assert set(observed["identity_candidates"]) >= {"OpenClaw", "Ollama app launcher"}


def test_operator_table_contains_identity_disclosure_columns() -> None:
    capture = _capture(
        CapturedProcessRow(
            pid=7301,
            parent_pid=500,
            process_name="powershell.exe",
            executable_path=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe",
            command_line=r'powershell -File C:\Calyx_Terminal\Scripts\station_health_loop.ps1',
            started_at_utc=datetime(2026, 4, 15, 20, 15, 0, tzinfo=UTC),
        )
    )

    snapshot = build_runtime_topology_snapshot(repo_root=Path("C:/Calyx_Terminal"), capture=capture)
    row = snapshot["operator_runtime_table"][0]

    assert row["pid"] == 7301
    assert row["matched_identity"] == "PowerShell station health loop"
    assert row["identity_status"] == "named"
    assert row["service_family"] == "station_health_loop"
    assert row["authority_posture"] == "authoritative"
