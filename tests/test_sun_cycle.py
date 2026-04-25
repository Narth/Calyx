from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tools.sun_cycle import (
    assess_boot_guard,
    build_sunrise_record,
    sha256_path,
    validate_sun_cycle_record,
)


ROOT = Path(__file__).resolve().parents[1]


def test_build_sunrise_record_is_schema_valid() -> None:
    record = build_sunrise_record(
        ROOT,
        node_id="cloud-cbo",
        correlation_id="sunrise-test",
        ts_utc="2026-04-25T16:49:00Z",
        reason="unknown",
        next_phase="cbo_operational_readiness",
    )

    errors = validate_sun_cycle_record(record)

    assert errors == []
    assert record["reason"] == "unknown"
    assert record["next_intended_boot_phase"] == "cbo_operational_readiness"
    assert record["station_state_snapshot"]["repo_roots_present"] == [str(ROOT)]


def test_boot_guard_blocks_low_battery_without_ac() -> None:
    record = build_sunrise_record(
        ROOT,
        node_id="cloud-cbo",
        correlation_id="sunrise-test",
        ts_utc="2026-04-25T16:49:00Z",
        reason="unknown",
        next_phase="cbo_operational_readiness",
        energy={
            "power_line_status": "offline",
            "battery_charge_status": "discharging",
            "battery_life_percent": 12.0,
            "battery_life_remaining": None,
        },
    )

    report = assess_boot_guard(
        record,
        {"sunrise_min_battery_percent": 25, "ac_required": False},
    )

    assert report["status"] == "blocked"
    assert "battery_below_sunrise_min" in report["checks"]


def test_hash_file_uses_sha256(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("calyx", encoding="utf-8")

    assert sha256_path(target) == hashlib.sha256(b"calyx").hexdigest()


def test_cli_writes_sunrise_and_report(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.sun_cycle",
            "--root",
            str(ROOT),
            "sunrise",
            "--node-id",
            "cloud-cbo",
            "--correlation-id",
            "sunrise-cli-test",
            "--out-dir",
            str(tmp_path / "telemetry" / "sun_cycle"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    sunrise_path = Path(output["record_path"])
    report_path = Path(output["report_path"])

    assert sunrise_path.exists()
    assert report_path.exists()
    assert output["boot_guard"]["status"] == "allowed"

    sunrise = json.loads(sunrise_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert validate_sun_cycle_record(sunrise) == []
    assert report["sunrise_sha256"] == sha256_path(sunrise_path)
