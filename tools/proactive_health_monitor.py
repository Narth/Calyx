#!/usr/bin/env python3
"""
Proactive Health Monitor — Mid-Process Validation
Validates agent functionality during operation, not just at startup/shutdown.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"

class ProactiveHealthMonitor:
    """Mid-process health validation without relying on failures."""
    
    def __init__(self):
        self.state_file = ROOT / "state" / "proactive_health_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
        
    def validate_agent_functionality(self, agent_name: str) -> Dict:
        """Validate agent is functioning as intended during operation."""
        issues = []
        confidence = 1.0
        
        # Check 1: Lock file freshness
        lock_file = OUT / f"{agent_name}.lock"
        if lock_file.exists():
            age = time.time() - lock_file.stat().st_mtime
            if age > 300:  # 5 minutes
                issues.append(f"Lock file stale ({age:.0f}s old)")
                confidence -= 0.3
        else:
            issues.append("Lock file missing")
            confidence -= 0.5
        
        # Check 2: Agent-specific validation
        if agent_name.startswith("agent"):
            # For agents, check they're actually completing tasks
            scheduler_lock = OUT / f"scheduler_{agent_name}.lock"
            if scheduler_lock.exists():
                scheduler_data = json.loads(scheduler_lock.read_text())
                phase = scheduler_data.get("phase", "")
                if phase == "launch" and age > 120:
                    issues.append("Scheduler stuck in launch phase")
                    confidence -= 0.4
            
            # Check for recent agent runs
            if agent_name == "agent1":
                runs = list(OUT.glob("agent_run_*"))
                if runs:
                    latest_run = max(runs, key=lambda p: p.stat().st_mtime)
                    run_age = time.time() - latest_run.stat().st_mtime
                    if run_age > 600:  # 10 minutes
                        issues.append(f"No recent runs ({run_age:.0f}s)")
                        confidence -= 0.2
        
        # Check 3: Memory and state checks
        try:
            lock_data = json.loads(lock_file.read_text())
            # Validate data structure
            if "ts" not in lock_data:
                issues.append("Lock data missing timestamp")
                confidence -= 0.2
            if "status" not in lock_data:
                issues.append("Lock data missing status")
                confidence -= 0.2
        except Exception as e:
            issues.append(f"Lock data invalid: {e}")
            confidence -= 0.3
        
        return {
            "agent": agent_name,
            "confidence": max(0.0, confidence),
            "issues": issues,
            "healthy": confidence >= 0.7,
            "needs_attention": len(issues) > 0
        }
    
    def check_all_agents(self) -> Dict:
        """Check all agents proactively."""
        agents = ["agent1", "agent2", "agent3", "agent4"]
        results = []
        
        for agent in agents:
            result = self.validate_agent_functionality(agent)
            results.append(result)
        
        healthy_count = sum(1 for r in results if r["healthy"])
        total_confidence = sum(r["confidence"] for r in results) / len(results)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "agents_checked": len(results),
            "healthy_agents": healthy_count,
            "unhealthy_agents": len(results) - healthy_count,
            "average_confidence": total_confidence,
            "details": results
        }
    
    def run_health_check(self):
        """Run comprehensive health check."""
        print("[Proactive Health Monitor] Running mid-process validation...")
        
        results = self.check_all_agents()
        
        print(f"\n[Health Status]")
        print(f"  Healthy Agents: {results['healthy_agents']}/{results['agents_checked']}")
        print(f"  Average Confidence: {results['average_confidence']:.2%}")
        
        if results['unhealthy_agents'] > 0:
            print(f"\n[Issues Detected]")
            for detail in results['details']:
                if not detail['healthy']:
                    print(f"  {detail['agent']}: {', '.join(detail['issues'])}")
        
        # Save state
        self.state_file.write_text(json.dumps(results, indent=2))
        
        return results

if __name__ == "__main__":
    monitor = ProactiveHealthMonitor()
    monitor.run_health_check()

