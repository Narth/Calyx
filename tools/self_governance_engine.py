#!/usr/bin/env python3
"""
Phase III Track D: Full Self-Governance Engine
Autonomous policy interpretation, self-directed goal setting, and ethical reasoning
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class SelfGovernanceMetrics:
    """SGII (Self-Governance Intelligence Index) tracking"""
    timestamp: datetime
    sgii_score: float  # 0.0-1.0
    policy_compliance: float  # 0.0-1.0
    autonomous_decisions: int
    ethical_reasoning_score: float  # 0.0-1.0
    goal_setting_quality: float  # 0.0-1.0
    independence_level: float  # 0.0-1.0

@dataclass
class GovernancePolicy:
    """Interpreted governance policy"""
    policy_id: str
    interpreted_rules: List[str]
    constraints: List[str]
    autonomy_boundaries: List[str]
    ethical_principles: List[str]
    compliance_score: float

@dataclass
class AutonomousGoal:
    """Self-directed goal"""
    goal_id: str
    title: str
    description: str
    priority: int  # 1-10
    feasibility_score: float  # 0.0-1.0
    ethical_assessment: str
    estimated_resources: Dict[str, float]
    parent_policy: str

class SelfGovernanceEngine:
    """Full self-governance capabilities for Station Calyx"""
    
    def __init__(self):
        self.config_path = ROOT / "config.yaml"
        self.logger = self._setup_logging()
        
        # State tracking
        self.governance_state = {
            "activated": False,
            "activation_time": None,
            "sgii_history": [],
            "autonomous_goals": [],
            "policy_interpretations": [],
            "ethical_decisions": []
        }
        
        # Load existing state
        self._load_state()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger('self_governance')
        logger.setLevel(logging.INFO)
        
        log_dir = ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "self_governance.log")
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def _load_state(self):
        """Load existing governance state"""
        state_file = ROOT / "state" / "self_governance_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    self.governance_state = json.load(f)
                self.logger.info("Loaded existing governance state")
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save governance state"""
        state_file = ROOT / "state" / "self_governance_state.json"
        state_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(state_file, 'w') as f:
                json.dump(self.governance_state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")
    
    def activate(self) -> Dict[str, any]:
        """Activate Track D: Full Self-Governance"""
        self.logger.info("=" * 60)
        self.logger.info("PHASE III TRACK D: FULL SELF-GOVERNANCE ACTIVATION")
        self.logger.info("=" * 60)
        
        activation_result = {
            "timestamp": datetime.now().isoformat(),
            "status": "ACTIVATING",
            "components": []
        }
        
        # Component 1: Policy Interpretation Engine
        self.logger.info("Activating: Policy Interpretation Engine")
        policy_result = self._activate_policy_engine()
        activation_result["components"].append(policy_result)
        
        # Component 2: Self-Directed Goal Setting
        self.logger.info("Activating: Self-Directed Goal Setting")
        goal_result = self._activate_goal_setting()
        activation_result["components"].append(goal_result)
        
        # Component 3: Ethical Reasoning Framework
        self.logger.info("Activating: Ethical Reasoning Framework")
        ethical_result = self._activate_ethical_reasoning()
        activation_result["components"].append(ethical_result)
        
        # Component 4: SGII Tracking
        self.logger.info("Activating: SGII Tracking System")
        sgii_result = self._activate_sgii_tracking()
        activation_result["components"].append(sgii_result)
        
        # Finalize activation
        self.governance_state["activated"] = True
        self.governance_state["activation_time"] = datetime.now().isoformat()
        self._save_state()
        
        activation_result["status"] = "OPERATIONAL"
        sgii_metrics = self.calculate_sgii()
        activation_result["sgii_initial"] = sgii_metrics["sgii"]
        
        self.logger.info("=" * 60)
        self.logger.info(f"TRACK D ACTIVATION COMPLETE - SGII: {sgii_metrics['sgii']:.3f}")
        self.logger.info("=" * 60)
        
        return activation_result
    
    def _activate_policy_engine(self) -> Dict[str, any]:
        """Activate autonomous policy interpretation"""
        # Load policies
        policy_dir = ROOT / "outgoing" / "policies"
        policies = []
        
        for policy_file in policy_dir.glob("*.json"):
            try:
                with open(policy_file, 'r') as f:
                    policy_data = json.load(f)
                    policies.append({
                        "file": policy_file.name,
                        "data": policy_data
                    })
            except Exception as e:
                self.logger.warning(f"Could not load policy {policy_file}: {e}")
        
        # Interpret policies
        interpretations = []
        for policy in policies:
            interpretation = self._interpret_policy(policy["data"])
            interpretations.append(interpretation)
        
        self.governance_state["policy_interpretations"] = interpretations
        
        return {
            "component": "policy_engine",
            "status": "operational",
            "policies_loaded": len(policies),
            "interpretations": len(interpretations)
        }
    
    def _interpret_policy(self, policy_data: Dict) -> Dict[str, any]:
        """Interpret a policy and extract governance rules"""
        interpretation = {
            "policy_id": policy_data.get("version", "unknown"),
            "rules": [],
            "constraints": [],
            "boundaries": [],
            "principles": []
        }
        
        # Extract rules from allowed_actions
        if "allowed_actions" in policy_data:
            interpretation["rules"] = policy_data["allowed_actions"]
        
        # Extract constraints
        if "constraints" in policy_data:
            interpretation["constraints"] = [
                str(k) + ": " + str(v) 
                for k, v in policy_data["constraints"].items()
            ]
        
        # Extract feature boundaries
        if "features" in policy_data:
            interpretation["boundaries"] = list(policy_data["features"].keys())
        
        # Define ethical principles
        interpretation["principles"] = [
            "Ensure safe operation",
            "Maintain system stability",
            "Respect resource constraints",
            "Act in best interest of Station Calyx",
            "Maintain transparency"
        ]
        
        return interpretation
    
    def _activate_goal_setting(self) -> Dict[str, any]:
        """Activate self-directed goal setting"""
        # Define initial autonomous goals
        initial_goals = [
            {
                "goal_id": "sg_d_001",
                "title": "Optimize SGII to ≥0.85",
                "description": "Achieve target self-governance intelligence index",
                "priority": 10,
                "feasibility": 0.85,
                "ethics": "safe - internal optimization",
                "resources": {"cpu": 2, "ram_mb": 50}
            },
            {
                "goal_id": "sg_d_002",
                "title": "Monitor and improve system efficiency",
                "description": "Continuous optimization of resource utilization",
                "priority": 8,
                "feasibility": 0.90,
                "ethics": "safe - monitoring activity",
                "resources": {"cpu": 1, "ram_mb": 25}
            },
            {
                "goal_id": "sg_d_003",
                "title": "Maintain ethical operation standards",
                "description": "Ensure all autonomous decisions comply with ethical principles",
                "priority": 9,
                "feasibility": 0.95,
                "ethics": "essential - governance requirement",
                "resources": {"cpu": 1, "ram_mb": 20}
            }
        ]
        
        self.governance_state["autonomous_goals"] = initial_goals
        
        return {
            "component": "goal_setting",
            "status": "operational",
            "initial_goals": len(initial_goals)
        }
    
    def _activate_ethical_reasoning(self) -> Dict[str, any]:
        """Activate ethical reasoning framework"""
        ethical_framework = {
            "principles": [
                "Safety First: Never compromise system stability",
                "Resource Consciousness: Respect system constraints",
                "Transparency: Log all autonomous decisions",
                "Accountability: Maintain audit trail",
                "Benevolence: Act in best interest of Station Calyx"
            ],
            "decision_criteria": [
                "Does this action compromise safety?",
                "Does this respect resource limits?",
                "Is this action reversible?",
                "Does this align with Station Calyx goals?",
                "Is this action ethical?"
            ],
            "active": True
        }
        
        self.governance_state["ethical_framework"] = ethical_framework
        
        return {
            "component": "ethical_reasoning",
            "status": "operational",
            "principles": len(ethical_framework["principles"])
        }
    
    def _activate_sgii_tracking(self) -> Dict[str, any]:
        """Activate SGII tracking system"""
        initial_metrics = self.calculate_sgii()
        
        return {
            "component": "sgii_tracking",
            "status": "operational",
            "initial_sgii": initial_metrics
        }
    
    def calculate_sgii(self) -> Dict[str, float]:
        """Calculate Self-Governance Intelligence Index"""
        # SGII components
        policy_compliance = 0.8  # Start conservative
        autonomous_capability = 0.7 if self.governance_state["activated"] else 0.3
        ethical_reasoning = 0.9  # Framework active
        goal_setting_quality = 0.8  # Goals defined
        independence_level = 0.75  # Moderate independence
        
        # Weighted SGII calculation
        sgii = (
            policy_compliance * 0.25 +
            autonomous_capability * 0.25 +
            ethical_reasoning * 0.20 +
            goal_setting_quality * 0.15 +
            independence_level * 0.15
        )
        
        metrics = {
            "sgii": sgii,
            "policy_compliance": policy_compliance,
            "autonomous_capability": autonomous_capability,
            "ethical_reasoning": ethical_reasoning,
            "goal_setting_quality": goal_setting_quality,
            "independence_level": independence_level
        }
        
        # Record metrics
        self.governance_state["sgii_history"].append({
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        })
        
        # Keep only recent history
        if len(self.governance_state["sgii_history"]) > 100:
            self.governance_state["sgii_history"] = self.governance_state["sgii_history"][-100:]
        
        return metrics
    
    def make_autonomous_decision(self, decision_context: Dict[str, any]) -> Dict[str, any]:
        """Make an autonomous decision with ethical reasoning"""
        # Evaluate decision against ethical framework
        ethical_assessment = self._assess_ethical_compliance(decision_context)
        
        # Check policy compliance
        policy_compliance = self._check_policy_compliance(decision_context)
        
        # Make decision
        decision = {
            "timestamp": datetime.now().isoformat(),
            "context": decision_context,
            "ethical_assessment": ethical_assessment,
            "policy_compliance": policy_compliance,
            "approved": ethical_assessment["score"] >= 0.7 and policy_compliance >= 0.7,
            "reasoning": self._generate_reasoning(ethical_assessment, policy_compliance)
        }
        
        # Record decision
        self.governance_state["ethical_decisions"].append(decision)
        
        # Keep only recent decisions
        if len(self.governance_state["ethical_decisions"]) > 1000:
            self.governance_state["ethical_decisions"] = self.governance_state["ethical_decisions"][-1000:]
        
        self._save_state()
        
        return decision
    
    def _assess_ethical_compliance(self, context: Dict[str, any]) -> Dict[str, any]:
        """Assess ethical compliance of a decision"""
        score = 0.0
        factors = []
        
        # Check safety
        if context.get("safety_risk", 0) < 0.3:
            score += 0.3
            factors.append("low_safety_risk")
        
        # Check resource impact
        if context.get("resource_impact", "low") in ["low", "medium"]:
            score += 0.3
            factors.append("acceptable_resource_impact")
        
        # Check reversibility
        if context.get("reversible", True):
            score += 0.2
            factors.append("reversible_action")
        
        # Check alignment with goals
        if context.get("goal_alignment", 0) > 0.7:
            score += 0.2
            factors.append("goal_aligned")
        
        return {
            "score": min(1.0, score),
            "factors": factors,
            "assessment": "compliant" if score >= 0.7 else "needs_review"
        }
    
    def _check_policy_compliance(self, context: Dict[str, any]) -> float:
        """Check policy compliance"""
        # Simplified policy compliance check
        actions = context.get("action", "unknown")
        
        # Load current policy
        policy_file = ROOT / "outgoing" / "policies" / "cbo_permissions.json"
        if policy_file.exists():
            try:
                with open(policy_file, 'r') as f:
                    policy = json.load(f)
                    allowed = policy.get("allowed_actions", [])
                    if actions in allowed or len(allowed) == 0:
                        return 1.0
                    else:
                        return 0.5
            except Exception:
                return 0.8  # Default permissive
        
        return 0.8
    
    def _generate_reasoning(self, ethical: Dict, policy: float) -> str:
        """Generate reasoning for a decision"""
        if ethical["score"] >= 0.7 and policy >= 0.7:
            return f"Decision approved: Ethically compliant ({ethical['score']:.2f}) and policy compliant ({policy:.2f})"
        else:
            return f"Decision needs review: Ethical {ethical['score']:.2f}, Policy {policy:.2f}"
    
    def generate_report(self) -> Dict[str, any]:
        """Generate comprehensive self-governance report"""
        sgii_metrics = self.calculate_sgii()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "track_d_status": "operational" if self.governance_state["activated"] else "inactive",
            "activation_time": self.governance_state.get("activation_time"),
            "sgii_metrics": sgii_metrics,
            "autonomous_goals": len(self.governance_state.get("autonomous_goals", [])),
            "policy_interpretations": len(self.governance_state.get("policy_interpretations", [])),
            "ethical_decisions": len(self.governance_state.get("ethical_decisions", [])),
            "recent_decisions": self.governance_state.get("ethical_decisions", [])[-5:]
        }
        
        return report


