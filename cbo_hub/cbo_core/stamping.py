"""
Sponsorship stamping — verify Calyx Sign sponsorship before stamped operations.

Per docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md: CBO may stamp operations
within sponsored scope when the Architect-signed sponsorship artifact is present
and valid. Escalate when a decision requires Architect input.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import NamedTuple


class SponsorshipResult(NamedTuple):
    """Result of sponsorship verification."""
    valid: bool
    reason: str
    proposal_id: str = "cbo_sponsorship_research_test_improve"


def _resolve_repo_root() -> Path:
    """Resolve repo root (same logic as calyx.kernel.paths)."""
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    anchor = Path(__file__).resolve().parents[2]  # cbo_hub/cbo_core -> repo
    root = anchor
    for _ in range(20):
        if (root / "CALYX_CONTRACT.yaml").exists() or (root / ".git").exists():
            return root
        parent = root.parent
        if parent == root:
            break
        root = parent
    return anchor


def check_sponsorship(
    repo_root: Path | None = None,
    *,
    verify_signature: bool = True,
) -> SponsorshipResult:
    """
    Check if CBO sponsorship is in effect (Architect-signed artifact present and valid).

    Args:
        repo_root: Repo root; resolved if None.
        verify_signature: If True, run ssh-keygen -Y verify. If False, only check .sig exists and is non-empty.

    Returns:
        SponsorshipResult(valid=True, ...) if sponsorship is in effect; else (valid=False, reason="...").
    """
    root = repo_root or _resolve_repo_root()
    proposal_id = "cbo_sponsorship_research_test_improve"
    approval_path = root / "governance" / "approvals" / f"{proposal_id}.approval.json"
    sig_path = root / "governance" / "approvals" / f"{proposal_id}.approval.json.sig"
    allowed_signers = root / "governance" / "identities" / "allowed_signers"

    if not sig_path.exists():
        return SponsorshipResult(valid=False, reason="sponsorship_sig_missing", proposal_id=proposal_id)
    if sig_path.stat().st_size == 0:
        return SponsorshipResult(valid=False, reason="sponsorship_sig_empty", proposal_id=proposal_id)

    if not verify_signature:
        return SponsorshipResult(valid=True, reason="sponsorship_sig_present", proposal_id=proposal_id)

    if not approval_path.exists():
        return SponsorshipResult(valid=False, reason="approval_json_missing", proposal_id=proposal_id)
    if not allowed_signers.exists():
        return SponsorshipResult(valid=False, reason="allowed_signers_missing", proposal_id=proposal_id)

    try:
        with open(approval_path, "rb") as f:
            content = f.read()
        result = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(allowed_signers),
                "-I", "architect",
                "-n", "calyx",
                "-s", str(sig_path),
            ],
            input=content,
            capture_output=True,
            timeout=5,
            cwd=str(root),
        )
        if result.returncode == 0:
            return SponsorshipResult(valid=True, reason="sponsorship_verified", proposal_id=proposal_id)
        err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        return SponsorshipResult(valid=False, reason=f"signature_verify_failed:{err[:200]}", proposal_id=proposal_id)
    except FileNotFoundError:
        return SponsorshipResult(valid=False, reason="ssh_keygen_not_found", proposal_id=proposal_id)
    except subprocess.TimeoutExpired:
        return SponsorshipResult(valid=False, reason="signature_verify_timeout", proposal_id=proposal_id)
    except Exception as e:
        return SponsorshipResult(valid=False, reason=f"sponsorship_check_error:{str(e)[:100]}", proposal_id=proposal_id)


def require_sponsorship_for_stamped_op(
    operation: str,
    repo_root: Path | None = None,
) -> None:
    """
    Raise if sponsorship is not valid. Call before any stamped operation (file write, script run within scope).

    Raises:
        PermissionError: If sponsorship is not in effect.
    """
    res = check_sponsorship(repo_root=repo_root)
    if not res.valid:
        raise PermissionError(
            f"Stamped operation '{operation}' denied: sponsorship not in effect ({res.reason}). "
            "CBO must escalate to Architect for approval. See docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md."
        )
