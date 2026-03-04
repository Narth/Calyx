"""
Phase F: CI invariant penetration tests.
Assert that importing from archive or station_calyx in active code is caught.
"""
from __future__ import annotations

import os
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
