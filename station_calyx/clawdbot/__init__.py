# -*- coding: utf-8 -*-
"""
Clawdbot Governance Layer
=========================

Station Calyx governance infrastructure for Clawdbot integration.

PURPOSE:
- Contain Clawdbot capabilities within Station Calyx governance
- Enforce HVD-1 compliance on all Clawdbot actions
- Provide CBO oversight for action proposals
- Log all actions to evidence store
- Enable trial phase monitoring and kill switch

AUTHORITY HIERARCHY:
1. Human (Architect) - Ultimate authority
2. HVD-1 - Non-overridable constraints
3. CBO - Oversight and approval
4. Clawdbot - Execution within approved bounds

CONSTRAINTS (NON-NEGOTIABLE):
- Clawdbot cannot modify governance artifacts
- Clawdbot cannot bypass CBO oversight
- Clawdbot cannot access Station Calyx core without explicit gate
- All actions logged to evidence store
- Unintended execution triggers immediate halt

TRIAL PHASE:
- Sandbox mode enforced
- All actions require CBO approval
- Kill switch available at any time
- Evidence preserved regardless of outcome
"""

from .sandbox import (
    SandboxConfig,
    SandboxEnforcer,
    get_sandbox_config,
    is_path_allowed,
    is_action_allowed,
)
from .oversight import (
    ActionProposal,
    OversightDecision,
    OversightQueue,
    submit_action_proposal,
    get_pending_proposals,
    approve_action,
    deny_action,
)
from .action_log import (
    ActionRecord,
    log_action,
    log_action_outcome,
    get_action_history,
)
from .kill_switch import (
    is_clawdbot_enabled,
    enable_clawdbot,
    disable_clawdbot,
    emergency_halt,
)
from .compliance import (
    check_hvd1_compliance,
    check_governance_protection,
    validate_action_proposal,
)

__all__ = [
    # Sandbox
    "SandboxConfig",
    "SandboxEnforcer", 
    "get_sandbox_config",
    "is_path_allowed",
    "is_action_allowed",
    # Oversight
    "ActionProposal",
    "OversightDecision",
    "OversightQueue",
    "submit_action_proposal",
    "get_pending_proposals",
    "approve_action",
    "deny_action",
    # Action logging
    "ActionRecord",
    "log_action",
    "log_action_outcome",
    "get_action_history",
    # Kill switch
    "is_clawdbot_enabled",
    "enable_clawdbot",
    "disable_clawdbot",
    "emergency_halt",
    # Compliance
    "check_hvd1_compliance",
    "check_governance_protection",
    "validate_action_proposal",
]
