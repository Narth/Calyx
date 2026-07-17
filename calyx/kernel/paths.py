"""Canonical runtime path resolution. No I/O beyond existence checks."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_repo_root(anchor: Path | str | None = None) -> Path:
    """
    Resolve repository root. Uses CALYX_REPO_ROOT if set, else walks up from anchor
    to find a directory containing CALYX_CONTRACT.yaml or .git.
    """
    if anchor is None:
        anchor = Path.cwd()
    root = Path(anchor).resolve()
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    for _ in range(20):
        if (root / "CALYX_CONTRACT.yaml").exists() or (root / ".git").exists():
            return root
        parent = root.parent
        if parent == root:
            break
        root = parent
    return Path(anchor).resolve()


def resolve_runtime_dir(repo_root: Path | None = None) -> Path:
    """Canonical runtime directory (e.g. runtime/)."""
    root = repo_root or resolve_repo_root()
    env_runtime = os.environ.get("CALYX_RUNTIME_DIR")
    if env_runtime:
        return Path(env_runtime).resolve()
    return (root / "runtime").resolve()


def resolve_receipts_dir(repo_root: Path | None = None) -> Path:
    """Canonical receipts directory under runtime."""
    return resolve_runtime_dir(repo_root) / "receipts"


def resolve_intents_dir(repo_root: Path | None = None) -> Path:
    """Canonical intents directory under runtime/cbo/intents."""
    return resolve_runtime_dir(repo_root) / "cbo" / "intents"


def resolve_manifests_dir(repo_root: Path | None = None) -> Path:
    """Canonical manifests directory under runtime."""
    return resolve_runtime_dir(repo_root) / "manifests"


def resolve_perf_receipts_dir(repo_root: Path | None = None) -> Path:
    """Performance receipts directory: runtime/receipts/perf/."""
    return resolve_receipts_dir(repo_root) / "perf"


def resolve_ledger_dir(repo_root: Path | None = None) -> Path:
    """Canonical ledger directory: runtime/ledger/."""
    return resolve_runtime_dir(repo_root) / "ledger"
