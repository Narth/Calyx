from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / ".github" / "scripts" / "generate_hub_runner_ci_receipt.py"
CHECKER_PATH = ROOT / ".github" / "scripts" / "check_receipts.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_receipt_checker_requires_current_pr_probe(tmp_path: Path) -> None:
    checker = _load(CHECKER_PATH, "check_receipts")
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    (receipts / "hub_runner__unrelated.jsonl").write_text(
        json.dumps(
            {
                "timestamp_utc": "2026-07-16T00:00:00+00:00",
                "phase": "validate",
                "status": "allowed",
                "receipt_type": "hub_runner",
                "envelope_id": "ci-pr-6-hub-runner-receipt",
                "reason": "swarm_validate_only_phase2",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert checker.check_receipts(7, receipts) is False


def test_generator_emits_receipt_accepted_by_checker(tmp_path: Path) -> None:
    generator = _load(GENERATOR_PATH, "generate_hub_runner_ci_receipt")
    checker = _load(CHECKER_PATH, "check_receipts_generated")
    runtime_dir = tmp_path / "runtime"

    receipt_path = generator.generate_probe_receipt(
        7,
        repo_root=ROOT,
        runtime_dir=runtime_dir,
    )

    assert receipt_path.parent == runtime_dir / "receipts"
    assert checker.check_receipts(7, receipt_path.parent) is True


def test_generator_cli_imports_repository_from_any_working_directory(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--pr-number",
            "7",
            "--repo-root",
            str(ROOT),
            "--runtime-dir",
            str(runtime_dir),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Hub Runner CI validation receipt:" in result.stdout
