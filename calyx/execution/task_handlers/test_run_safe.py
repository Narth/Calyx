"""test_run_safe: fs_read, run_test_harness. Deterministic test run."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def execute_test_run_safe(
    envelope: dict[str, Any],
    contract: dict,
    repo_root: Path,
) -> tuple[bool, dict[str, Any], list[dict]]:
    """
    Execute safe test run. Returns (success, result_summary, receipts).
    Tools: fs_read, run_test_harness. Stub: no harness invocation yet.
    """
    receipts = []
    # Stub: would run pytest or harness within allowlist
    return True, {"status": "executed", "task": "test_run_safe", "stub": True}, receipts