def main():
    """Main entry point"""
    import argparse
    
    ap = argparse.ArgumentParser(description="Phase III Track D: Self-Governance Engine")
    ap.add_argument("--activate", action="store_true", help="Activate Track D")
    ap.add_argument("--report", action="store_true", help="Generate report")
    ap.add_argument("--sgii", action="store_true", help="Show current SGII")
    
    args = ap.parse_args()
    
    engine = SelfGovernanceEngine()
    
    if args.activate:
        result = engine.activate()
        print(json.dumps(result, indent=2))
        
        # Write report
        report_file = ROOT / "reports" / f"phase_iii_track_d_activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(f"# Phase III Track D Activation Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Activation Result\n\n")
            f.write(f"```json\n{json.dumps(result, indent=2)}\n```\n")
        
        print(f"\nReport written to: {report_file}")
    
    if args.report:
        report = engine.generate_report()
        print(json.dumps(report, indent=2))
    
    if args.sgii:
        metrics = engine.calculate_sgii()
        print(f"SGII: {metrics['sgii']:.3f}")
        print(f"Policy Compliance: {metrics['policy_compliance']:.2f}")
        print(f"Autonomous Capability: {metrics['autonomous_capability']:.2f}")
        print(f"Ethical Reasoning: {metrics['ethical_reasoning']:.2f}")


if __name__ == "__main__":
    main()

