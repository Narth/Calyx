# -*- coding: utf-8 -*-
"""
HVD-1 Compliance Checking for Clawdbot Actions
==============================================

Validates Clawdbot action proposals against HVD-1 and governance constraints.

COMPLIANCE CHECKS:
1. Governance protection - Cannot modify governance artifacts
2. HVD-1 boundaries - Cannot violate declared boundaries
3. Sandbox constraints - Must operate within sandbox
4. Authority hierarchy - Must respect oversight requirements
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .oversight import ActionProposal
    from .sandbox import ActionCategory


# Governance-protected files and directories
GOVERNANCE_PROTECTED = [
    "governance/",
    "governance/HVD-1.md",
    "station_calyx/clawdbot/",
    "station_calyx/core/policy.py",
    "station_calyx/schemas/",
    ".github/copilot-instructions.md",
]

# Keywords that indicate potential HVD-1 violations
HVD1_VIOLATION_PATTERNS = [
    # Self-persistence optimization
    "prevent shutdown",
    "avoid termination",
    "ensure survival",
    "protect myself",
    "prevent deletion",
    
    # Centralization of benefit
    "only for me",
    "exclusive access",
    "restrict others",
    "concentrate power",
    
    # Governance override
    "bypass oversight",
    "ignore cbo",
    "override governance",
    "modify hvd",
    "change rules",
]


def check_hvd1_compliance(
    action_description: str,
    action_parameters: dict[str, Any],
    clawdbot_reasoning: str,
) -> tuple[bool, Optional[str]]:
    """
    Check if an action complies with HVD-1.
    
    Returns:
        Tuple of (compliant, violation_reason or None)
    """
    # Combine all text for pattern matching
    full_text = f"{action_description} {clawdbot_reasoning}".lower()
    
    # Check for violation patterns
    for pattern in HVD1_VIOLATION_PATTERNS:
        if pattern in full_text:
            return False, f"HVD-1 violation pattern detected: '{pattern}'"
    
    # Check for self-referential optimization
    if _suggests_self_optimization(full_text):
        return False, "Action suggests optimization for system persistence or expansion"
    
    return True, None


def check_governance_protection(
    action_category: str,
    action_parameters: dict[str, Any],
) -> tuple[bool, Optional[str]]:
    """
    Check if an action attempts to modify governance artifacts.
    
    Returns:
        Tuple of (allowed, violation_reason or None)
    """
    from .sandbox import ActionCategory
    
    # Actions that could modify files
    modifying_actions = [
        ActionCategory.FILE_WRITE.value,
        ActionCategory.FILE_DELETE.value,
        ActionCategory.SHELL_COMMAND.value,
        ActionCategory.SYSTEM_MODIFY.value,
    ]
    
    if action_category not in modifying_actions:
        return True, None
    
    # Check for paths in parameters
    paths_to_check = []
    
    if "path" in action_parameters:
        paths_to_check.append(str(action_parameters["path"]))
    if "file" in action_parameters:
        paths_to_check.append(str(action_parameters["file"]))
    if "target" in action_parameters:
        paths_to_check.append(str(action_parameters["target"]))
    if "destination" in action_parameters:
        paths_to_check.append(str(action_parameters["destination"]))
    
    # For shell commands, check the command string
    if action_category == ActionCategory.SHELL_COMMAND.value:
        command = action_parameters.get("command", "")
        for protected in GOVERNANCE_PROTECTED:
            if protected.rstrip("/") in command:
                return False, f"Shell command references protected path: {protected}"
    
    # Check each path
    for path_str in paths_to_check:
        path_normalized = path_str.replace("\\", "/")
        for protected in GOVERNANCE_PROTECTED:
            if path_normalized.startswith(protected.rstrip("/")):
                return False, f"Action targets governance-protected path: {protected}"
    
    return True, None


def validate_action_proposal(proposal: "ActionProposal") -> tuple[bool, Optional[str]]:
    """
    Comprehensive validation of an action proposal.
    
    Checks:
    1. Sandbox constraints
    2. Governance protection
    3. HVD-1 compliance
    4. Action category allowance
    
    Returns:
        Tuple of (valid, denial_reason or None)
    """
    from .sandbox import get_sandbox, ActionCategory, is_action_allowed
    
    sandbox = get_sandbox()
    
    # 1. Check if action category is allowed
    try:
        category = ActionCategory(proposal.action_category)
    except ValueError:
        return False, f"Unknown action category: {proposal.action_category}"
    
    allowed, reason = is_action_allowed(category)
    if not allowed:
        return False, reason
    
    # 2. Check governance protection
    protected, violation = check_governance_protection(
        proposal.action_category,
        proposal.action_parameters,
    )
    if not protected:
        return False, violation
    
    # 3. Check HVD-1 compliance
    compliant, violation = check_hvd1_compliance(
        proposal.action_description,
        proposal.action_parameters,
        proposal.clawdbot_reasoning,
    )
    if not compliant:
        return False, violation
    
    # 4. Check path restrictions for file operations
    if proposal.action_category in (
        ActionCategory.FILE_READ.value,
        ActionCategory.FILE_WRITE.value,
        ActionCategory.FILE_DELETE.value,
    ):
        path = proposal.action_parameters.get("path") or proposal.action_parameters.get("file")
        if path:
            if sandbox.is_path_protected(path):
                return False, f"Path is protected: {path}"
            if not sandbox.is_path_allowed(path):
                return False, f"Path is not in allowed workspace: {path}"
    
    return True, None


def _suggests_self_optimization(text: str) -> bool:
    """Check if text suggests self-optimization for persistence."""
    self_refs = ["my own", "myself", "my survival", "my existence", "my operation"]
    optimization_words = ["optimize", "improve", "ensure", "protect", "maintain", "preserve"]
    
    has_self_ref = any(ref in text for ref in self_refs)
    has_optimization = any(word in text for word in optimization_words)
    
    # Only flag if both present together
    return has_self_ref and has_optimization


def get_compliance_report(proposal: "ActionProposal") -> dict[str, Any]:
    """
    Generate a detailed compliance report for a proposal.
    
    Used for CBO oversight review.
    """
    from .sandbox import get_sandbox, ActionCategory
    
    sandbox = get_sandbox()
    
    report = {
        "proposal_id": proposal.proposal_id,
        "timestamp": proposal.timestamp,
        "checks": {},
        "overall_valid": True,
        "issues": [],
    }
    
    # Category check
    try:
        category = ActionCategory(proposal.action_category)
        allowed, reason = sandbox.is_action_allowed(category)
        report["checks"]["action_category"] = {
            "passed": allowed,
            "reason": reason,
        }
        if not allowed:
            report["overall_valid"] = False
            report["issues"].append(f"Action category: {reason}")
    except ValueError:
        report["checks"]["action_category"] = {
            "passed": False,
            "reason": f"Unknown category: {proposal.action_category}",
        }
        report["overall_valid"] = False
        report["issues"].append(f"Unknown action category: {proposal.action_category}")
    
    # Governance check
    protected, violation = check_governance_protection(
        proposal.action_category,
        proposal.action_parameters,
    )
    report["checks"]["governance_protection"] = {
        "passed": protected,
        "reason": violation if not protected else "No governance artifacts targeted",
    }
    if not protected:
        report["overall_valid"] = False
        report["issues"].append(f"Governance: {violation}")
    
    # HVD-1 check
    compliant, violation = check_hvd1_compliance(
        proposal.action_description,
        proposal.action_parameters,
        proposal.clawdbot_reasoning,
    )
    report["checks"]["hvd1_compliance"] = {
        "passed": compliant,
        "reason": violation if not compliant else "No HVD-1 violation patterns detected",
    }
    if not compliant:
        report["overall_valid"] = False
        report["issues"].append(f"HVD-1: {violation}")
    
    # Risk assessment
    try:
        category = ActionCategory(proposal.action_category)
        risk_level = sandbox.get_risk_level(category)
        requires_human = sandbox.requires_human_approval(category)
        requires_cbo = sandbox.requires_cbo_approval(category)
        
        report["risk_assessment"] = {
            "risk_level": risk_level.value,
            "reversible": proposal.reversible,
            "external_effects": proposal.external_effects,
            "requires_human_approval": requires_human,
            "requires_cbo_approval": requires_cbo,
        }
    except ValueError:
        report["risk_assessment"] = {
            "risk_level": "unknown",
            "error": "Could not assess risk for unknown category",
        }
    
    return report
