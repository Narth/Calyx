"""Calyx kernel: minimal stable core for envelope, contract, receipts, toolsurface, paths."""

from __future__ import annotations

from .paths import resolve_repo_root, resolve_runtime_dir, resolve_receipts_dir
from .envelope import WorkEnvelope
from .contract import load_contract, validate_work_envelope, get_tool_allowlist
from .integrity_gate import (
    check_integrity,
    gate_before_action,
    acquire_coordinator_lease,
    spine_operation_lease,
    SystemIntegrityError,
)
from .receipts import write_receipt
from .toolsurface import check_tool_allowed

__all__ = [
    "check_integrity",
    "gate_before_action",
    "resolve_repo_root",
    "resolve_runtime_dir",
    "resolve_receipts_dir",
    "WorkEnvelope",
    "load_contract",
    "validate_work_envelope",
    "get_tool_allowlist",
    "write_receipt",
    "check_tool_allowed",
    "SystemIntegrityError",
]
