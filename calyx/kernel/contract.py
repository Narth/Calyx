"""Load CALYX_CONTRACT.yaml and validate Work Envelopes. Deny-by-default.

WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1: Contract integrity
enforcement. If contract_sha256 is non-empty, it must match canonical hash or load fails.
"""

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


def _canonical_contract_hash(data: dict) -> str:
    """Compute sha256 of contract dict excluding contract_sha256. Deterministic."""
    excluded = {k: v for k, v in data.items() if k != "contract_sha256"}
    canonical = yaml.dump(excluded, sort_keys=True, default_flow_style=False, allow_unicode=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _emit_audit(event: str, data: dict | None = None) -> None:
    try:
        from .event_ledger import emit
        emit(level="WARN", component="contract", event=event, msg=event, data=data or {})
    except Exception:
        pass


def load_contract(contract_path: Path | str) -> tuple[dict, str]:
    """
    Load CALYX_CONTRACT.yaml. Returns (contract_dict, contract_sha256).
    If contract_sha256 is non-empty in file, enforces integrity (fail closed on mismatch).
    Raises if file missing, invalid, or integrity check fails.
    """
    path = Path(contract_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract not found: {path}")
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("Contract must be a YAML mapping")

    declared_hash = (data.get("contract_sha256") or "").strip()
    actual_hash = _canonical_contract_hash(data)

    if declared_hash:
        if declared_hash != actual_hash:
            _emit_audit("audit.contract.integrity.failed", {
                "declared": declared_hash[:16] + "...",
                "actual": actual_hash[:16] + "...",
                "path": str(path),
            })
            raise ValueError(
                f"Contract integrity failed: declared hash does not match. "
                f"Tampering or drift detected. Path: {path}"
            )

    return data, actual_hash


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

    swarm_valid, swarm_errors = envelope.validate_swarm_extensions()
    if not swarm_valid:
        return False, "invalid_swarm_extension: " + "; ".join(swarm_errors)

    return True, None


def get_tool_allowlist(contract: dict, task_type: str) -> list[str]:
    """Return list of allowed tools for task_type from contract tool_surface."""
    surface = (contract.get("tool_surface") or {}).get(task_type) or {}
    return list(surface.get("allowed_tools") or [])
