"""
WO_CANONICAL_RESPONSE_HASH_V1 — Canonical response bundle builder.
Builds crh.v1 schema bundles for cross-channel and cross-node parity checking.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical_hash import sha256_hex
from .canonical_json import canonical_dumps


# WO_CANONICAL_EQUIVALENCE_HASH_V2: stable subset for parity (excludes ts_utc, corr_id, request_id, entry_point)
STABLE_POLICY_KEYS = ("governance_required", "canonical_response_mode", "fastpath_used", "tooling_allowed")


def build_equivalence_bundle(
    *,
    intent: str,
    normalized_request_sha256: str,
    evidence: list[dict[str, str]],
    policy_flags: dict[str, bool],
    response_sha256: str,
    node_id: str = "unknown",
    auth_verified: bool = True,
    signer_fingerprint: str = "",
) -> dict[str, Any]:
    """
    Build equivalence bundle (stable fields only). Used for cross-channel parity.
    Excludes: ts_utc, corr_id, request_id, entry_point.
    WO_EQUIVALENCE_SCOPE_V3: includes auth_verified, signer_fingerprint.
    """
    evidence_sorted = sorted(evidence, key=lambda e: (e.get("kind", ""), e.get("path", "")))
    stable_flags = {k: policy_flags[k] for k in STABLE_POLICY_KEYS if k in policy_flags}
    bundle: dict[str, Any] = {
        "schema": "crh.equiv.v2",
        "intent": intent,
        "normalized_request_sha256": normalized_request_sha256,
        "evidence": evidence_sorted,
        "policy_flags": stable_flags,
        "response_sha256": response_sha256,
        "node_id": node_id,
        "auth_verified": auth_verified,
        "signer_fingerprint": "governed" if auth_verified else (signer_fingerprint or "ungoverned"),
    }
    equiv_str = canonical_dumps(bundle)
    bundle["equivalence_hash_sha256"] = sha256_hex(equiv_str)
    return bundle


def build_canonical_bundle(
    *,
    ts_utc: str,
    corr_id: str,
    request_id: str | None = None,
    entry_point: str,
    node_id: str,
    intent: str,
    normalized_request: str,
    evidence: list[dict[str, str]],
    policy_flags: dict[str, bool],
    response_text: str,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """
    Build crh.v1 canonical bundle. Evidence must be sorted by (kind, path).
    Returns bundle dict; caller computes canonical_hash_sha256 via finalize_bundle().
    """
    norm_req_sha = sha256_hex(normalized_request)
    resp_sha = sha256_hex(response_text)
    evidence_sorted = sorted(evidence, key=lambda e: (e.get("kind", ""), e.get("path", "")))
    bundle: dict[str, Any] = {
        "schema": "crh.v1",
        "ts_utc": ts_utc,
        "corr_id": corr_id,
        "request_id": request_id or corr_id,
        "entry_point": entry_point,
        "node_id": node_id,
        "intent": intent,
        "normalized_request": normalized_request,
        "normalized_request_sha256": norm_req_sha,
        "evidence": evidence_sorted,
        "policy_flags": policy_flags,
        "response_sha256": resp_sha,
    }
    canonical_str = canonical_dumps(bundle)
    bundle["canonical_hash_sha256"] = sha256_hex(canonical_str)
    return bundle


def hash_file_content(path: Path) -> str:
    """SHA-256 of file content. Returns empty string on error."""
    try:
        if path.exists() and path.is_file():
            return sha256_hex(path.read_bytes())
    except Exception:
        pass
    return ""


def evidence_state(path: str, repo_root: Path) -> dict[str, str]:
    """Evidence entry for STATE.md."""
    p = repo_root / path
    return {"kind": "state", "path": path, "sha256": hash_file_content(p)}


def evidence_file(path: str, repo_root: Path) -> dict[str, str]:
    """Evidence entry for a file."""
    p = repo_root / path
    return {"kind": "file", "path": path, "sha256": hash_file_content(p)}


def evidence_repo_hit(path: str, repo_root: Path) -> dict[str, str]:
    """Evidence entry for repo_search top hit. Path may be absolute or relative."""
    p = Path(path.replace("\\", "/"))
    if p.is_absolute() and str(repo_root) in str(p):
        try:
            rel = p.relative_to(repo_root).as_posix()
        except ValueError:
            rel = path.replace("\\", "/")
    else:
        rel = path.replace("\\", "/").lstrip("/")
        p = repo_root / rel
    return {"kind": "repo_hit", "path": rel, "sha256": hash_file_content(p)}
