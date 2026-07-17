"""Phase I intake card normalization and validation."""

from __future__ import annotations

import re
from typing import Any


INTAKE_CARD_FIELDS = (
    "USE_CASE",
    "TRIGGERS",
    "ANTI_TRIGGERS",
    "ORDERED_STEPS",
    "EXPECTED_RESULT",
    "REQUIRED_EVIDENCE",
)


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    out: list[str] = []
    for item in items:
        text = _clean_string(item)
        if text and text not in out:
            out.append(text)
    return out


def _extract_search_target(intent: str) -> str:
    match = re.search(
        r"search(?:\s+the\s+[^\n]+?)?\s+for\s+['\"]?([^'\n\"]+?)['\"]?(?:\s+and|\s*\?|$)",
        intent,
        flags=re.IGNORECASE,
    )
    return _clean_string(match.group(1)) if match else ""


def _extract_definition_target(intent: str) -> str:
    match = re.search(
        r"which\s+file\s+defines\s+([^?.!\n]+)",
        intent,
        flags=re.IGNORECASE,
    )
    return _clean_string(match.group(1)) if match else ""


def _derive_use_case(artifact: dict[str, Any], intent: str, search_target: str, definition_target: str) -> str:
    explicit = _clean_string(
        (artifact.get("intake_card") or {}).get("USE_CASE")
        or artifact.get("use_case")
        or artifact.get("intent_summary")
    )
    if explicit:
        return explicit
    task_type = _clean_string(artifact.get("task_type") or "unspecified_task")
    if search_target and definition_target and search_target.lower() != definition_target.lower():
        return f"Resolve compound query for search target '{search_target}' and definition target '{definition_target}' within task_type '{task_type}'."
    if intent:
        return intent
    return f"Process '{task_type}' request within declared scope."


def _derive_triggers(
    artifact: dict[str, Any],
    intent: str,
    task_type: str,
    search_target: str,
    definition_target: str,
) -> list[str]:
    explicit = _string_list((artifact.get("intake_card") or {}).get("TRIGGERS") or artifact.get("triggers"))
    derived: list[str] = list(explicit)
    for item in (intent, f"task_type:{task_type}" if task_type else "", f"search_target:{search_target}" if search_target else "", f"definition_target:{definition_target}" if definition_target else ""):
        text = _clean_string(item)
        if text and text not in derived:
            derived.append(text)
    return derived


def _derive_anti_triggers(
    artifact: dict[str, Any],
    intent: str,
    task_type: str,
    search_target: str,
    definition_target: str,
) -> list[str]:
    explicit = _string_list((artifact.get("intake_card") or {}).get("ANTI_TRIGGERS") or artifact.get("anti_triggers"))
    derived: list[str] = list(explicit)
    defaults = [
        "outside_declared_scope",
        f"outside_task_type:{task_type}" if task_type else "",
        "missing_required_evidence",
    ]
    if search_target and definition_target and search_target.lower() != definition_target.lower():
        defaults.append("do_not_collapse_search_target_into_definition_target")
    intent_lower = intent.lower()
    if "confirm" in intent_lower and "what" in intent_lower:
        defaults.append("do_not_treat_knowledge_query_as_simple_confirmation")
    for item in defaults:
        text = _clean_string(item)
        if text and text not in derived:
            derived.append(text)
    return derived


def _derive_ordered_steps(
    artifact: dict[str, Any],
    task_type: str,
    search_target: str,
    definition_target: str,
) -> list[str]:
    explicit = _string_list((artifact.get("intake_card") or {}).get("ORDERED_STEPS") or artifact.get("ordered_steps"))
    if explicit:
        return explicit
    if search_target and definition_target and search_target.lower() != definition_target.lower():
        return [
            f"Normalize the explicit search target '{search_target}' and the definition target '{definition_target}' separately.",
            "Reject any plan that ignores either target or merges them without explanation.",
            "Collect declared evidence for each target before planning execution.",
            "Produce a bounded result that either answers both targets or explains the distinction.",
        ]
    return [
        f"Normalize the '{task_type or 'unspecified'}' request into a bounded use case.",
        "Constrain the plan to declared scope and constraints before execution planning.",
        "Collect required evidence before any execution-capable step is authorized.",
        "Produce the expected result and stop at the declared boundary.",
    ]


