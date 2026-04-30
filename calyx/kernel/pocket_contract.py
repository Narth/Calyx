"""Pocket-contract normalization and validation for whiteboard pockets."""

from __future__ import annotations

from typing import Any


REQUIRED_POCKET_CONTRACT_FIELDS = (
    "OBJECTIVE",
    "ALLOWED_CONTEXT",
    "ALLOWED_TOOLS",
    "EXIT_CRITERIA",
    "MAX_RECURSION_DEPTH",
)

_REASON_ONLY_TOKENS = frozenset({"reason_only", "no_tools", "none"})


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.replace("\r", "\n").replace(",", "\n").split("\n")
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]
    items: list[str] = []
    for raw in raw_items:
        text = _normalize_text(raw)
        if text and text not in items:
            items.append(text)
    return items


def _coerce_nonnegative_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def normalize_pocket_contract(
    payload: dict[str, Any] | None,
    *,
    fallback_objective: str = "",
) -> dict[str, Any]:
    source = payload or {}
    contract = {
        "OBJECTIVE": _normalize_text(source.get("OBJECTIVE") or source.get("objective") or fallback_objective),
        "ALLOWED_CONTEXT": _normalize_list(source.get("ALLOWED_CONTEXT") or source.get("allowed_context")),
        "ALLOWED_TOOLS": _normalize_list(source.get("ALLOWED_TOOLS") or source.get("allowed_tools")),
        "EXIT_CRITERIA": _normalize_list(source.get("EXIT_CRITERIA") or source.get("exit_criteria")),
    }
    max_depth = _coerce_nonnegative_int(
        source.get("MAX_RECURSION_DEPTH")
        if "MAX_RECURSION_DEPTH" in source
        else source.get("max_recursion_depth")
    )
    if max_depth is not None:
        contract["MAX_RECURSION_DEPTH"] = max_depth
    return contract


def validate_pocket_contract(contract: dict[str, Any] | None) -> list[str]:
    normalized = normalize_pocket_contract(contract)
    errors: list[str] = []
    if not normalized["OBJECTIVE"]:
        errors.append("OBJECTIVE")
    if not normalized["ALLOWED_CONTEXT"]:
        errors.append("ALLOWED_CONTEXT")
    if not normalized["ALLOWED_TOOLS"]:
        errors.append("ALLOWED_TOOLS")
    if not normalized["EXIT_CRITERIA"]:
        errors.append("EXIT_CRITERIA")
    if "MAX_RECURSION_DEPTH" not in normalized:
        errors.append("MAX_RECURSION_DEPTH")
    return errors


def get_max_recursion_depth(contract: dict[str, Any] | None) -> int:
    normalized = normalize_pocket_contract(contract)
    return int(normalized.get("MAX_RECURSION_DEPTH", 0))


def current_depth_exceeds_contract(contract: dict[str, Any] | None, depth: Any) -> bool:
    parsed_depth = _coerce_nonnegative_int(depth)
    if parsed_depth is None:
        return True
    return parsed_depth > get_max_recursion_depth(contract)


def whiteboard_allows_live_tools(contract: dict[str, Any] | None) -> bool:
    normalized = normalize_pocket_contract(contract)
    allowed_tools = {item.strip().lower() for item in normalized["ALLOWED_TOOLS"] if item.strip()}
    if not allowed_tools:
        return False
    return not allowed_tools.issubset(_REASON_ONLY_TOKENS)
