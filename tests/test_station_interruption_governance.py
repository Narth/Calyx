from __future__ import annotations

import json
import os
import subprocess
import textwrap
import shutil
import uuid
from pathlib import Path

import pytest


POWERSHELL = r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe"
REPO_ROOT = Path(__file__).resolve().parents[1]
TRUTH_HELPER = REPO_ROOT / "Scripts" / "runtime_truth_contract.ps1"


pytestmark = pytest.mark.skipif(os.name != "nt", reason="PowerShell lifecycle tests require Windows")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def local_repo():
    repo = REPO_ROOT / f"pytest_station_lifecycle_{uuid.uuid4().hex}"
    repo.mkdir(parents=True, exist_ok=False)
    (repo / "runtime" / "receipts" / "audit").mkdir(parents=True, exist_ok=True)
    try:
        yield repo
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def _run_ps(script: str) -> str:
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_clean_shutdown_marker_creation(local_repo: Path) -> None:
    repo = local_repo
    script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $leaseSummary = @{{
            active_leases = @(
                [ordered]@{{
                    swarm_run_id = 'swarm-run-001'
                    work_envelope_id = 'env-001'
                    lease_id = 'lease-001'
                    worker_id = 'worker-01'
                    lease_state = 'approved'
                }}
            )
            in_flight_operations = @('swarm-run-001')
        }}
        $result = Emit-StationShutdownMarker -RepoRoot $repoRoot -Reason manual -ObservedAtUtc ([datetime]'2026-04-18T20:00:00Z') -ServiceSummary @('dev_harness','cbo_core') -LeaseSummary $leaseSummary
        $result | ConvertTo-Json -Compress
        """
    )
    result = json.loads(_run_ps(script))
    latest = Path(result["latest_path"])
    receipt = Path(result["receipt_path"])
    assert latest.exists()
    assert receipt.exists()
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["schema"] == "station.shutdown_marker.v1"
    assert payload["reason"] == "manual"
    assert payload["active_services"] == ["cbo_core", "dev_harness"]
    assert payload["active_lease_count"] == 1
    assert payload["in_flight_operations"] == ["swarm-run-001"]


def test_missing_shutdown_marker_is_classified_as_post_interruption_restart(local_repo: Path) -> None:
    repo = local_repo
    (repo / "STATE.md").write_text("Status: test\nheartbeat_ts: 2026-04-18T08:00:00Z\n", encoding="utf-8")
    _write_json(
        repo / "runtime" / "station_health.json",
        {
            "emitted_ts_utc": "2026-04-18T08:05:00Z",
            "health_ts": "2026-04-18T08:05:00Z",
            "truth_state": "fresh",
        },
    )
    host_script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $result = Emit-HostBootDetected -RepoRoot $repoRoot -ObservedAtUtc ([datetime]'2026-04-18T09:00:00Z') -HostBootUtc ([datetime]'2026-04-18T09:00:00Z')
        $result | ConvertTo-Json -Compress
        """
    )
    host_result = json.loads(_run_ps(host_script))
    host_payload = json.loads(Path(host_result["latest_path"]).read_text(encoding="utf-8"))
    assert host_payload["classification"] == "post_interruption_restart"
    assert "missing_clean_shutdown_marker" in host_payload["classification_reasons"]

    interruption_script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $result = Emit-StationUncleanInterruption -RepoRoot $repoRoot -ObservedAtUtc ([datetime]'2026-04-18T09:00:30Z') -HostBootUtc ([datetime]'2026-04-18T09:00:00Z')
        $result | ConvertTo-Json -Compress
        """
    )
    interruption_result = json.loads(_run_ps(interruption_script))
    interruption_payload = json.loads(Path(interruption_result["latest_path"]).read_text(encoding="utf-8"))
    assert interruption_payload["interruption_detected"] is True
    assert interruption_payload["inferred_interruption_window"]["start_after_utc"] == "2026-04-18T08:05:00.0000000Z"
    assert interruption_payload["inferred_interruption_window"]["end_at_or_before_utc"] == "2026-04-18T09:00:00.0000000Z"
    assert any(item["surface"] == "station_health.json" for item in interruption_payload["affected_surfaces"])


def test_clean_shutdown_marker_yields_normal_restart_classification(local_repo: Path) -> None:
    repo = local_repo
    _write_json(
        repo / "runtime" / "station_health.json",
        {
            "emitted_ts_utc": "2026-04-18T08:05:00Z",
            "health_ts": "2026-04-18T08:05:00Z",
            "truth_state": "fresh",
        },
    )
    _write_json(
        repo / "runtime" / "station_shutdown_marker.json",
        {
            "schema": "station.shutdown_marker.v1",
            "shutdown_ts_utc": "2026-04-18T08:06:00Z",
            "reason": "patch",
            "active_services": [],
            "active_service_count": 0,
            "active_leases": [],
            "active_lease_count": 0,
            "in_flight_operations": [],
            "in_flight_operation_count": 0,
        },
    )
    script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $result = Emit-HostBootDetected -RepoRoot $repoRoot -ObservedAtUtc ([datetime]'2026-04-18T09:00:00Z') -HostBootUtc ([datetime]'2026-04-18T09:00:00Z')
        $result | ConvertTo-Json -Compress
        """
    )
    result = json.loads(_run_ps(script))
    payload = json.loads(Path(result["latest_path"]).read_text(encoding="utf-8"))
    assert payload["classification"] == "normal_restart"
    assert payload["clean_shutdown_marker_present"] is True


