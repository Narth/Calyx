"""IntentGateway - canonical ingress for inbound user messages

Accepts inbound messages from any channel and creates IntentArtifacts.
Emits evidence events for MESSAGE_RECEIVED, INTENT_ARTIFACT_CREATED (via accept),
MESSAGE_ACK_SENT, and CLARIFICATION_REQUESTED when required.

Contract:
 - process_inbound_message(channel, sender, message, metadata=None, trusted=False)
   -> returns dict: {intent_id, status, reason, clarification_questions}

Status values: ACCEPTED, NEEDS_CLARIFICATION, REJECTED

"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .intent_artifact import (
    IntentArtifact,
    accept_intent_artifact,
    get_artifact_path,
    DEFAULT_CONFIDENCE_THRESHOLD,
)
from .system_mode import get_system_mode, check_execution_allowed
from .user_model import load_user_model, record_confirmation, record_rejection, record_clarification
from station_calyx.core.user_model import get_user_model_path
from station_calyx.core.evidence import create_event, append_event
from .evidence import create_event, append_event, load_recent_events
from .config import get_config
from .execution_policy import decide as policy_decide


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def process_inbound_message(
    channel: str,
    sender: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    trusted: bool = False,
) -> Dict[str, Any]:
    """Process an inbound message and create/persist an IntentArtifact.

    Returns a structured result describing the artifact and required next steps.
    """
    metadata = metadata or {}

    # Produce stable intent_id (UUIDv4)
    intent_id = f"intent-{uuid.uuid4().hex[:8]}"

    # Base interpreted goal is the raw message; consult UserModel to improve
    interpreted_goal = message
    # Base confidence strategy: default low
    default_conf = float(metadata.get("confidence", 0.5))

    # Identity binding: resolve trusted user_id per channel
    user_id = None
    untrusted_user_id = metadata.get("user_id") if metadata else None
    if metadata and metadata.get("user_id"):
        # Channel-aware binding
        if channel == "standard":
            # Dashboard: expect session-bound user in metadata['session_user']
            session_user = metadata.get("session_user")
            if session_user and session_user == untrusted_user_id:
                user_id = untrusted_user_id
            else:
                # Emit evidence of unbound user
                try:
                    evt = create_event(
                        event_type="USER_ID_UNBOUND",
                        node_role="intent_gateway",
                        summary="Untrusted user_id on dashboard message",
                        payload={"provided_user_id": untrusted_user_id, "session_user": metadata.get("session_user")},
                        tags=["user_model", "unbound"],
                        session_id=intent_id,
                    )
                    append_event(evt)
                except Exception:
                    pass
        elif channel == "discord":
            # Discord: expect numeric discord id
            try:
                int(untrusted_user_id)
                user_id = untrusted_user_id
            except Exception:
                try:
                    evt = create_event(
                        event_type="USER_ID_REJECTED",
                        node_role="intent_gateway",
                        summary="Rejected non-numeric Discord user_id",
                        payload={"provided_user_id": untrusted_user_id},
                        tags=["user_model", "rejected"],
                        session_id=intent_id,
                    )
                    append_event(evt)
                except Exception:
                    pass
        elif channel == "cli":
            # CLI/local: operator identity must be present
            op = metadata.get("operator")
            if op and op == untrusted_user_id:
                user_id = untrusted_user_id
            else:
                try:
                    evt = create_event(
                        event_type="USER_ID_UNBOUND",
                        node_role="intent_gateway",
                        summary="Untrusted user_id on cli message",
                        payload={"provided_user_id": untrusted_user_id, "operator": metadata.get("operator")},
                        tags=["user_model", "unbound"],
                        session_id=intent_id,
                    )
                    append_event(evt)
                except Exception:
                    pass

    # Consult user model only if identity bound
    if user_id:
        try:
            user_model = load_user_model(user_id)
            # Conservative confidence rule: require at least 1 prior confirmation to boost
            match_confirmed = any(rec.get("interpreted_goal") == interpreted_goal for rec in user_model.confirmed_intents)
            match_rejected = any(rec.get("interpreted_goal") == interpreted_goal for rec in user_model.rejected_interpretations)
            if match_confirmed:
                # Only boost if there is at least one confirmation record
                default_conf = min(0.95, default_conf + 0.2)
                inferred = True
                user_summary = {
                    "pattern_confirmed_count": len(user_model.confirmed_intents),
                    "last_confirmed": user_model.confirmed_intents[-1].get("confirmed_at") if user_model.confirmed_intents else None,
                }
            else:
                inferred = False
                user_summary = {}

            if match_rejected:
                default_conf = max(0.0, default_conf - 0.3)
        except Exception:
            inferred = False
            user_summary = {}
    else:
        inferred = False
        user_summary = {}

    # Ensure within 0.0-1.0
    default_conf = max(0.0, min(1.0, default_conf))

    clarification_required = bool(metadata.get("clarification_required", False)) or (default_conf < float(DEFAULT_CONFIDENCE_THRESHOLD))

    artifact = IntentArtifact(
        intent_id=intent_id,
        raw_user_input=message,
        interpreted_goal=interpreted_goal,
        constraints=metadata.get("constraints", {}),
        confidence_score=default_conf,
        clarification_required=clarification_required,
        inferred_from_user_model=inferred,
        user_model_summary=user_summary,
    )

    # Emit MESSAGE_RECEIVED event
    try:
        evt = create_event(
            event_type="MESSAGE_RECEIVED",
            node_role="intent_gateway",
            summary=f"Message received from {sender} on {channel}",
            payload={
                "channel": channel,
                "sender": sender,
                "message_preview": (message[:200] if message else ""),
                "intent_id": intent_id,
                "direction": "inbound",
            },
            tags=["message", channel, "ingress"],
            session_id=intent_id,
        )
        append_event(evt)
    except Exception:
        pass

    # Persist artifact
    try:
        # Write artifact but ensure no execution is triggered here
        # System mode check (non-execution path) just ensures safe startup
        _mode = get_system_mode()
        accept_intent_artifact(artifact)
    except Exception:
        # Persist failed
        return {"intent_id": intent_id, "status": "REJECTED", "reason": "persist_failed", "clarification_questions": []}

    # Decide status
    if clarification_required:
        # Emit clarification requested event
        try:
            q = [f"Please confirm intent: '{artifact.interpreted_goal}'?"]
            evt2 = create_event(
                event_type="CLARIFICATION_REQUESTED",
                node_role="intent_gateway",
                summary=f"Clarification requested for {intent_id}",
                payload={"intent_id": intent_id, "questions": q},
                tags=["intent", "clarification"],
                session_id=intent_id,
            )
            append_event(evt2)
        except Exception:
            q = []

        return {"intent_id": intent_id, "status": "NEEDS_CLARIFICATION", "reason": "low_confidence", "clarification_questions": q}

    # Accepted
    return {"intent_id": intent_id, "status": "ACCEPTED", "reason": "accepted", "clarification_questions": []}


def echo_chain_info(intent_id: str) -> Dict[str, Any]:
    """Return artifact path and last evidence offset/hash for echo chain test."""
    cfg = get_config()
    artifact_path = get_artifact_path(intent_id)
    # Last evidence event (if available)
    events = load_recent_events(1)
    last = events[-1] if events else None
    last_hash = last.get("_hash") if last else None
    last_ts = last.get("ts") if last else None
    return {"artifact_path": str(artifact_path), "last_event_hash": last_hash, "last_event_ts": last_ts}
