"""
Policy validators: tripwire, competitor_clause. Deny-by-default on malformed.
Stdlib only. No external deps.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

TRIPWIRE_REQUIRED = frozenset({"current_level", "last_decision", "reason"})
TRIPWIRE_DECISIONS = frozenset({"allow", "warn", "deny"})
COMPETITOR_REQUIRED = frozenset({"expiry", "max_relaxation_cap"})


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Load YAML. Returns (data, error)."""
    if yaml is None:
        return None, "PyYAML required; pip install pyyaml"
    if not path.exists():
        return None, f"file not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return None, f"parse error: {e}"
    if not isinstance(data, dict):
        return None, "root must be dict"
    return data, ""


def validate_tripwire(path: Path | None = None, repo_root: Path | None = None) -> tuple[str, str]:
    """
    Validate tripwire_levels.yaml. Returns (decision, reason).
    decision: allow | warn | deny
    Deny-by-default on malformed.
    """
    if path is None:
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[1]
        path = repo_root / "policy" / "tripwire_levels.yaml"

    data, err = _load_yaml(path)
    if data is None:
        return "deny", f"deny_by_default: {err}"

    levels = data.get("tripwire_levels")
    if not isinstance(levels, dict):
        return "deny", "deny_by_default: tripwire_levels must be dict"

    missing = TRIPWIRE_REQUIRED - set(levels)
    if missing:
        return "deny", f"deny_by_default: missing required keys: {missing}"

    decision = str(levels.get("last_decision", "")).strip().lower()
    if decision not in TRIPWIRE_DECISIONS:
        return "deny", f"deny_by_default: invalid last_decision: {decision}"

    reason = levels.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return "deny", "deny_by_default: reason must be non-empty string"

    level = levels.get("current_level", 1)
    if level == 3:
        return "deny", reason
    if level == 2:
        return "warn", reason
    return "allow", reason


def validate_competitor_clause(
    path: Path | None = None,
    repo_root: Path | None = None,
    *,
    relaxation_occurred: bool = False,
    receipt_has_relaxation_applied: bool = False,
) -> tuple[bool, str]:
    """
    Validate competitor_clause.yaml. Returns (ok, reason).
    Rejects missing expiry or max_relaxation_cap.
    If relaxation_occurred and not receipt_has_relaxation_applied -> deny.
    """
    if path is None:
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[1]
        path = repo_root / "policy" / "competitor_clause.yaml"

    data, err = _load_yaml(path)
    if data is None:
        return False, f"deny_by_default: {err}"

    clause = data.get("competitor_clause")
    if not isinstance(clause, dict):
        return False, "deny_by_default: competitor_clause must be dict"

    missing = COMPETITOR_REQUIRED - set(clause)
    if missing:
        return False, f"deny_by_default: missing required keys: {missing}"

    if relaxation_occurred and not receipt_has_relaxation_applied:
        return False, "deny_by_default: relaxation occurred but relaxation_applied not set in receipt"

    return True, ""


def check_tripwire(path: Path | None = None, repo_root: Path | None = None) -> tuple[str, str]:
    """Alias for validate_tripwire. Returns (allow|warn|deny, reason)."""
    return validate_tripwire(path=path, repo_root=repo_root)