def test_recovery_artifact_reports_services_ports_and_truth_surfaces(local_repo: Path) -> None:
    repo = local_repo
    (repo / "STATE.md").write_text("Status: test\nheartbeat_ts: 2026-04-18T10:00:00Z\nruntime_truth_state: fresh\n", encoding="utf-8")
    _write_json(
        repo / "runtime" / "station_heartbeat.json",
        {
            "emitted_ts_utc": "2026-04-18T10:00:00Z",
            "heartbeat_emitted_ts": "2026-04-18T10:00:00Z",
            "truth_state": "fresh",
        },
    )
    _write_json(
        repo / "runtime" / "service_runtime_snapshot.json",
        {
            "emitted_ts_utc": "2026-04-18T10:00:00Z",
            "heartbeat_emitted_ts": "2026-04-18T10:00:00Z",
            "truth_state": "fresh",
        },
    )
    _write_json(
        repo / "runtime" / "runtime_topology_snapshot.json",
        {
            "emitted_ts_utc": "2026-04-18T10:00:00Z",
            "truth_state": "fresh",
        },
    )
    script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $serviceStatuses = [ordered]@{{
            dev_harness = 'ok'
            cbo_core = 'ok'
            avatar_web = 'missing'
            telemetry_gateway = 'ok'
        }}
        $portStatuses = [ordered]@{{
            7777 = 'listening'
            7778 = 'listening'
            7780 = 'not_listening'
            7781 = 'listening'
        }}
        $result = Emit-StationRecoveryStatus -RepoRoot $repoRoot -ObservedAtUtc ([datetime]'2026-04-18T10:00:10Z') -StartExitCode 0 -ServiceStatuses $serviceStatuses -PortStatuses $portStatuses
        $result | ConvertTo-Json -Compress
        """
    )
    result = json.loads(_run_ps(script))
    payload = json.loads(Path(result["latest_path"]).read_text(encoding="utf-8"))
    assert payload["schema"] == "station.recovery_status.v1"
    assert payload["recovery_classification"] == "partial"
    assert payload["services"]["avatar_web"] == "missing"
    assert payload["port_bindings"]["7778"] == "listening"
    assert payload["topology_snapshot_available"] is True
    assert any(item["surface"] == "station_heartbeat.json" for item in payload["truth_surfaces"])


def test_missing_prior_state_is_handled_explicitly(local_repo: Path) -> None:
    repo = local_repo
    script = textwrap.dedent(
        f"""
        $repoRoot = '{repo}'
        . '{TRUTH_HELPER}'
        $result = Emit-StationUncleanInterruption -RepoRoot $repoRoot -ObservedAtUtc ([datetime]'2026-04-18T11:00:00Z') -HostBootUtc ([datetime]'2026-04-18T11:00:00Z')
        $result | ConvertTo-Json -Compress
        """
    )
    result = json.loads(_run_ps(script))
    payload = json.loads(Path(result["latest_path"]).read_text(encoding="utf-8"))
    assert payload["schema"] == "station.unclean_interruption.v1"
    assert payload["last_station_artifact_ts_utc"] == ""
    assert payload["affected_surfaces"] == []
