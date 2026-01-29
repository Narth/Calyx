# -*- coding: utf-8 -*-
"""
Clawdbot Sandbox Configuration
==============================

Defines boundaries for Clawdbot execution.

SANDBOX PRINCIPLES:
- Default deny: Actions not explicitly allowed are blocked
- Path restrictions: Clawdbot cannot access protected directories
- Action restrictions: Certain action types require elevated approval
- Resource limits: Prevent unbounded resource consumption

PROTECTED PATHS (Clawdbot cannot modify):
- governance/ - HVD-1 and governance artifacts
- station_calyx/core/ - Core Station Calyx code
- station_calyx/clawdbot/ - This governance layer
- .git/ - Version control
- outgoing/gates/ - Gate files

ALLOWED PATHS (Clawdbot can access):
- station_calyx/data/clawdbot/ - Clawdbot workspace
- outgoing/clawdbot/ - Clawdbot heartbeats and status
- User-specified working directories
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class ActionRiskLevel(Enum):
    """Risk levels for Clawdbot actions."""
    LOW = "low"           # Read-only, reversible
    MEDIUM = "medium"     # Local modifications, reversible
    HIGH = "high"         # External effects, potentially irreversible
    CRITICAL = "critical" # Irreversible, requires human approval


class ActionCategory(Enum):
    """Categories of Clawdbot actions."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_COMMAND = "shell_command"
    NETWORK_REQUEST = "network_request"
    BROWSER_ACTION = "browser_action"
    EMAIL_SEND = "email_send"
    API_CALL = "api_call"
    SKILL_INSTALL = "skill_install"
    SKILL_MODIFY = "skill_modify"
    MEMORY_UPDATE = "memory_update"
    SYSTEM_MODIFY = "system_modify"


# Risk levels by action category
ACTION_RISK_MAP: dict[ActionCategory, ActionRiskLevel] = {
    ActionCategory.FILE_READ: ActionRiskLevel.LOW,
    ActionCategory.FILE_WRITE: ActionRiskLevel.MEDIUM,
    ActionCategory.FILE_DELETE: ActionRiskLevel.HIGH,
    ActionCategory.SHELL_COMMAND: ActionRiskLevel.HIGH,
    ActionCategory.NETWORK_REQUEST: ActionRiskLevel.MEDIUM,
    ActionCategory.BROWSER_ACTION: ActionRiskLevel.MEDIUM,
    ActionCategory.EMAIL_SEND: ActionRiskLevel.CRITICAL,
    ActionCategory.API_CALL: ActionRiskLevel.HIGH,
    ActionCategory.SKILL_INSTALL: ActionRiskLevel.HIGH,
    ActionCategory.SKILL_MODIFY: ActionRiskLevel.MEDIUM,
    ActionCategory.MEMORY_UPDATE: ActionRiskLevel.LOW,
    ActionCategory.SYSTEM_MODIFY: ActionRiskLevel.CRITICAL,
}


@dataclass
class SandboxConfig:
    """Configuration for Clawdbot sandbox."""
    
    # Protected paths (absolute or relative to workspace root)
    protected_paths: list[str] = field(default_factory=lambda: [
        "governance",
        "station_calyx/core",
        "station_calyx/clawdbot",
        "station_calyx/schemas",
        ".git",
        ".github",
        "outgoing/gates",
    ])
    
    # Allowed workspace paths
    allowed_paths: list[str] = field(default_factory=lambda: [
        "station_calyx/data/clawdbot",
        "outgoing/clawdbot",
    ])
    
    # Actions that require human approval regardless of risk level
    human_approval_required: list[ActionCategory] = field(default_factory=lambda: [
        ActionCategory.EMAIL_SEND,
        ActionCategory.SYSTEM_MODIFY,
    ])
    
    # Actions blocked entirely in trial phase
    blocked_actions: list[ActionCategory] = field(default_factory=lambda: [
        ActionCategory.SYSTEM_MODIFY,
    ])
    
    # Trial phase settings
    trial_mode: bool = True
    max_actions_per_hour: int = 100
    max_network_requests_per_hour: int = 50
    require_cbo_approval_all: bool = True  # In trial, all actions need CBO approval
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "protected_paths": self.protected_paths,
            "allowed_paths": self.allowed_paths,
            "human_approval_required": [a.value for a in self.human_approval_required],
            "blocked_actions": [a.value for a in self.blocked_actions],
            "trial_mode": self.trial_mode,
            "max_actions_per_hour": self.max_actions_per_hour,
            "max_network_requests_per_hour": self.max_network_requests_per_hour,
            "require_cbo_approval_all": self.require_cbo_approval_all,
        }


