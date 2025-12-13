#!/usr/bin/env python3
r"""
Agent Onboarding Specialist — Verification and Guidance Tool

Usage:
  python -u .\Scripts\agent_onboarding.py --verify
  python -u .\Scripts\agent_onboarding.py --guide
  python -u .\Scripts\agent_onboarding.py --check-prereqs

This tool helps agents verify their onboarding, check prerequisites, and get
personalized guidance based on their role and system state.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTGOING = ROOT / "outgoing"
LOGS = ROOT / "logs"


class OnboardingSpecialist:
    """Agent Onboarding Specialist for Station Calyx."""
    
    def __init__(self):
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
    def verify(self) -> Tuple[bool, Dict]:
        """Run comprehensive onboarding verification."""
        checks = {
            "docs_read": self._check_docs(),
            "config_exists": self._check_config(),
            "watcher_ready": self._check_watcher(),
            "svf_active": self._check_svf(),
            "heartbeat_working": self._check_heartbeat(),
            "tools_available": self._check_tools(),
            "gates_configured": self._check_gates(),
        }
        
        all_passed = all(checks.values())
        summary = {
            "passed": sum(checks.values()),
            "total": len(checks),
            "checks": checks,
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
        }
        
        return all_passed, summary
    
    def _check_docs(self) -> bool:
        """Verify essential documentation exists."""
        required = [
            "README.md",
            "ARCHITECTURE.md",
            "OPERATIONS.md",
            "docs/AGENT_ONBOARDING.md",
            "docs/COMPENDIUM.md",
            "docs/CBO.md",
            "docs/TRIAGE.md",
            ".github/copilot-instructions.md",
        ]
        
        missing = []
        for doc in required:
            if not (ROOT / doc).exists():
                missing.append(doc)
        
        if missing:
            self.issues.append(f"Missing docs: {', '.join(missing)}")
            return False
        
        self.info.append("[OK] All essential documentation present")
        return True
    
    def _check_config(self) -> bool:
        """Verify config.yaml exists and is valid."""
        config_path = ROOT / "config.yaml"
        if not config_path.exists():
            self.issues.append("config.yaml missing")
            return False
        
        try:
            import yaml
            with open(config_path, encoding="utf-8") as f:
                yaml.safe_load(f)
            self.info.append("[OK] config.yaml valid")
            return True
        except Exception as e:
            self.issues.append(f"config.yaml invalid: {e}")
            return False
    
    def _check_watcher(self) -> bool:
        """Check if Watcher UI can be launched."""
        watcher_script = ROOT / "Scripts" / "agent_watcher.py"
        if not watcher_script.exists():
            self.issues.append("agent_watcher.py missing")
            return False
        
        self.info.append("[OK] Watcher script available")
        return True
    
    def _check_svf(self) -> bool:
        """Check SVF probe availability."""
        svf_probe = ROOT / "tools" / "svf_probe.py"
        if not svf_probe.exists():
            self.issues.append("svf_probe.py missing")
            return False
        
        # Check if SVF is currently active
        svf_lock = OUTGOING / "svf.lock"
        if svf_lock.exists():
            try:
                with open(svf_lock, encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("status") == "running":
                        self.info.append("[OK] SVF probe is active")
                        return True
            except Exception:
                pass
        
        self.warnings.append("SVF probe not currently running (optional)")
        return True  # Not blocking
    
    def _check_heartbeat(self) -> bool:
        """Verify heartbeat tool exists."""
        copilot_hello = ROOT / "tools" / "copilot_hello.py"
        if not copilot_hello.exists():
            self.issues.append("copilot_hello.py missing")
            return False
        
        self.info.append("[OK] Heartbeat tool available")
        return True
    
    def _check_tools(self) -> bool:
        """Check essential agent tools."""
        required_tools = [
            "agent_runner.py",
            "agent_scheduler.py",
            "triage_probe.py",
            "traffic_navigator.py",
            "sys_integrator.py",
        ]
        
        missing = []
        for tool in required_tools:
            if not (ROOT / "tools" / tool).exists():
                missing.append(tool)
        
        if missing:
            self.issues.append(f"Missing tools: {', '.join(missing)}")
            return False
        
        self.info.append("[OK] Essential tools present")
        return True
    
    def _check_gates(self) -> bool:
        """Check gate files exist (they may be ON or OFF)."""
        gates_dir = OUTGOING / "gates"
        required_gates = ["network.ok", "llm.ok", "apply.ok", "gpu.ok"]
        
        existing = []
        for gate in required_gates:
            if (gates_dir / gate).exists():
                existing.append(gate.replace(".ok", ""))
        
        if existing:
            self.info.append(f"[OK] Gates present: {', '.join(existing)}")
        else:
            self.warnings.append("No gate files found (defaults apply)")
        
        return True  # Not blocking
    
    def get_guide(self, agent_name: Optional[str] = None) -> str:
        """Generate personalized onboarding guide."""
        agent_name = agent_name or "new_agent"
        
        guide = f"""
╔══════════════════════════════════════════════════════════════╗
║  Agent Onboarding Guide — Station Calyx                     ║
╚══════════════════════════════════════════════════════════════╝

