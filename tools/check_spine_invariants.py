#!/usr/bin/env python3
"""
Spine invariant checks for CI.
- Fails if any active code (outside archive/) imports non-existent namespaces (e.g. station_calyx.core).
- Fails if new top-level directories exist without being documented in docs/INDEX.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def repo_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root


def check_forbidden_imports(root: Path) -> list[str]:
    """Find .py files outside archive/ that import station_calyx or archive."""
    forbidden = []
    archive_dir = root / "archive"
    # Only scan active code roots (avoid .git, node_modules, etc.)
    exclude_paths = {root / "tools" / "check_spine_invariants.py"}
    for subdir in ["calyx", "tools", "benchmarks", "station_calyx", "scripts", "Scripts"]:
        scan = root / subdir
        if not scan.exists():
            continue
        for py_path in scan.rglob("*.py"):
            if py_path in exclude_paths:
                continue
            if archive_dir in py_path.parents:
                continue
            try:
                text = py_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if re.search(r"(?:from\s+station_calyx|import\s+station_calyx)", text):
                rel = py_path.relative_to(root)
                forbidden.append(str(rel))
            if re.search(r"(?:from\s+archive\.|import\s+archive\b)", text):
                rel = py_path.relative_to(root)
                forbidden.append(str(rel) + " (imports archive)")
    return forbidden


def documented_top_level_dirs(root: Path) -> set[str]:
    """Extract top-level directory names that appear in docs/INDEX.md."""
    index_path = root / "docs" / "INDEX.md"
    if not index_path.exists():
        return set()
    text = index_path.read_text(encoding="utf-8", errors="replace")
    # Match paths like calyx/, docs/, bloomos/, tools/, etc.
    first_components = set()
    for line in text.splitlines():
        # Look for path-like tokens (word chars, then /)
        for m in re.finditer(r"([a-zA-Z_][a-zA-Z0-9_]*)/", line):
            first_components.add(m.group(1))
        # Also paths in backticks or after -
        for m in re.finditer(r"`([a-zA-Z_][a-zA-Z0-9_]*)/", line):
            first_components.add(m.group(1))
    return first_components


def actual_top_level_dirs(root: Path) -> list[str]:
    """List top-level directories in repo (excluding hidden and standard)."""
    allowed_skip = {".git", ".github", ".venv", "venv", "node_modules", "__pycache__"}
    dirs = []
    for p in root.iterdir():
        if p.is_dir() and p.name not in allowed_skip and not p.name.startswith("."):
            dirs.append(p.name)
    return sorted(dirs)


def check_top_level_documented(root: Path) -> list[str]:
    """Return list of top-level dirs not documented in INDEX.md."""
    documented = documented_top_level_dirs(root)
    actual = actual_top_level_dirs(root)
    undocumented = [d for d in actual if d not in documented]
    return undocumented


def main() -> int:
    root = repo_root()
    exit_code = 0

    # 1. Forbidden imports
    forbidden = check_forbidden_imports(root)
    if forbidden:
        print("SPINE CHECK FAILED: Active code must not import missing/archived namespaces.")
        print("Files importing 'station_calyx' (move to archive/ or remove import):")
        for f in forbidden:
            print(f"  - {f}")
        exit_code = 1
    else:
        print("OK: No forbidden namespace imports in active code.")

    # 2. Top-level dirs documented in INDEX.md
    undocumented = check_top_level_documented(root)
    if undocumented:
        print("SPINE CHECK FAILED: All top-level directories must be documented in docs/INDEX.md.")
        print("Undocumented top-level directories:", undocumented)
        exit_code = 1
    else:
        print("OK: All top-level directories documented in docs/INDEX.md.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
