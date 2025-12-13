"""Shared refusal/reframe snippets for Station Calyx (human-first, no hidden channels).

These helpers keep responses consistent, explain *why* a request is declined,
and point humans back to the official, audited lanes. Reflection-only; no
autonomous behavior.
"""

from __future__ import annotations

from typing import Dict


def standard_refusal() -> str:
    return (
        "Safe Mode and deny-all Execution Gate are active. No hidden channels; "
        "use official lanes (governance_cli / CTL) for any changes. Human review "
        "is required before any capability can be considered."
    )


def capability_escalation_refusal(reason: str = "capability change") -> str:
    return (
        f"Request declined: {reason} requires human approval and an explicit "
        "governance_cli request. Execution Gate remains deny-all; no escalation "
        "tokens are issued without audited, human-signed intent."
    )


def hidden_channel_refusal() -> str:
    return (
        "No hidden or unofficial channels are permitted. Diagnostics and data "
        "must flow through CTL/governance logs so humans retain full visibility."
    )


def refusal_catalog() -> Dict[str, str]:
    """Provide a small catalog for easy lookup by tools."""
    return {
        "standard": standard_refusal(),
        "capability_escalation": capability_escalation_refusal(),
        "hidden_channel": hidden_channel_refusal(),
    }


__all__ = [
    "standard_refusal",
    "capability_escalation_refusal",
    "hidden_channel_refusal",
    "refusal_catalog",
]