def _derive_expected_result(
    artifact: dict[str, Any],
    task_type: str,
    search_target: str,
    definition_target: str,
) -> str:
    explicit = _clean_string((artifact.get("intake_card") or {}).get("EXPECTED_RESULT") or artifact.get("expected_result"))
    if explicit:
        return explicit
    if search_target and definition_target and search_target.lower() != definition_target.lower():
        return (
            f"Return a grounded answer for search target '{search_target}' and definition target '{definition_target}', "
            "or explicitly explain why they resolve to different artifacts."
        )
    return f"Produce a grounded '{task_type or 'unspecified'}' result within declared scope and evidence bounds."


def _derive_required_evidence(
    artifact: dict[str, Any],
    search_target: str,
    definition_target: str,
) -> list[str]:
    explicit = _string_list((artifact.get("intake_card") or {}).get("REQUIRED_EVIDENCE") or artifact.get("required_evidence"))
    evidence = artifact.get("evidence_requirements") or {}
    derived: list[str] = list(explicit)
    if isinstance(evidence, dict):
        for key in ("harness_lanes", "checks", "receipt_types"):
            for item in _string_list(evidence.get(key)):
                entry = f"{key}:{item}"
                if entry not in derived:
                    derived.append(entry)
    for item in (
        "intent_artifact_persisted",
        f"search_target:{search_target}" if search_target else "",
        f"definition_target:{definition_target}" if definition_target else "",
    ):
        text = _clean_string(item)
        if text and text not in derived:
            derived.append(text)
    return derived


def normalize_intake_card(artifact: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic intake card for the artifact."""
    intent = _clean_string(artifact.get("intent"))
    task_type = _clean_string(artifact.get("task_type"))
    search_target = _extract_search_target(intent)
    definition_target = _extract_definition_target(intent)
    return {
        "USE_CASE": _derive_use_case(artifact, intent, search_target, definition_target),
        "TRIGGERS": _derive_triggers(artifact, intent, task_type, search_target, definition_target),
        "ANTI_TRIGGERS": _derive_anti_triggers(artifact, intent, task_type, search_target, definition_target),
        "ORDERED_STEPS": _derive_ordered_steps(artifact, task_type, search_target, definition_target),
        "EXPECTED_RESULT": _derive_expected_result(artifact, task_type, search_target, definition_target),
        "REQUIRED_EVIDENCE": _derive_required_evidence(artifact, search_target, definition_target),
    }


def merge_intake_card(artifact: dict[str, Any]) -> dict[str, Any]:
    """Attach a deterministic intake card to an artifact copy."""
    merged = dict(artifact)
    merged["intake_card"] = normalize_intake_card(artifact)
    return merged


def missing_intake_card_fields(card: dict[str, Any]) -> list[str]:
    """Return required intake card fields that are absent or empty."""
    missing: list[str] = []
    for field in INTAKE_CARD_FIELDS:
        value = card.get(field)
        if isinstance(value, str):
            if not _clean_string(value):
                missing.append(field)
        elif isinstance(value, list):
            if not _string_list(value):
                missing.append(field)
        else:
            missing.append(field)
    return missing


def validate_intake_card(card: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return validation result and missing/invalid field names."""
    missing = missing_intake_card_fields(card)
    return len(missing) == 0, missing


def intake_card_clarification_message(missing: list[str]) -> str:
    """Create a deterministic clarification message for missing intake card fields."""
    if not missing:
        return "Intake card is complete."
    joined = ", ".join(missing)
    return f"Phase I intake card incomplete. Missing or empty fields: {joined}."
