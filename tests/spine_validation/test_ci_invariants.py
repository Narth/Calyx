"""
Phase F: CI invariant penetration tests.
Assert that importing from archive or station_calyx in active code is caught.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_spine_invariant_script_forbidden_imports():
    """Active code must not import station_calyx or archive."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.check_spine_invariants import check_forbidden_imports
    forbidden = check_forbidden_imports(REPO_ROOT)
    assert forbidden == [], f"Forbidden imports in active code: {forbidden}"


def test_bloomos_not_imported_in_kernel_or_execution():
    """No bloomos imports in calyx/kernel or calyx/execution."""
    for subdir in ["calyx/kernel", "calyx/execution"]:
        dir_path = REPO_ROOT / subdir.replace("/", os.sep)
        if not dir_path.exists():
            continue
        for py in dir_path.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            assert "bloomos" not in text and "from bloomos" not in text and "import bloomos" not in text, (
                f"{py.relative_to(REPO_ROOT)} must not import bloomos"
            )


def test_spine_invariant_documents_all_tracked_top_level_dirs():
    from tools.check_spine_invariants import check_top_level_documented

    assert check_top_level_documented(REPO_ROOT) == []


def test_top_level_inventory_ignores_untracked_workspace_dirs(tmp_path, monkeypatch):
    from tools import check_spine_invariants

    (tmp_path / "local_only").mkdir()
    completed = subprocess.CompletedProcess(
        args=["git", "ls-files", "-z"],
        returncode=0,
        stdout=b"calyx/kernel/example.py\0docs/INDEX.md\0.github/workflows/ci.yml\0",
        stderr=b"",
    )
    monkeypatch.setattr(check_spine_invariants.subprocess, "run", lambda *args, **kwargs: completed)

    assert check_spine_invariants.actual_top_level_dirs(tmp_path) == ["calyx", "docs"]
