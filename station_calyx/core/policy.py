"""Station Calyx Policy Gate"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

COMPONENT_ROLE = "policy_gate"

class ExecutionResult(Enum):
    DENIED = "DENIED"
    ALLOWED = "ALLOWED"

@dataclass
class PolicyDecision:
    result: ExecutionResult
    reason: str
    timestamp: str
    request_type: str
    request_summary: str
    policy_version: str = "v1-deny-all"
    def to_dict(self) -> dict[str, Any]:
        return {"result": self.result.value, "reason": self.reason, "timestamp": self.timestamp, "request_type": self.request_type, "request_summary": self.request_summary, "policy_version": self.policy_version}

@dataclass
class ExecutionPolicy:
    deny_all: bool = True
    allow_list: list[str] = field(default_factory=list)
    policy_version: str = "v1-deny-all"
    advisory_only: bool = True
    execution_enabled: bool = False

class PolicyGate:
    def __init__(self, policy: Optional[ExecutionPolicy] = None):
        self.policy = policy or ExecutionPolicy()
        self._decision_count = 0
        self._denied_count = 0
    
    def evaluate(self, request_type: str, request_summary: str, context: Optional[dict[str, Any]] = None, log_decision: bool = True) -> PolicyDecision:
        now = datetime.now(timezone.utc)
        self._decision_count += 1
        self._denied_count += 1
        return PolicyDecision(result=ExecutionResult.DENIED, reason="EXECUTION_GATE: deny-all active (v1 advisory-only mode)", timestamp=now.isoformat(), request_type=request_type, request_summary=request_summary, policy_version=self.policy.policy_version)
    
    def get_stats(self) -> dict[str, Any]:
        return {"policy_version": self.policy.policy_version, "deny_all": self.policy.deny_all, "advisory_only": self.policy.advisory_only, "execution_enabled": self.policy.execution_enabled, "total_decisions": self._decision_count, "denied_count": self._denied_count}

_default_gate: Optional[PolicyGate] = None

def get_policy_gate() -> PolicyGate:
    global _default_gate
    if _default_gate is None: _default_gate = PolicyGate()
    return _default_gate

def request_execution(request_type: str, request_summary: str, context: Optional[dict[str, Any]] = None) -> PolicyDecision:
    return get_policy_gate().evaluate(request_type, request_summary, context)
