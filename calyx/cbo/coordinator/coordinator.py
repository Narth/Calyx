"""Station Calyx Coordinator - Main executive layer"""

from __future__ import annotations
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger("coordinator")

from .escalation import EscalationManager
from .execution import ExecutionEngine
from .intent_pipeline import IntentPipeline
from .schemas import EventEnvelope, Intent
from .state_core import StateCore
from .telemetry import TelemetryIntake
from .verification import VerificationLoop


class Coordinator:
    """Main coordinator orchestrating telemetry → state → intent → execution → verification"""
    
    def __init__(self, root: Path):
        self.root = root
        self.telemetry = TelemetryIntake(root)
        self.state = StateCore(root)
        self.intents = IntentPipeline(root)
        self.verification = VerificationLoop(root)
        self.execution = ExecutionEngine(root, self.verification)
        self.escalation = EscalationManager(root)
    
    def pulse(self) -> Dict[str, Any]:
        """Execute one coordinator pulse"""
        # 1. Reflect: Ingest telemetry
        events = self.telemetry.ingest_recent_events()
        self.state.update_from_events(events)
        
        # 2. Check guardrails
        guardrails = self.state.check_guardrails()
        
        # 3. Expire old intents
        expired_count = self.intents.expire_intents()
        
        # 4. Get prioritized intents
        prioritized = self.intents.get_prioritized_intents(limit=5)
        
        # 5. Check for stalled executions
        stalls = self.escalation.check_stalls()
        if stalls:
            for stall in stalls:
                intent = self.intents.get_intent(stall["intent_id"])
                if intent:
                    escalation_id = self.escalation.escalate(intent, f"Execution stalled for {stall['elapsed_minutes']:.1f} minutes")
                    LOGGER.warning(f"Escalation created: {escalation_id} for stalled intent {stall['intent_id']}")
        
        # 6. Execute autonomous intents (in guide/execute mode)
        executions = []
        if self.state.get_autonomy_mode() in ["guide", "execute"]:
            for intent in prioritized[:2]:  # Limit to 2 parallel
                # Write debug trace for decision
                try:
                    dbg_dir = self.root / "outgoing" / "bridge"
                    dbg_dir.mkdir(parents=True, exist_ok=True)
                    dbg_path = dbg_dir / "coord_debug.log"
                    can_exec = False
                    try:
                        can_exec = self.execution.can_execute(intent, self.state.state)
                    except Exception:
                        LOGGER.exception("can_execute check failed for %s", intent.id)
                    with dbg_path.open('a', encoding='utf-8') as _fh:
                        _fh.write(f"{datetime.now().isoformat()} DEBUG> considering intent={intent.id} autonomy={intent.autonomy_required} can_execute={can_exec}\n")
                except Exception:
                    LOGGER.exception("Failed to write coord debug")

                if self.execution.can_execute(intent, self.state.state):
                    result = self.execution.execute_intent(intent, self.state.state)
                    executions.append({
                        "intent_id": intent.id,
                        "result": result
                    })
                    # Remove executed or errored intents from the queue to avoid re-execution
                    try:
                        if result.get("status") and result.get("status") != "skipped":
                            self.intents.remove_intent(intent.id)
                            try:
                                dbg_path = self.root / "outgoing" / "bridge" / "coord_debug.log"
                                with dbg_path.open('a', encoding='utf-8') as _fh:
                                    _fh.write(f"{datetime.now().isoformat()} DEBUG> removed intent={intent.id} after status={result.get('status')}\n")
                            except Exception:
                                LOGGER.exception("Failed to write coord debug removal")
                    except Exception:
                        LOGGER.exception("Failed to remove intent %s", intent.id)
                    try:
                        dbg_dir = self.root / "outgoing" / "bridge"
                        dbg_path = dbg_dir / "coord_debug.log"
                        with dbg_path.open('a', encoding='utf-8') as _fh:
                            _fh.write(f"{datetime.now().isoformat()} DEBUG> executed intent={intent.id} result_status={result.get('status')}\n")
                    except Exception:
                        LOGGER.exception("Failed to write coord debug after exec")
        
        # 7. Prepare report
        report = {
            "timestamp": datetime.now().isoformat(),
            "events_ingested": len(events),
            "guardrails": guardrails,
            "intents_expired": expired_count,
            "intents_queued": len(self.intents.intents),
            "intents_prioritized": len(prioritized),
            "resource_headroom": self.state.get_resource_headroom(),
            "autonomy_mode": self.state.get_autonomy_mode(),
            "top_intents": [i.to_dict() for i in prioritized[:3]],
            "executions": executions,
            "stalls": stalls,
                "active_escalations": len(self.escalation.get_active_escalations()),
        }
        # Persist report to outgoing/bridge/last_pulse_report.json for diagnostics
        try:
            out_dir = self.root / "outgoing" / "bridge"
            out_dir.mkdir(parents=True, exist_ok=True)
            report_path = out_dir / "last_pulse_report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            LOGGER.exception("Failed to write last_pulse_report.json")

        # Also write a compact execution audit summary for machine watchers
        try:
            out_dir = self.root / "outgoing" / "bridge"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "timestamp": datetime.now().isoformat(),
                "executions": []
            }
            for ex in executions:
                r = ex.get("result") or {}
                summary["executions"].append({
                    "intent_id": ex.get("intent_id"),
                    "status": r.get("status"),
                    "manifest_id": r.get("manifest_id"),
                    "domain": r.get("domain")
                })
            summary_path = out_dir / "execution_audit_summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            LOGGER.exception("Failed to write execution_audit_summary.json")
        # Append auditable execution entries to outgoing/bridge/dialog.log for operator traceability
        try:
            out_dir = self.root / "outgoing" / "bridge"
            out_dir.mkdir(parents=True, exist_ok=True)
            dialog_path = out_dir / "dialog.log"
            with dialog_path.open("a", encoding="utf-8") as fh:
                ts = datetime.now().isoformat()
                for ex in executions:
                    intent_id = ex.get("intent_id")
                    result = ex.get("result") or {}
                    status = result.get("status", "unknown")
                    manifest = result.get("manifest_id")
                    domain = result.get("domain")
                    error = result.get("error")
                    line = f"{ts} COORD> intent={intent_id} status={status}"
                    if manifest:
                        line += f" manifest={manifest}"
                    if domain:
                        line += f" domain={domain}"
                    if error:
                        line += f" error={error}"
                    fh.write(line + "\n")
        except Exception:
            # Do not let auditing failures break coordinator pulse
            LOGGER.exception("Failed to write coordinator execution audit")

        return report
    
    def add_intent(
        self,
        description: str,
        origin: str = "CBO",
        required_capabilities: Optional[List[str]] = None,
        desired_outcome: str = "",
        priority_hint: int = 50,
        autonomy_required: str = "suggest"
    ) -> Optional[str]:
        """Add a new intent"""
        intent_id = f"i-{int(time.time())}"
        
        intent = Intent(
            id=intent_id,
            origin=origin,
            description=description,
            required_capabilities=required_capabilities or [],
            desired_outcome=desired_outcome,
            priority_hint=priority_hint,
            autonomy_required=autonomy_required
        )
        
        if self.intents.add_intent(intent):
            return intent_id
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current coordinator status"""
        return {
            "state": self.state.state,
            "intents_count": len(self.intents.intents),
            "confidence": self.verification.get_all_confidence(),
            "autonomy_mode": self.state.get_autonomy_mode()
        }

