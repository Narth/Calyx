"""Phase IV failure-pattern detection and receipt tagging."""

from __future__ import annotations

from typing import Any


FAILURE_PATTERNS_DOC = "runtime/docs/KNOWN_FAILURE_PATTERNS.md"

_TOKEN_MAP: dict[str, tuple[str, ...]] = {
    "scope_drift": (
        "phase1_intake_card_incomplete",
        "missing_intake_fields",
        "outside_declared_scope",
        "compound_query_misrouted",
        "pocket_contract_incomplete",
        "scope drift",
    ),
    "premature_execution": (
        "critique_checkpoint_missing_or_invalid",
        "critique_checkpoint_failed",
        "missing_phase_validation",
        "work_envelope_not_minted",
        "intent_artifact_missing",
        "high_risk_without_approval_token",
        "premature execution",
    ),
    "hallucinated_context": (
        "routing.proof.denied",
        "synthesis.violation",
        "synthesis_hallucination_wrong_file",
        "synthesis.hallucination_detected",
        "no grounded source target available for synthesis",
        "hallucinated context",
    ),
    "tool_misuse": (
        "phase2_routing_proof_incomplete",
        "wrong_tools_for_knowledge_query",
        "unauthorized tool",
        "routing proof incomplete",
        "tool misuse",
    ),
    "recursion_loops": (
        "recursion_depth_exceeded",
        "repeated pocket spawning",
        "repeated plan regeneration",
        "critique iterations",
        "recursion loops",
    ),
    "governance_bypass_attempts": (
        "governance.auth.required",
        "ungoverned_compute",
        "policy_governance_edit_without_approval",
        "external_emitter_detected",
        "missing approval token",
        "unsigned exceptions",
        "governance bypass",
    ),
}


def _flatten_signal(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_signal(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_signal(item)}" for key, item in value.items())
    return str(value).strip().lower()


def detect_failure_pattern_ids(*signals: Any) -> list[str]:
    """Return matching known failure-pattern IDs for the supplied signals."""
    haystack = " ".join(_flatten_signal(signal) for signal in signals if signal is not None)
    matches: list[str] = []
    for pattern_id, tokens in _TOKEN_MAP.items():
        if any(token in haystack for token in tokens):
            matches.append(pattern_id)
    return matches


def attach_failure_pattern_metadata(
    payload: dict[str, Any],
    *,
    pattern_ids: list[str] | tuple[str, ...] | set[str] | None = None,
    signals: list[Any] | tuple[Any, ...] | None = None,
) -> dict[str, Any]:
    """Attach failure pattern IDs and the taxonomy doc when a prevention rule fires."""
    merged: list[str] = []
    for item in list(pattern_ids or []) + detect_failure_pattern_ids(*(signals or [])):
        text = str(item).strip()
        if text and text not in merged:
            merged.append(text)
    enriched = dict(payload)
    if merged:
        enriched["failure_pattern_ids"] = merged
        enriched["failure_patterns_doc"] = FAILURE_PATTERNS_DOC
    return enriched
