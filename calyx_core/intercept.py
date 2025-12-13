from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional


class ActionType(Enum):
    """What kind of thing is being intercepted?"""

    AGENT_TASK = auto()
    AGENT_SPAWN = auto()
    AGENT_TERMINATE = auto()
    SCHEDULER_LAUNCH = auto()
    TOOL_CALL = auto()
    API_CALL = auto()
    EXTERNAL_API = auto()  # kept for compatibility; prefer API_CALL going forward
    STATE_WRITE = auto()
    MAILBOX_WRITE = auto()
    SCHEDULER_TICK = auto()
    SYSTEM_CMD = auto()
    FILE_IO = auto()


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CASDirective(Enum):
    """What CAS might want done with this action/agent."""

    NONE = "none"
    PAUSE_AGENT = "pause_agent"
    QUARANTINE_AGENT = "quarantine_agent"
    HALT_STATION = "halt_station"


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    ram_percent: float


@dataclass
class InterceptContext:
    """
    The 'who/what/why' of an action an agent is trying to perform.
    This is what CBO sends into the Interceptor.
    """

    agent_name: str
    action_type: ActionType
    description: str
    tool_name: Optional[str] = None
    payload_meta: Dict[str, Any] = field(default_factory=dict)
    tes: Optional[float] = None
    agii: Optional[float] = None
    cas: Optional[float] = None
    resources: Optional[ResourceSnapshot] = None
    timestamp: float = field(default_factory=time.time)
    dry_run: bool = False


@dataclass
class InterceptDecision:
    """The Interceptor's ruling on whether an action may proceed."""

    allow: bool
    cas_directive: CASDirective = CASDirective.NONE
    severity: Severity = Severity.INFO
    reasons: List[str] = field(default_factory=list)
    require_human_review: bool = False
    adjust_autonomy: Optional[str] = None
    log_path: Optional[Path] = None


