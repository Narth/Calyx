"""
Post-run verifier for autonomous execution benchmark suite.
Phase 3C: Confirms total_cases_completed, execution_log_hash, sandbox hashes, no .tmp.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .execution_log import compute_execution_log_hash


def verify_run(
    envelope_data: dict,
    log_path: Path,
    sandbox_root: Path,
    expected_cases: int,
    runtime_root: Path,
) -> dict[str, Any]:
    """
    Post-run verification. Returns verification result with pass/fail per check.
    """
    log_path = Path(log_path)
    sandbox_root = Path(sandbox_root)
    runtime_root = Path(runtime_root)

    results: dict[str, Any] = {
        "total_cases_completed": {"pass": False, "expected": expected_cases, "actual": None},
        "execution_log_hash": {"pass": False, "expected": None, "actual": None},
        "sandbox_hashes_recorded": {"pass": False},
        "no_tmp_remains": {"pass": False, "found": []},
        "schema_version_valid": {"pass": False, "actual": None},
    }
    schema = envelope_data.get("schema_version", "")
    results["schema_version_valid"]["actual"] = schema
    results["schema_version_valid"]["pass"] = schema in ("1.2", "1.3", "1.4")

    # 1.4: compaction metrics consistency (when schema 1.4)
    results["compaction_metrics_consistent"] = {"pass": True}
    if schema == "1.4":
        metrics = envelope_data.get("metrics") or {}
        for key in ("compaction_applied_count", "compaction_rate", "dropped_action_count", "compaction_token_savings_est"):
            if key not in metrics:
                results["compaction_metrics_consistent"]["pass"] = False
                break

    # 2. total_cases_completed == expected
    actual_completed = envelope_data.get("total_cases_completed", 0)
    results["total_cases_completed"]["actual"] = actual_completed
    results["total_cases_completed"]["pass"] = actual_completed == expected_cases

    # 3. execution_log_hash matches file
    stored_hash = envelope_data.get("execution_log_hash", "")
    if log_path.exists():
        computed_hash = compute_execution_log_hash(log_path)
        results["execution_log_hash"]["expected"] = computed_hash
        results["execution_log_hash"]["actual"] = stored_hash
        results["execution_log_hash"]["pass"] = stored_hash == computed_hash
    else:
        results["execution_log_hash"]["pass"] = False

    # 4. sandbox hashes recorded
    before_hash = envelope_data.get("sandbox_state_hash_before", "")
    after_hash = envelope_data.get("sandbox_state_hash_after", "")
    results["sandbox_hashes_recorded"]["pass"] = bool(before_hash or after_hash)

    # 5. no .tmp remains under runtime
    tmp_files: list[Path] = []
    for p in runtime_root.rglob("*.tmp"):
        if p.is_file():
            tmp_files.append(p)
    results["no_tmp_remains"]["found"] = [str(p) for p in tmp_files]
    results["no_tmp_remains"]["pass"] = len(tmp_files) == 0

    all_pass = all(
        r.get("pass", False)
        for r in results.values()
        if isinstance(r, dict) and "pass" in r
    )
    results["overall"] = {"pass": all_pass}

    return results
