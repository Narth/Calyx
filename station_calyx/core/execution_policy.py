"""ExecutionPolicy - capability-scoped decision engine

Provides a simple, auditable execution policy used in PHASE_4_LIVE.
Decision returns ALLOW | DENY | REQUIRE_APPROVAL and emits EXECUTION_POLICY_DECISION events.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Any

from .evidence import create_event, append_event
from .config import get_config

# Default allowlist (can be extended via env or config)
DEFAULT_ALLOWLIST = os.environ.get("CALYX_CAPABILITY_ALLOWLIST", "read_evidence,list_processes,read_logs,write_outgoing").split(",")

class Decision:
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decide(intent_id: str, requested_capability: str, caller_identity: Dict[str, Any], channel: str, risk: str = "LOW") -> Dict[str, Any]:
    """Make a policy decision and emit an evidence event.

    - For PHASE 4 initial rollout: allow only capabilities in allowlist and LOW risk.
    """
    cfg = get_config()
    allowlist = DEFAULT_ALLOWLIST
    # allowlist may be in cfg.metadata later; keep env-driven for now

    if requested_capability in allowlist and risk == "LOW":
        decision = Decision.ALLOW
        rationale = "Capability allowed by allowlist and low risk"
    else:
        decision = Decision.DENY
        rationale = "Capability not allowed by allowlist or risk too high"

    # Emit evidence
    try:
        evt = create_event(
            event_type="EXECUTION_POLICY_DECISION",
            node_role="execution_policy",
            summary=f"Policy decision for capability {requested_capability}",
            payload={
                "intent_id": intent_id,
                "requested_capability": requested_capability,
                "decision": decision,
                "rationale": rationale,
                "caller_identity": caller_identity,
                "channel": channel,
                "risk": risk,
                "timestamp": _now_iso(),
            },
            tags=["execution","policy","decision"],
            session_id=intent_id,
        )
        append_event(evt)
    except Exception:
        pass

    return {"decision": decision, "rationale": rationale}
