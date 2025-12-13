"""Execution Engine - Orchestrates autonomous domain execution"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .domains import DomainRegistry
from .escalation import EscalationManager
from .manifest import ManifestSystem
from .schemas import Intent
from .verification import VerificationLoop


class ExecutionEngine:
    """Executes autonomous domains with manifest protection"""
    
    def __init__(self, root, verification: VerificationLoop):
        self.root = root
        self.verification = verification
        self.manifest_system = ManifestSystem(root)
        self.domain_registry = DomainRegistry(root)
        self.escalation = EscalationManager(root)
    
    def execute_intent(self, intent: Intent, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an intent if it matches an autonomous domain"""
        
        # Check if intent requires capabilities we can execute
        for capability in intent.required_capabilities:
            domain = self.domain_registry.get_domain(capability)
            
            if domain and domain.can_execute(state):
                # Create manifest
                manifest_content = {
                    "intent_id": intent.id,
                    "capability": capability,
                    "description": intent.description
                }
                manifest_id = self.manifest_system.create_manifest(intent.id, manifest_content)
                
                # Try to claim manifest
                if not self.manifest_system.claim_manifest(manifest_id):
                    return {
                        "status": "skipped",
                        "reason": "Manifest already claimed by another process"
                    }
                
                # Track execution start
                self.escalation.track_execution(intent.id)
                
                # Execute domain
                try:
                    result = domain.execute(intent)
                    
                    # Verify success
                    verified = self.verification.verify_execution(intent, result)
                    
                    if verified["success"]:
                        self.manifest_system.mark_complete(manifest_id, result)
                        # Clear execution tracker
                        if intent.id in self.escalation.execution_trackers:
                            del self.escalation.execution_trackers[intent.id]
                        return {
                            "status": "done",
                            "manifest_id": manifest_id,
                            "domain": capability,
                            "result": result,
                            "confidence": verified["confidence"]
                        }
                    else:
                        # Rollback if failed
                        rollback_result = domain.rollback(result)
                        self.manifest_system.mark_failed(manifest_id, str(result.get("error", "Unknown")))
                        # Clear execution tracker
                        if intent.id in self.escalation.execution_trackers:
                            del self.escalation.execution_trackers[intent.id]
                        return {
                            "status": "failed",
                            "manifest_id": manifest_id,
                            "domain": capability,
                            "result": result,
                            "rollback": rollback_result
                        }
                
                except Exception as e:
                    self.manifest_system.mark_failed(manifest_id, str(e))
                    # Clear execution tracker
                    if intent.id in self.escalation.execution_trackers:
                        del self.escalation.execution_trackers[intent.id]
                    return {
                        "status": "error",
                        "manifest_id": manifest_id,
                        "error": str(e)
                    }
        
        return {
            "status": "skipped",
            "reason": "No matching autonomous domain"
        }
    
    def can_execute(self, intent: Intent, state: Dict[str, Any]) -> bool:
        """Check if intent can be executed autonomously"""
        for capability in intent.required_capabilities:
            if self.domain_registry.can_execute_domain(capability, state):
                return True
        return False

