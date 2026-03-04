"""
Review Agent - Evidence-Based Validation (Not Approval)
Does NOT approve PRs - only summarizes:
- Blast radius
- Suspicious tests
- Policy violations
- Missing evidence

For now, wired as report generator that runs in CI and posts as PR comment if supported,
otherwise writes report to artifacts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ReviewAgent:
    """Review agent - generates evidence-based reports, does not approve."""
    
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self.receipts_path = self.repo_root / "runtime" / "receipts"
        self.results_path = self.repo_root / "runtime" / "benchmarks" / "results"
        self.manifests_path = self.repo_root / "runtime" / "manifests"
    
    def analyze_blast_radius(self, diff_paths: List[str]) -> Dict:
        """Analyze blast radius of changes."""
        governance_paths = ["governance/", "CALYX_CONTRACT.yaml"]
        core_paths = ["calyx/core/", "benchmarks/harness/"]
        docs_paths = ["docs/", "*.md"]
        
        touches_governance = any(
            any(gp in path for gp in governance_paths) for path in diff_paths
        )
        touches_core = any(
            any(cp in path for cp in core_paths) for path in diff_paths
        )
        touches_docs_only = all(
            any(dp in path or path.endswith(".md") for dp in docs_paths) for path in diff_paths
        )
        
        return {
            "touches_governance": touches_governance,
            "touches_core": touches_core,
            "touches_docs_only": touches_docs_only,
            "affected_files_count": len(diff_paths),
            "risk_level": "high" if touches_governance else ("med" if touches_core else "low")
        }
    
    def find_suspicious_tests(self, test_results_path: Optional[Path] = None) -> List[Dict]:
        """Find suspicious test patterns."""
        suspicious = []
        
        # Stub - would analyze test results for:
        # - Skipped tests
        # - Tests that always pass
        # - Tests with no assertions
        # - Tests that mock everything
        
        return suspicious
    
    def check_policy_violations(
        self,
        envelope: Dict,
        contract_path: Path
    ) -> List[Dict]:
        """Check for policy violations."""
        violations = []
        
        # Check task_type is allowed
        task_type = envelope.get("task_type")
        # Would load contract and check allowed_tasks
        
        # Check source is allowed
        source = envelope.get("source")
        if source not in ["discord", "laptop_node"]:
            violations.append({
                "type": "invalid_source",
                "source": source,
                "severity": "high"
            })
        
        # Check stop conditions
        scope_paths = envelope.get("scope", {}).get("paths", [])
        governance_paths = ["governance/", "CALYX_CONTRACT.yaml"]
        if any(gp in str(p) for p in scope_paths for gp in governance_paths):
            if not envelope.get("requires_human_approval") or not envelope.get("approval_token"):
                violations.append({
                    "type": "governance_touch_without_approval",
                    "severity": "high"
                })
        
        return violations
    
    def check_missing_evidence(
        self,
        envelope: Dict,
        receipts_path: Path,
        manifests_path: Path
    ) -> List[str]:
        """Check for missing evidence/receipts."""
        missing = []
        
        task_type = envelope.get("task_type")
        envelope_id = envelope.get("envelope_id")
        
        # Check for hub runner receipt
        hub_receipts = list(receipts_path.glob("hub_runner__*.jsonl"))
        if not hub_receipts:
            missing.append("hub_runner_receipt")
        
        # Check for manifest
        manifests = list(manifests_path.glob("*_manifest.json"))
        if not manifests:
            missing.append("run_manifest")
        
        # Check for task-specific receipts
        # Would check required_receipts from contract based on task_type
        
        return missing
    
    def generate_report(
        self,
        envelope: Dict,
        diff_paths: List[str],
        contract_path: Path
    ) -> Dict:
        """Generate review report."""
        blast_radius = self.analyze_blast_radius(diff_paths)
        suspicious_tests = self.find_suspicious_tests()
        policy_violations = self.check_policy_violations(envelope, contract_path)
        missing_evidence = self.check_missing_evidence(
            envelope,
            self.receipts_path,
            self.manifests_path
        )
        
        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "envelope_id": envelope.get("envelope_id"),
            "blast_radius": blast_radius,
            "suspicious_tests": suspicious_tests,
            "policy_violations": policy_violations,
            "missing_evidence": missing_evidence,
            "recommendation": "review_required" if policy_violations or missing_evidence else "proceed_with_caution"
        }
        
        return report
    
    def write_report(self, report: Dict, output_path: Path):
        """Write report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def format_pr_comment(self, report: Dict) -> str:
        """Format report as PR comment."""
        lines = [
            "## Review Agent Report",
            "",
            f"**Envelope ID:** `{report['envelope_id']}`",
            "",
            "### Blast Radius",
            f"- Affected files: {report['blast_radius']['affected_files_count']}",
            f"- Touches governance: {report['blast_radius']['touches_governance']}",
            f"- Touches core: {report['blast_radius']['touches_core']}",
            f"- Risk level: {report['blast_radius']['risk_level']}",
            "",
        ]
        
        if report['policy_violations']:
            lines.extend([
                "### Policy Violations",
                ""
            ])
            for violation in report['policy_violations']:
                lines.append(f"- **{violation['type']}** (severity: {violation['severity']})")
            lines.append("")
        
        if report['missing_evidence']:
            lines.extend([
                "### Missing Evidence",
                ""
            ])
            for item in report['missing_evidence']:
                lines.append(f"- {item}")
            lines.append("")
        
        if report['suspicious_tests']:
            lines.extend([
                "### Suspicious Tests",
                ""
            ])
            for test in report['suspicious_tests']:
                lines.append(f"- {test}")
            lines.append("")
        
        lines.append(f"**Recommendation:** {report['recommendation']}")
        
        return "\n".join(lines)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Review Agent")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--envelope", help="Path to envelope JSON")
    parser.add_argument("--diff-paths", nargs="+", help="Changed file paths")
    parser.add_argument("--contract", default="CALYX_CONTRACT.yaml")
    parser.add_argument("--output", help="Output report path")
    parser.add_argument("--pr-comment", action="store_true", help="Output as PR comment")
    args = parser.parse_args()
    
    agent = ReviewAgent(args.repo_root)
    
    # Load envelope
    if args.envelope:
        with open(args.envelope, "r", encoding="utf-8") as f:
            envelope = json.load(f)
    else:
        envelope = {"envelope_id": "test", "task_type": "doc_update", "source": "discord", "scope": {"paths": []}}
    
    diff_paths = args.diff_paths or []
    contract_path = Path(args.contract)
    
    # Generate report
    report = agent.generate_report(envelope, diff_paths, contract_path)
    
    if args.pr_comment:
        print(agent.format_pr_comment(report))
    elif args.output:
        agent.write_report(report, Path(args.output))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