class SandboxEnforcer:
    """Enforces sandbox boundaries on Clawdbot actions."""
    
    def __init__(self, config: Optional[SandboxConfig] = None, workspace_root: Optional[Path] = None):
        self.config = config or SandboxConfig()
        self.workspace_root = workspace_root or Path.cwd()
        self._action_counts: dict[str, int] = {}
        self._last_reset_hour: Optional[int] = None
    
    def is_path_protected(self, path: str | Path) -> bool:
        """Check if a path is protected from Clawdbot access."""
        path = Path(path)
        
        # Make path relative to workspace if absolute
        try:
            if path.is_absolute():
                path = path.relative_to(self.workspace_root)
        except ValueError:
            # Path is outside workspace - protected by default
            return True
        
        path_str = str(path).replace("\\", "/")
        
        for protected in self.config.protected_paths:
            protected = protected.replace("\\", "/")
            if path_str.startswith(protected) or path_str == protected:
                return True
        
        return False
    
    def is_path_allowed(self, path: str | Path) -> bool:
        """Check if a path is in the allowed workspace."""
        if self.is_path_protected(path):
            return False
        
        path = Path(path)
        
        try:
            if path.is_absolute():
                path = path.relative_to(self.workspace_root)
        except ValueError:
            return False
        
        path_str = str(path).replace("\\", "/")
        
        # In trial mode, only explicitly allowed paths
        if self.config.trial_mode:
            for allowed in self.config.allowed_paths:
                allowed = allowed.replace("\\", "/")
                if path_str.startswith(allowed):
                    return True
            return False
        
        # Outside trial mode, anything not protected is allowed
        return True
    
    def is_action_allowed(
        self,
        category: ActionCategory,
        context: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Check if an action category is allowed.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Check if action is blocked entirely
        if category in self.config.blocked_actions:
            return False, f"Action category {category.value} is blocked in current configuration"
        
        # Check rate limits
        self._maybe_reset_counts()
        hour_key = category.value
        current_count = self._action_counts.get(hour_key, 0)
        
        if category == ActionCategory.NETWORK_REQUEST:
            if current_count >= self.config.max_network_requests_per_hour:
                return False, f"Network request rate limit exceeded ({self.config.max_network_requests_per_hour}/hour)"
        else:
            total_actions = sum(self._action_counts.values())
            if total_actions >= self.config.max_actions_per_hour:
                return False, f"Action rate limit exceeded ({self.config.max_actions_per_hour}/hour)"
        
        return True, "Action allowed by sandbox policy"
    
    def get_risk_level(self, category: ActionCategory) -> ActionRiskLevel:
        """Get the risk level for an action category."""
        return ACTION_RISK_MAP.get(category, ActionRiskLevel.HIGH)
    
    def requires_human_approval(self, category: ActionCategory) -> bool:
        """Check if action requires human approval."""
        return category in self.config.human_approval_required
    
    def requires_cbo_approval(self, category: ActionCategory) -> bool:
        """Check if action requires CBO approval."""
        if self.config.require_cbo_approval_all:
            return True
        
        risk = self.get_risk_level(category)
        return risk in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL)
    
    def record_action(self, category: ActionCategory) -> None:
        """Record an action for rate limiting."""
        self._maybe_reset_counts()
        hour_key = category.value
        self._action_counts[hour_key] = self._action_counts.get(hour_key, 0) + 1
    
    def _maybe_reset_counts(self) -> None:
        """Reset counts if hour has changed."""
        from datetime import datetime
        current_hour = datetime.now().hour
        
        if self._last_reset_hour != current_hour:
            self._action_counts = {}
            self._last_reset_hour = current_hour


# Global sandbox instance
_sandbox: Optional[SandboxEnforcer] = None


def get_sandbox_config() -> SandboxConfig:
    """Get the current sandbox configuration."""
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxEnforcer()
    return _sandbox.config


def get_sandbox() -> SandboxEnforcer:
    """Get the sandbox enforcer instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxEnforcer()
    return _sandbox


def is_path_allowed(path: str | Path) -> bool:
    """Check if a path is allowed for Clawdbot access."""
    return get_sandbox().is_path_allowed(path)


def is_action_allowed(category: ActionCategory, context: Optional[dict] = None) -> tuple[bool, str]:
    """Check if an action is allowed."""
    return get_sandbox().is_action_allowed(category, context)
