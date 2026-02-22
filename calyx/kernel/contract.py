"""Load CALYX_CONTRACT.yaml and validate Work Envelopes. Deny-by-default."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .envelope import WorkEnvelope

try:
    import yaml
except ImportError:
    yaml = None


def _load_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML required for contract load; pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_contract(contract_path: Path | str) -> tuple[dict, str]:
    """
    Load CALYX_CONTRACT.yaml. Returns (contract_dict, contract_sha256).
    Raises if file missing or invalid.
    """
    path = Path(contract_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract not found: {path}")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("Contract must be a YAML mapping")
    return data, sha


def validate_work_envelope(
    envelope: WorkEnvelope,
    contract: dict,
    contract_sha256: str,
    phase: str = "phase_a",
) -> tuple[bool, str | None]:
    """
    Validate a Work Envelope against the contract. Deny-by-default.
    Returns (allowed: bool, denial_reason: str | None). If allowed, reason is None.
    """
    allowed_tasks = contract.get("allowed_tasks") or []
    if envelope.task_type not in allowed_tasks:
        return False, f"task_type '{envelope.task_type}' not in allowed_tasks"

    allowed_sources = (contract.get("allowed_sources") or {}).get(phase) or []
    if envelope.source not in allowed_sources:
        return False, f"source '{envelope.source}' not in allowed_sources for {phase}"

    scope_paths = envelope.scope.get("paths") or []
    governance_paths = ["governance/", "CALYX_CONTRACT.yaml", ".github/workflows/"]
    if any(p.startswith(tuple(governance_paths)) for p in scope_paths):
        if not envelope.requires_human_approval or not envelope.approval_token:
            return False, "policy_governance_edit_without_approval"

    if envelope.risk_tier == "high":
        if not envelope.requires_human_approval or not envelope.approval_token:
            return False, "high_risk_without_approval_token"

    return True, None


def get_tool_allowlist(contract: dict, task_type: str) -> list[str]:
    """Return list of allowed tools for task_type from contract tool_surface."""
    surface = (contract.get("tool_surface") or {}).get(task_type) or {}
    return list(surface.get("allowed_tools") or [])
