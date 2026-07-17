"""Node identity and node-scoped paths for federated benchmarking."""
from __future__ import annotations

from pathlib import Path


def get_node_id(runtime_root: Path) -> str | None:
    """Read node_id from runtime/node_id.txt. Returns None if absent."""
    p = Path(runtime_root) / "node_id.txt"
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def get_results_dir(benchmarks_root: Path, suite_id: str, runtime_root: Path) -> Path:
    """
    Return node-scoped results directory when node_id exists:
    runtime/benchmarks/results/<suite>/<node_id>/
    Otherwise: runtime/benchmarks/results/<suite>/
    """
    base = Path(benchmarks_root) / "results" / suite_id
    node_id = get_node_id(Path(runtime_root))
    if node_id:
        return base / node_id
    return base