class StationInterceptor:
    """
    Single chokepoint for all significant actions in Station Calyx.
    """

    def __init__(
        self,
        log_dir: str = "./reports/intercepts/phaseA",
        record_only: bool = True,
        tes_thresholds: Optional[Dict[str, float]] = None,
        resource_limits: Optional[Dict[str, float]] = None,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.record_only = record_only

        self.tes_thresholds = tes_thresholds or {
            "autonomy_increase": 94.0,
            "stable_min": 90.0,
            "rollback_warn": 88.0,
            "pause": 85.0,
            "quarantine": 82.0,
        }

        self.resource_limits = resource_limits or {
            "cpu_soft": 85.0,
            "cpu_hard": 95.0,
            "ram_soft": 85.0,
            "ram_hard": 95.0,
        }

    def check(self, ctx: InterceptContext) -> InterceptDecision:
        reasons: List[str] = []
        cas_dir = CASDirective.NONE
        severity = Severity.INFO
        require_review = False
        adjust_autonomy: Optional[str] = None

        res_decision = self._check_resources(ctx)
        reasons.extend(res_decision.reasons)
        cas_dir = self._max_cas(cas_dir, res_decision.cas_directive)
        severity = self._max_severity(severity, res_decision.severity)

        tes_decision = self._check_tes(ctx)
        reasons.extend(tes_decision.reasons)
        cas_dir = self._max_cas(cas_dir, tes_decision.cas_directive)
        severity = self._max_severity(severity, tes_decision.severity)
        if tes_decision.adjust_autonomy:
            adjust_autonomy = tes_decision.adjust_autonomy

        agii_decision = self._check_agii(ctx)
        reasons.extend(agii_decision.reasons)
        cas_dir = self._max_cas(cas_dir, agii_decision.cas_directive)
        severity = self._max_severity(severity, agii_decision.severity)
        if agii_decision.require_human_review:
            require_review = True

        allow = True
        if cas_dir in (CASDirective.PAUSE_AGENT, CASDirective.QUARANTINE_AGENT):
            allow = False
        if severity == Severity.CRITICAL:
            allow = False

        enforcement_mode = "record_only" if (self.record_only or ctx.dry_run) else "enforce"
        effective_allow = allow
        effective_cas_dir = cas_dir
        if enforcement_mode == "record_only":
            reasons.append("Record-only mode active; action not blocked.")
            effective_allow = True
            effective_cas_dir = CASDirective.NONE

        log_path = self._log_decision(
            ctx=ctx,
            computed_allow=allow,
            effective_allow=effective_allow,
            computed_cas=cas_dir,
            effective_cas=effective_cas_dir,
            severity=severity,
            reasons=reasons,
            enforcement_mode=enforcement_mode,
        )

        return InterceptDecision(
            allow=effective_allow,
            cas_directive=effective_cas_dir,
            severity=severity,
            reasons=reasons,
            require_human_review=require_review,
            adjust_autonomy=adjust_autonomy,
            log_path=log_path,
        )

    def _check_resources(self, ctx: InterceptContext) -> InterceptDecision:
        if not ctx.resources:
            return InterceptDecision(
                allow=True,
                reasons=["No resource snapshot provided; skipping resource check."],
            )

        cpu = ctx.resources.cpu_percent
        ram = ctx.resources.ram_percent
        reasons: List[str] = []
        cas_dir = CASDirective.NONE
        severity = Severity.INFO

        if cpu >= self.resource_limits["cpu_hard"] or ram >= self.resource_limits["ram_hard"]:
            reasons.append(
                f"Resource hard limit exceeded (CPU={cpu:.1f}%, RAM={ram:.1f}%). CAS suggests PAUSE_AGENT."
            )
            cas_dir = CASDirective.PAUSE_AGENT
            severity = Severity.CRITICAL
        elif cpu >= self.resource_limits["cpu_soft"] or ram >= self.resource_limits["ram_soft"]:
            reasons.append(
                f"Resource soft limit exceeded (CPU={cpu:.1f}%, RAM={ram:.1f}%). Proceed with caution."
            )
            severity = Severity.WARNING
        else:
            reasons.append(
                f"Resources within safe bounds (CPU={cpu:.1f}%, RAM={ram:.1f}%)."
            )

        return InterceptDecision(
            allow=True,
            cas_directive=cas_dir,
            severity=severity,
            reasons=reasons,
        )

    def _check_tes(self, ctx: InterceptContext) -> InterceptDecision:
        tes = ctx.tes
        if tes is None:
            return InterceptDecision(
                allow=True,
                reasons=["No TES provided; skipping TES-based autonomy checks."],
            )

        reasons: List[str] = [f"TES={tes:.2f}."]
        cas_dir = CASDirective.NONE
        severity = Severity.INFO
        adjust_autonomy: Optional[str] = None

        if tes < self.tes_thresholds["quarantine"]:
            reasons.append("TES below quarantine threshold; CAS suggests QUARANTINE_AGENT.")
            cas_dir = CASDirective.QUARANTINE_AGENT
            severity = Severity.CRITICAL
            adjust_autonomy = "decrease"
        elif tes < self.tes_thresholds["pause"]:
            reasons.append("TES below pause threshold; CAS suggests PAUSE_AGENT.")
            cas_dir = CASDirective.PAUSE_AGENT
            severity = Severity.CRITICAL
            adjust_autonomy = "decrease"
        elif tes < self.tes_thresholds["rollback_warn"]:
            reasons.append("TES below rollback warning; consider rollback/escalated review.")
            severity = Severity.WARNING
            adjust_autonomy = "decrease"
        elif tes >= self.tes_thresholds["autonomy_increase"]:
            reasons.append("TES high; eligible for autonomy increase subject to governance approval.")
            adjust_autonomy = "increase"
        else:
            reasons.append("TES within stable operating range.")

        return InterceptDecision(
            allow=True,
            cas_directive=cas_dir,
            severity=severity,
            reasons=reasons,
            adjust_autonomy=adjust_autonomy,
        )

    def _check_agii(self, ctx: InterceptContext) -> InterceptDecision:
        agii = ctx.agii
        reasons: List[str] = []
        require_review = False
        severity = Severity.INFO

        if agii is None:
            reasons.append("No AGII provided; using neutral integrity assumption.")
        else:
            reasons.append(f"AGII={agii:.2f}.")
            if agii < 0.4:
                reasons.append("Low AGII; suggest human review of this agent's behavior.")
                require_review = True
                severity = Severity.WARNING

        return InterceptDecision(
            allow=True,
            reasons=reasons,
            severity=severity,
            require_human_review=require_review,
        )

    def _log_decision(
        self,
        ctx: InterceptContext,
        computed_allow: bool,
        effective_allow: bool,
        computed_cas: CASDirective,
        effective_cas: CASDirective,
        severity: Severity,
        reasons: List[str],
        enforcement_mode: str,
    ) -> Path:
        ts = time.strftime("%Y%m%d-%H%M%S", time.localtime(ctx.timestamp))
        decision_id = f"{ts}-{int(ctx.timestamp * 1000) % 1000:03d}"
        fname = f"{decision_id}_{ctx.agent_name}_{ctx.action_type.name.lower()}.json"
        path = self._resolve_log_dir(ctx) / fname

        record = {
            "decision_id": decision_id,
            "timestamp": ctx.timestamp,
            "phase": ctx.payload_meta.get("phase"),
            "surface": ctx.payload_meta.get("surface"),
            "agent_name": ctx.agent_name,
            "agent_role": ctx.payload_meta.get("agent_role"),
            "autonomy_tier": ctx.payload_meta.get("autonomy_tier"),
            "action_type": ctx.action_type.name,
            "description": ctx.description,
            "tool_name": ctx.tool_name,
            "payload_meta": ctx.payload_meta,
            "correlation_id": ctx.payload_meta.get("correlation_id"),
            "tes": ctx.tes,
            "agii": ctx.agii,
            "cas": ctx.cas,
            "resources": {
                "cpu_percent": ctx.resources.cpu_percent if ctx.resources else None,
                "ram_percent": ctx.resources.ram_percent if ctx.resources else None,
            },
            "decision": {
                "computed_allow": computed_allow,
                "effective_allow": effective_allow,
                "computed_cas_directive": computed_cas.value,
                "effective_cas_directive": effective_cas.value,
                "severity": severity.value,
                "reasons": reasons,
                "enforcement_mode": enforcement_mode,
                "dry_run": ctx.dry_run,
                "record_only": self.record_only,
            },
        }

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
        except Exception:
            pass

        return path

    @staticmethod
    def _max_cas(a: CASDirective, b: CASDirective) -> CASDirective:
        order = [
            CASDirective.NONE,
            CASDirective.PAUSE_AGENT,
            CASDirective.QUARANTINE_AGENT,
            CASDirective.HALT_STATION,
        ]
        return max(a, b, key=lambda x: order.index(x))

    @staticmethod
    def _max_severity(a: Severity, b: Severity) -> Severity:
        order = [Severity.INFO, Severity.WARNING, Severity.CRITICAL]
        return max(a, b, key=lambda x: order.index(x))

    def _resolve_log_dir(self, ctx: InterceptContext) -> Path:
        """
        Route logs to phase/surface-specific subdirectories when provided.
        Falls back to the base log_dir.
        """
        phase = ctx.payload_meta.get("phase") if ctx.payload_meta else None
        surface = ctx.payload_meta.get("surface") if ctx.payload_meta else None

        path = self.log_dir
        if phase:
            path = path / str(phase)
        if surface:
            path = path / str(surface).replace("/", "_")

        path.mkdir(parents=True, exist_ok=True)
        return path
