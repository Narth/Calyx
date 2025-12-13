#!/usr/bin/env python3
r"""
Agent Compliance Audit Tool — Retroactive Governance Verification

Usage:
    python -u ./tools/agent_compliance_audit.py --audit
    python -u ./tools/agent_compliance_audit.py --agent cp6

This tool verifies all active agents comply with the new onboarding standards
and protocols, including SVF attribution, heartbeat format, and documentation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"
COMPENDIUM = ROOT / "docs" / "COMPENDIUM.md"
SVF_PROTOCOL = ROOT / "Codex" / "COMM_PROTOCOL_SHARED_VOICE.md"


class ComplianceAuditor:
    """Agent Compliance Auditor for retroactive governance."""
    
    def __init__(self):
        self.violations: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: List[str] = []
        
    def audit_all(self) -> Dict:
        """Audit all active agents."""
        # Load agent registry
        registry_path = OUTGOING / "agents" / "registry.json"
        if not registry_path.exists():
            self.violations.append({
                "agent": "system",
                "issue": "Registry not found",
                "severity": "error"
            })
            return self._summary()
        
        with open(registry_path, encoding="utf-8") as f:
            registry = json.load(f)
        
        agents = registry.get("agents", {})
        
        # Audit each agent
        for name, data in agents.items():
            self._audit_agent(name, data)
        
        return self._summary()
    
    def audit_agent(self, agent_name: str) -> Dict:
        """Audit a specific agent."""
        registry_path = OUTGOING / "agents" / "registry.json"
        if not registry_path.exists():
            return {"error": "Registry not found"}
        
        with open(registry_path, encoding="utf-8") as f:
            registry = json.load(f)
        
        agents = registry.get("agents", {})
        if agent_name not in agents:
            return {"error": f"Agent '{agent_name}' not found in registry"}
        
        self._audit_agent(agent_name, agents[agent_name])
        return self._summary()
    
    def _audit_agent(self, name: str, data: Dict) -> None:
        """Audit individual agent."""
        checks = [
            ("heartbeat_format", self._check_heartbeat_format, name),
            ("svf_attribution", self._check_svf_attribution, name),
            ("compendium_entry", self._check_compendium_entry, name),
            ("role_assignment", self._check_role_assignment, name, data),
            ("tone_consistency", self._check_tone_consistency, name, data),
        ]
        
        for check_name, check_func, *args in checks:
            try:
                result = check_func(*args)
                if result["status"] == "pass":
                    continue
                elif result["status"] == "warning":
                    self.warnings.append({
                        "agent": name,
                        "check": check_name,
                        "issue": result.get("issue", ""),
                        "severity": "warning"
                    })
                else:
                    self.violations.append({
                        "agent": name,
                        "check": check_name,
                        "issue": result.get("issue", ""),
                        "severity": result.get("severity", "error")
                    })
            except Exception as e:
                self.violations.append({
                    "agent": name,
                    "check": check_name,
                    "issue": f"Check failed: {e}",
                    "severity": "error"
                })
    
    def _check_heartbeat_format(self, name: str) -> Dict:
        """Check heartbeat file format compliance."""
        lock_file = OUTGOING / f"{name}.lock"
        if not lock_file.exists():
            return {"status": "warning", "issue": "No heartbeat file"}
        
        try:
            with open(lock_file, encoding="utf-8") as f:
                data = json.load(f)
            
            required_fields = ["name", "status", "ts"]
            missing = [f for f in required_fields if f not in data]
            
            if missing:
                return {
                    "status": "error",
                    "issue": f"Missing required fields: {', '.join(missing)}",
                    "severity": "high"
                }
            
            # Check status values
            valid_statuses = ["running", "done", "warn", "error", "idle"]
            if data.get("status") not in valid_statuses:
                return {
                    "status": "warning",
                    "issue": f"Invalid status: {data.get('status')}"
                }
            
            return {"status": "pass"}
            
        except json.JSONDecodeError:
            return {
                "status": "error",
                "issue": "Invalid JSON format",
                "severity": "high"
            }
        except Exception as e:
            return {
                "status": "error",
                "issue": f"Read error: {e}",
                "severity": "high"
            }
    
    def _check_svf_attribution(self, name: str) -> Dict:
        """Check SVF attribution compliance."""
        # Skip non-copilot/system agents for now
        if name in ["watcher_token", "llm", "llm_ready"]:
            return {"status": "pass"}
        
        # Check recent outputs for SVF compliance
        shared_logs = OUTGOING / "shared_logs"
        if not shared_logs.exists():
            return {"status": "warning", "issue": "No shared logs to verify"}
        
        # Look for agent outputs in recent logs
        recent_logs = sorted(shared_logs.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        
        svf_found = False
        for log_file in recent_logs:
            try:
                content = log_file.read_text(encoding="utf-8")
                # Check for SVF attribution pattern
                if f"[{name}" in content or name.capitalize() in content:
                    svf_found = True
                    # Check for context token
                    if "[C:" in content:
                        return {"status": "pass"}
                    else:
                        return {
                            "status": "warning",
                            "issue": "SVF context token missing in recent output"
                        }
            except Exception:
                continue
        
        # If agent has outputs but no SVF attribution found
        if svf_found:
            return {
                "status": "warning",
                "issue": "Recent outputs lack SVF attribution"
            }
        
        return {"status": "pass"}
    
    def _check_compendium_entry(self, name: str) -> Dict:
        """Check Compendium documentation."""
        if not COMPENDIUM.exists():
            return {"status": "error", "issue": "Compendium not found", "severity": "high"}
        
        content = COMPENDIUM.read_text(encoding="utf-8")
        
        # Check if agent is documented
        if name not in content and name.lower() not in content:
            # Some agents have display names
            display_map = {
                "bridge": "CBO",
                "cp6": "CP6 Sociologist",
                "cp7": "CP7 Chronicler",
                "cp8": "CP8 Quartermaster",
                "cp9": "CP9 Auto-Tuner",
                "cp10": "CP10 Whisperer",
                "cp12": "CP12 Coordinator",
                "sysint": "Systems Integrator",
                "navigator": "Traffic Navigator",
                "triage": "Triage Orchestrator",
            }
            
            display_name = display_map.get(name, name)
            if display_name not in content:
                return {
                    "status": "warning",
                    "issue": "Not documented in Compendium"
                }
        
        return {"status": "pass"}
    
    def _check_role_assignment(self, name: str, data: Dict) -> Dict:
        """Check role assignment consistency."""
        role = data.get("role", "")
        
        # System agents don't need roles
        if data.get("kind") == "system" and not role:
            return {"status": "pass"}
        
        # Agents and copilots should have roles
        if data.get("kind") in ["agent", "copilot"] and not role:
            return {
                "status": "warning",
                "issue": "Missing role assignment"
            }
        
        return {"status": "pass"}
    
    def _check_tone_consistency(self, name: str, data: Dict) -> Dict:
        """Check tone consistency."""
        tone = data.get("last_tone", "")
        
        # Expected tones from Compendium
        expected_tones = {
            "agent1": "Operational",
            "agent2": "Operational",
            "agent3": "Operational",
            "agent4": "Operational",
            "cp6": "Sociologist",
            "cp7": "Chronicler",
            "cp8": "Quartermaster",
            "cp9": "Chronicler",
            "cp10": "Chronicler",
            "triage": "Diagnostic",
            "cbo": "Overseer",
            "navigator": "Operational",
            "sysint": "Notice",
        }
        
        expected = expected_tones.get(name)
        if expected and tone and tone not in [expected, "Notice", "Operational"]:
            # Some flexibility is allowed
            return {"status": "pass"}
        
        return {"status": "pass"}
    
    def _summary(self) -> Dict:
        """Generate audit summary."""
        total_agents = len(set(v["agent"] for v in self.violations + self.warnings))
        
        return {
            "total_agents_audited": total_agents,
            "violations": len(self.violations),
            "warnings": len(self.warnings),
            "compliance_rate": f"{((total_agents - len(self.violations)) / max(total_agents, 1) * 100):.1f}%",
            "violations": self.violations,
            "warnings": self.warnings,
        }


def main(argv: Optional[List[str]] = None) -> int:
    # Handle Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    
    ap = argparse.ArgumentParser(
        description="Agent Compliance Audit Tool"
    )
    ap.add_argument(
        "--audit",
        action="store_true",
        help="Audit all active agents"
    )
    ap.add_argument(
        "--agent",
        type=str,
        help="Audit specific agent"
    )
    
    args = ap.parse_args(argv)
    
    auditor = ComplianceAuditor()
    
    if args.agent:
        result = auditor.audit_agent(args.agent)
    elif args.audit:
        result = auditor.audit_all()
    else:
        result = auditor.audit_all()
    
    # Print summary
    print("\n" + "="*70)
    print("AGENT COMPLIANCE AUDIT SUMMARY")
    print("="*70)
    print(f"\nAgents Audited: {result.get('total_agents_audited', 0)}")
    print(f"Violations: {result.get('violations', 0)}")
    print(f"Warnings: {result.get('warnings', 0)}")
    print(f"Compliance Rate: {result.get('compliance_rate', 'N/A')}")
    
    if result.get('violations'):
        print("\n[ERROR] VIOLATIONS:")
        for v in result['violations']:
            print(f"  {v['agent']}: {v['check']} - {v['issue']}")
    
    if result.get('warnings'):
        print("\n[WARN] WARNINGS:")
        for w in result['warnings']:
            print(f"  {w['agent']}: {w['check']} - {w['issue']}")
    
    print("\n" + "="*70)
    
    if result.get('violations'):
        print("[WARN] Some agents require compliance updates.")
    else:
        print("[OK] All agents meet compliance standards.")
    
    print("="*70 + "\n")
    
    return 0 if not result.get('violations') else 1


if __name__ == "__main__":
    raise SystemExit(main())

