"""Phase II routing proof construction, validation, and persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUTING_PROOF_FIELDS = (
    "SELECTED_TOOL_PATH",
    "REJECTED_ALTERNATIVES",
    "SOURCE_TARGET_REQUIRED",
)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        candidates = []
    out: list[str] = []
    for item in candidates:
        text = _clean_text(item)
        if text and text not in out:
            out.append(text)
    return out


def build_routing_proof(
    *,
    selected_tool_path: str,
    rejected_alternatives: list[str] | tuple[str, ...],
    source_target_required: list[str] | tuple[str, ...],
    intent: str = "",
    entry_point: str = "",
    rationale: str = "",
    resolved_source_targets: list[str] | tuple[str, ...] | None = None,
    proof_id: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic routing proof payload."""
    return {
        "proof_id": _clean_text(proof_id) or "",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "intent": _clean_text(intent),
        "entry_point": _clean_text(entry_point),
        "SELECTED_TOOL_PATH": _clean_text(selected_tool_path),
        "REJECTED_ALTERNATIVES": _normalize_list(rejected_alternatives),
        "SOURCE_TARGET_REQUIRED": _normalize_list(source_target_required) or ["NONE"],
        "RESOLVED_SOURCE_TARGETS": _normalize_list(resolved_source_targets or []),
        "RATIONALE": _clean_text(rationale),
    }


def validate_routing_proof(proof: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return whether the routing proof is complete and which fields are missing."""
    missing: list[str] = []
    selected = _clean_text(proof.get("SELECTED_TOOL_PATH"))
    if not selected:
        missing.append("SELECTED_TOOL_PATH")
    rejected = _normalize_list(proof.get("REJECTED_ALTERNATIVES"))
    if not rejected:
        missing.append("REJECTED_ALTERNATIVES")
    required = _normalize_list(proof.get("SOURCE_TARGET_REQUIRED"))
    if not required:
        missing.append("SOURCE_TARGET_REQUIRED")
    return len(missing) == 0, missing


def source_targets_satisfied(proof: dict[str, Any]) -> bool:
    """True if all required source targets are resolved, or if proof explicitly needs none."""
    required = _normalize_list(proof.get("SOURCE_TARGET_REQUIRED"))
    if not required or required == ["NONE"]:
        return True
    resolved = set(_normalize_list(proof.get("RESOLVED_SOURCE_TARGETS")))
    for target in required:
        if target not in resolved:
            return False
    return True


def append_resolved_source_targets(
    proof: dict[str, Any],
    targets: list[str] | tuple[str, ...] | set[str] | str,
) -> dict[str, Any]:
    """Return a proof copy with resolved source targets appended once."""
    updated = dict(proof)
    resolved = _normalize_list(updated.get("RESOLVED_SOURCE_TARGETS"))
    for target in _normalize_list(targets):
        if target not in resolved:
            resolved.append(target)
    updated["RESOLVED_SOURCE_TARGETS"] = resolved
    return updated


def persist_routing_proof(proof: dict[str, Any], repo_root: Path, artifact_id: str) -> Path:
    """Append routing proof to runtime/cbo/routing_proofs.jsonl."""
    repo_root = Path(repo_root)
    runtime_dir = repo_root / "runtime" / "cbo"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / "routing_proofs.jsonl"
    payload = dict(proof)
    payload["artifact_id"] = _clean_text(artifact_id)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