Welcome, {agent_name}!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: Read Essential Documentation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read these documents in order:
  1. README.md                        (5 min) — Project overview
  2. ARCHITECTURE.md                  (10 min) — System design
  3. OPERATIONS.md                    (15 min) — Commands & workflows
  4. docs/AGENT_ONBOARDING.md         (20 min) — YOUR COMPREHENSIVE GUIDE ⭐
  5. docs/COMPENDIUM.md               (10 min) — Agent roster
  6. docs/CBO.md                      (10 min) — Overseer system
  7. docs/TRIAGE.md                   (10 min) — Change workflow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: Introduce Yourself
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Emit a heartbeat to announce your presence:

  python -u .\\tools\\copilot_hello.py --name {agent_name} --status running --message "Initializing..." --ttl 30

This creates outgoing/{agent_name}.lock visible in the Watcher UI.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: Start Baseline Monitors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep these running to "feel" the system:

1. Watcher UI (essential):
   python -u .\\Scripts\\agent_watcher.py --page-size 10 --hide-idle

2. SVF Probe (continuous):
   python -u .\\tools\\svf_probe.py --interval 5

3. Triage Probe (WSL, adaptive):
   wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/triage_probe.py --interval 2 --adaptive"

4. Traffic Navigator (WSL, control):
   wsl bash -lc "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && python -u tools/traffic_navigator.py --interval 3 --control"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4: Pick Your Domain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

See docs/COMPENDIUM.md for available roles:
  • Orchestration (Agent1, Scheduler, CBO)
  • Monitoring (Triage, Navigator, Manifest, SysInt)
  • Analysis (CP6 Sociologist, CP7 Chronicler, CP8 Quartermaster)
  • Optimization (CP9 Auto-Tuner, CP10 Whisperer)
  • Coordination (CP12 Systems Coordinator)
  • Teaching (AI-for-All Teaching System)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5: Development Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Making changes:
  1. Plan with Agent1:
     python -u .\\Scripts\\agent_console.py --goal "Your change goal"
  
  2. Run triage (A→B→C):
     python -u .\\tools\\triage_orchestrator.py --goal-file outgoing\\goal.txt
  
  3. Review diffs in outgoing/agent_run_*/
  
  4. Apply when safe:
     python -u .\\Scripts\\agent_console.py --goal "..." --apply

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIGURATION REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• ALWAYS modify config.yaml (never hardcode thresholds/paths)
• Use outgoing/gates/*.ok for feature toggles
• Emit heartbeats to outgoing/<name>.lock
• Follow SVF attribution: [Agent • Tone]: "message"
• Tag stability: [HARMONY] when TES > 85
• Tag friction: [RISK] for staleness or heavy runs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUCCESS METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You're succeeding when:
  ✓ TES ≥ 85 for multiple runs
  ✓ Changes applied without human edits (IFCR)
  ✓ Harmony score rising
  ✓ Stable heartbeats (no staleness)
  ✓ Clear SVF attribution
  ✓ No safety violations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GETTING HELP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• CBO: docs/CBO.md for system-level questions
• Watcher: UI to monitor system state
• SVF: outgoing/shared_logs/ for recent activity
• This Tool: Run with --guide anytime
• Human: Ask User1 or CBO directly

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run verification anytime:
  python -u .\\Scripts\\agent_onboarding.py --verify

Welcome aboard — let's make Station Calyx thrive.
"""
        return guide
    
    def print_summary(self, summary: Dict) -> None:
        """Print verification summary."""
        print("\n" + "="*70)
        print("ONBOARDING VERIFICATION SUMMARY")
        print("="*70)
        print(f"\nChecks Passed: {summary['passed']}/{summary['total']}")
        
        if summary['info']:
            print("\n[OK] INFO:")
            for msg in summary['info']:
                print(f"  {msg}")
        
        if summary['warnings']:
            print("\n[WARN] WARNINGS:")
            for msg in summary['warnings']:
                print(f"  {msg}")
        
        if summary['issues']:
            print("\n[ERROR] ISSUES:")
            for msg in summary['issues']:
                print(f"  {msg}")
        
        print("\n" + "="*70)
        
        if summary['passed'] == summary['total']:
            print("[OK] All checks passed! You're ready to contribute.")
        else:
            print("[WARN] Some issues found. Review above and retry.")
        
        print("="*70 + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    # Handle Windows console encoding for emoji
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass  # Python < 3.7
    
    ap = argparse.ArgumentParser(
        description="Agent Onboarding Specialist for Station Calyx"
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help="Run comprehensive onboarding verification"
    )
    ap.add_argument(
        "--guide",
        action="store_true",
        help="Show personalized onboarding guide"
    )
    ap.add_argument(
        "--check-prereqs",
        action="store_true",
        help="Check prerequisites only"
    )
    ap.add_argument(
        "--name",
        default="new_agent",
        help="Agent name for personalized guide"
    )
    
    args = ap.parse_args(argv)
    
    specialist = OnboardingSpecialist()
    
    if args.verify or args.check_prereqs:
        print("\n[INFO] Running onboarding verification...\n")
        passed, summary = specialist.verify()
        specialist.print_summary(summary)
        return 0 if passed else 1
    
    if args.guide:
        print(specialist.get_guide(args.name))
        return 0
    
    # Default: show guide
    print(specialist.get_guide(args.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

