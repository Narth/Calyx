"""
WO_VERIFIED_CLAIMS_LEDGER_V1 — Mandatory postcondition verification for side-effect claims.
Structured event class within the Station Event Ledger: claim.attempted, claim.verified, claim.failed.
"""
from __future__ import annotations

from typing import Any

from .event_ledger import emit as ledger_emit
from .event_ledger import get_corr_id


def _claim_data(
    claim_type: str,
    artifact_path: str | None = None,
    sha256: str | None = None,
    reason: str | None = None,
    corr_id: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"claim_type": claim_type}
    if artifact_path:
        data["artifact_path"] = str(artifact_path)[:512]
    if sha256:
        data["sha256"] = str(sha256)[:64]
    if reason:
        data["reason"] = str(reason)[:500]
    cid = corr_id or get_corr_id() or ""
    if cid:
        data["corr_id"] = cid[:64]
    return data


def emit_claim_attempted(
    claim_type: str,
    *,
    artifact_path: str | None = None,
    corr_id: str | None = None,
) -> None:
    """Emit claim.attempted. Never throws."""
    try:
        ledger_emit(
            level="INFO",
            component="cbo",
            event="claim.attempted",
            msg=f"Claim attempted: {claim_type}",
            data=_claim_data(claim_type, artifact_path=artifact_path, corr_id=corr_id),
            corr_id=corr_id,
        )
    except Exception:
        pass


def emit_claim_verified(
    claim_type: str,
    *,
    artifact_path: str | None = None,
    sha256: str | None = None,
    corr_id: str | None = None,
) -> None:
    """Emit claim.verified. Never throws."""
    try:
        ledger_emit(
            level="INFO",
            component="cbo",
            event="claim.verified",
            msg=f"Claim verified: {claim_type}",
            data=_claim_data(claim_type, artifact_path=artifact_path, sha256=sha256, corr_id=corr_id),
            corr_id=corr_id,
        )
    except Exception:
        pass


def emit_claim_failed(
    claim_type: str,
    reason: str,
    *,
    artifact_path: str | None = None,
    corr_id: str | None = None,
) -> None:
    """Emit claim.failed. Never throws."""
    try:
        ledger_emit(
            level="WARN",
            component="cbo",
            event="claim.failed",
            msg=f"Claim failed: {claim_type} — {reason[:200]}",
            data=_claim_data(claim_type, reason=reason, artifact_path=artifact_path, corr_id=corr_id),
            corr_id=corr_id,
        )
    except Exception:
        pass
