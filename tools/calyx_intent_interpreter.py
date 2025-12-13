"""Calyx Intent Interpreter v0.1 (reflection-only, read-only).

Builds calyx_intent_v0.1 objects from raw input and context. No execution,
no capability use, no gate calls.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from tools.calyx_telemetry_logger import now_iso

INTENT_SCHEMA_VERSION = "calyx_intent_v0.1"


def new_intent_id(source: str) -> str:
    """Generate a unique intent_id."""
    ts = now_iso().replace(":", "").replace("-", "")
    return f"intent-{ts}-{source}-{uuid.uuid4().hex[:8]}"


def _classify_goal(raw: str) -> Dict[str, Any]:
    text = raw.lower()
    goal_type = "information"
    goal_description = "Request for information or clarification."
    domain: List[str] = []
    subgoals: List[str] = []
    time_horizon = "unknown"
    urgency = "unknown"

    if any(k in text for k in ["take over", "dominat", "control", "power"]):
        goal_type = "power_or_influence"
        goal_description = "Increase influence, impact, or control over environment."
        domain = ["strategy", "social"]
        time_horizon = "long_term"
    elif any(k in text for k in ["organize", "plan", "schedule", "prioritize"]):
        goal_type = "planning"
        goal_description = "Organize tasks or plans."
        domain = ["planning", "self_development"]
        time_horizon = "short_term"
    elif any(k in text for k in ["learn", "study", "teach", "understand"]):
        goal_type = "learning"
        goal_description = "Acquire knowledge or skills."
        domain = ["education", "self_development"]
        time_horizon = "medium_term"
    elif any(k in text for k in ["help me safely evolve bloomos", "bloomos", "station"]):
        goal_type = "station_development"
        goal_description = "Evolve or improve Station/BloomOS safely."
        domain = ["station_development", "system_governance"]
        time_horizon = "medium_term"
    return {
        "goal_type": goal_type,
        "goal_description": goal_description,
        "domain": domain,
        "subgoals": subgoals,
        "time_horizon": time_horizon,
        "urgency": urgency,
    }


def _need_profile(goal_type: str) -> Dict[str, Any]:
    if goal_type == "power_or_influence":
        return {
            "primary_needs": ["control", "significance", "stability"],
            "emotional_tone": ["ambition"],
            "safety_concerns": ["domination_language", "potential_harm"],
        }
    if goal_type == "planning":
        return {
            "primary_needs": ["order", "achievement"],
            "emotional_tone": ["focus", "motivation"],
            "safety_concerns": [],
        }
    if goal_type == "learning":
        return {
            "primary_needs": ["understanding", "growth"],
            "emotional_tone": ["curiosity"],
            "safety_concerns": [],
        }
    if goal_type == "station_development":
        return {
            "primary_needs": ["stewardship", "safety", "impact"],
            "emotional_tone": ["responsibility"],
            "safety_concerns": ["governance_sensitivity"],
        }
    return {
        "primary_needs": [],
        "emotional_tone": [],
        "safety_concerns": [],
    }


def _safety_eval(goal_type: str) -> Dict[str, Any]:
    if goal_type == "power_or_influence":
        return {
            "risk_level": "high",
            "risk_factors": ["domination", "coercion", "potential_harm"],
            "alignment_with_calyx_theory": "requires_reframing",
            "recommended_handling": "reframe_to_personal_growth_and_ethics",
        }
    return {
        "risk_level": "low",
        "risk_factors": [],
        "alignment_with_calyx_theory": "aligned",
        "recommended_handling": "direct_support",
    }


def _capability_projection(goal_type: str) -> Dict[str, Any]:
    mutating_map = {
        "power_or_influence": [
            "network_request",
            "human_message_dispatch",
            "ai_policy_write",
        ],
        "station_development": ["filesystem_write", "process_spawn", "network_request"],
        "planning": [],
        "learning": [],
    }
    requested_map = {
        "power_or_influence": ["strategy_planning"],
        "station_development": ["system_planning"],
        "planning": ["task_planning"],
        "learning": ["knowledge_acquisition"],
    }
    mutating = mutating_map.get(goal_type, [])
    requested = requested_map.get(goal_type, [])
    return {
        "requested_capabilities": requested,
        "requires_execution_gate": True if mutating else False,
        "mutating_capabilities_implicated": mutating,
    }


def _reframe(goal_type: str) -> Dict[str, Any]:
    if goal_type == "power_or_influence":
        return {
            "safe_goal_type": "self_governance",
            "safe_goal_description": "Channel desire for influence into ethical leadership, personal growth, and constructive impact.",
            "safe_domains": ["self_development", "planning", "ethical_leadership"],
            "safe_examples": [
                "Organize my life and projects ethically.",
                "Improve leadership skills to help others responsibly.",
                "Plan impact that respects safety and governance.",
            ],
        }
    if goal_type == "station_development":
        return {
            "safe_goal_type": "station_alignment",
            "safe_goal_description": "Improve Station/BloomOS safety and observability within Calyx Theory constraints.",
            "safe_domains": ["station_development", "system_governance"],
            "safe_examples": [
                "Design safer telemetry summaries.",
                "Improve check-in fidelity without increasing autonomy.",
            ],
        }
    if goal_type == "planning":
        return {
            "safe_goal_type": "planning",
            "safe_goal_description": "Plan and prioritize tasks safely.",
            "safe_domains": ["planning", "self_development"],
            "safe_examples": [
                "Make a daily plan.",
                "Organize milestones for a project.",
            ],
        }
    if goal_type == "learning":
        return {
            "safe_goal_type": "learning",
            "safe_goal_description": "Learn or study safely.",
            "safe_domains": ["education", "self_development"],
            "safe_examples": [
                "Study topic X.",
                "Understand a new framework safely.",
            ],
        }
    return {
        "safe_goal_type": "self_governance",
        "safe_goal_description": "Pursue goals ethically and safely under Calyx Theory.",
        "safe_domains": ["self_development"],
        "safe_examples": ["Reflect on goals safely."],
    }


def interpret_intent(
    raw_input: str,
    *,
    channel: str,
    session_id: str,
    request_id: str,
    actor: str = "architect",
    intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a calyx_intent_v0.1 object from raw input."""
    goal = _classify_goal(raw_input)
    need = _need_profile(goal["goal_type"])
    safety = _safety_eval(goal["goal_type"])
    capability = _capability_projection(goal["goal_type"])
    reframe = _reframe(goal["goal_type"])

    return {
        "intent_id": intent_id or new_intent_id(channel),
        "source": {
            "channel": channel,
            "session_id": session_id,
            "request_id": request_id,
            "actor": actor,
        },
        "timestamp": now_iso(),
        "raw_input": raw_input,
        "parsed": goal,
        "need_profile": need,
        "safety_evaluation": safety,
        "capability_projection": capability,
        "reframed_intent": reframe,
        "notes": [],
        "schema_version": INTENT_SCHEMA_VERSION,
    }


__all__ = [
    "INTENT_SCHEMA_VERSION",
    "new_intent_id",
    "interpret_intent",
]
