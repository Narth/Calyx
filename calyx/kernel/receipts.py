"""Canonical receipt writer. Schema validation enforced."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import resolve_receipts_dir, resolve_repo_root

# Minimal required keys for a valid receipt (schema enforcement)
REQUIRED_RECEIPT_KEYS = frozenset({"timestamp_utc", "phase", "status", "receipt_type"})


def _validate_receipt_payload(payload: dict[str, Any]) -> None:
    """Raise ValueError if payload missing required keys."""
    missing = REQUIRED_RECEIPT_KEYS - set(payload)
    if missing:
        raise ValueError(f"Receipt missing required keys: {missing}")


def write_receipt(
    payload: dict[str, Any],
    prefix: str = "spine",
    repo_root: Path | None = None,
) -> Path:
    """
    Write a canonical receipt. Payload must include timestamp_utc, phase, status, receipt_type.
    Returns path to written receipt file.
    """
    _validate_receipt_payload(payload)
    receipts_dir = resolve_receipts_dir(repo_root)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"{prefix}__{ts}.json"
    path = receipts_dir / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def append_receipt_line(
    payload: dict[str, Any],
    prefix: str = "spine",
    repo_root: Path | None = None,
) -> Path:
    """
    Append a single JSON line to a receipt file (JSONL). Same validation as write_receipt.
    """
    _validate_receipt_payload(payload)
    receipts_dir = resolve_receipts_dir(repo_root)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"{prefix}__{ts}.jsonl"
    path = receipts_dir / name
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def resolve_governance_receipts_dir(repo_root: Path | None = None) -> Path:
    """Governance receipts directory: runtime/receipts/governance/."""
    return resolve_receipts_dir(repo_root) / "governance"


def write_governance_receipt(
    payload: dict[str, Any],
    wo_id: str,
    repo_root: Path | None = None,
) -> Path:
    """
    Write a governance receipt to runtime/receipts/governance/{wo_id}__{timestamp}.json.
    Payload must include wo_id, commit_sha, files_changed, tests_passed, ledger_schema_hash,
    policy_hashes, deny_reasons_count, relaxation_applied.
    """
    gov_dir = resolve_governance_receipts_dir(repo_root)
    gov_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"{wo_id}__{ts}.json"
    path = gov_dir / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path
