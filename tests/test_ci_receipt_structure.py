from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / ".github" / "scripts" / "validate_receipt_structure.py"
GENERATOR_PATH = ROOT / ".github" / "scripts" / "generate_ci_receipt.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_receipt_structure", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_receipt() -> dict:
    return {
        "timestamp_utc": "2026-07-16T20:00:00+00:00",
        "pr_number": 7,
        "risk_tier": "high",
        "ci_workflow": "code_factory_gates",
        "status": "completed",
    }


def test_validate_ci_receipt_accepts_canonical_shape() -> None:
    validator = _load_validator()

    assert validator.validate_ci_receipt(_valid_receipt(), expected_pr_number=7) == []


def test_validate_ci_receipt_rejects_missing_and_invalid_fields() -> None:
    validator = _load_validator()
    receipt = _valid_receipt()
    receipt.pop("status")
    receipt["timestamp_utc"] = "not-a-timestamp"
    receipt["pr_number"] = True
    receipt["risk_tier"] = "critical"

    errors = validator.validate_ci_receipt(receipt, expected_pr_number=7)

    assert any("missing required fields: status" in error for error in errors)
    assert any("timestamp_utc must be ISO-8601" in error for error in errors)
    assert any("pr_number must be a positive integer" in error for error in errors)
    assert any("risk_tier must be one of" in error for error in errors)


def test_validator_cli_exercises_real_generator() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR_PATH),
            "--pr-number",
            "7",
            "--generator",
            str(GENERATOR_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "validation passed" in result.stdout
