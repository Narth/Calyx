#!/usr/bin/env python3
"""
Granular TES Tracker - Track Task Execution Score per agent, task type, and phase
Implements per-agent performance tracking to identify weakest links
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


class GranularTESTracker:
    """Track TES metrics at multiple levels of granularity"""
    
    def __init__(self):
        self.metrics_file = ROOT / "logs" / "agent_metrics.csv"
        self.granular_file = ROOT / "logs" / "granular_tes.jsonl"
        self.agent_summary_file = ROOT / "logs" / "agent_tes_summary.json"
        
    def track_task(
        self,
        agent_id: str,
        task_type: str,
        phase: str,
        tes: float,
        duration: float,
        success: bool,
        **kwargs
    ):
        """Track a single task execution"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "task_type": task_type,
            "phase": phase,
            "tes": tes,
            "duration": duration,
            "success": success,
            **kwargs
        }
        
        # Append to granular log
        with self.granular_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_agent_summary(self) -> Dict:
        """Generate summary metrics per agent"""
        if not self.granular_file.exists():
            return {}
        
        # Aggregate data
        agent_data = defaultdict(lambda: {
            "tasks": [],
            "by_task_type": defaultdict(list),
            "by_phase": defaultdict(list)
        })
        
        with self.granular_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    agent_id = entry.get("agent_id", "unknown")
                    agent_data[agent_id]["tasks"].append(entry)
                    agent_data[agent_id]["by_task_type"][entry.get("task_type", "unknown")].append(entry)
                    agent_data[agent_id]["by_phase"][entry.get("phase", "unknown")].append(entry)
                except:
                    continue
        
        # Calculate metrics
        summary = {}
        for agent_id, data in agent_data.items():
            tasks = data["tasks"]
            if not tasks:
                continue
            
            # Overall metrics
            tes_values = [t["tes"] for t in tasks if "tes" in t]
            durations = [t["duration"] for t in tasks if "duration" in t]
            successes = [t["success"] for t in tasks if "success" in t]
            
            # Per-task-type metrics
            task_type_metrics = {}
            for task_type, type_tasks in data["by_task_type"].items():
                type_tes = [t["tes"] for t in type_tasks if "tes" in t]
                task_type_metrics[task_type] = {
                    "count": len(type_tasks),
                    "avg_tes": sum(type_tes) / len(type_tes) if type_tes else 0,
                    "min_tes": min(type_tes) if type_tes else 0,
                    "max_tes": max(type_tes) if type_tes else 0,
                }
            
            # Per-phase metrics
            phase_metrics = {}
            for phase, phase_tasks in data["by_phase"].items():
                phase_tes = [t["tes"] for t in phase_tasks if "tes" in t]
                phase_metrics[phase] = {
                    "count": len(phase_tasks),
                    "avg_tes": sum(phase_tes) / len(phase_tes) if phase_tes else 0,
                }
            
            summary[agent_id] = {
                "overall": {
                    "count": len(tasks),
                    "avg_tes": sum(tes_values) / len(tes_values) if tes_values else 0,
                    "min_tes": min(tes_values) if tes_values else 0,
                    "max_tes": max(tes_values) if tes_values else 0,
                    "success_rate": sum(successes) / len(successes) if successes else 0,
                    "avg_duration": sum(durations) / len(durations) if durations else 0,
                },
                "by_task_type": task_type_metrics,
                "by_phase": phase_metrics,
            }
        
        return summary
    
    def identify_weakest_links(self, threshold: float = 50.0) -> List[Dict]:
        """Identify agents with TES below threshold"""
        summary = self.get_agent_summary()
        weak_links = []
        
        for agent_id, metrics in summary.items():
            overall = metrics.get("overall", {})
            avg_tes = overall.get("avg_tes", 0)
            
            if avg_tes < threshold:
                weak_links.append({
                    "agent_id": agent_id,
                    "avg_tes": avg_tes,
                    "task_count": overall.get("count", 0),
                    "success_rate": overall.get("success_rate", 0),
                    "worst_task_type": self._find_worst_task_type(metrics),
                    "worst_phase": self._find_worst_phase(metrics),
                })
        
        return sorted(weak_links, key=lambda x: x["avg_tes"])
    
    def _find_worst_task_type(self, metrics: Dict) -> Optional[str]:
        """Find task type with lowest TES"""
        by_type = metrics.get("by_task_type", {})
        if not by_type:
            return None
        
        worst = min(by_type.items(), key=lambda x: x[1].get("avg_tes", 0))
        return worst[0] if worst else None
    
    def _find_worst_phase(self, metrics: Dict) -> Optional[str]:
        """Find phase with lowest TES"""
        by_phase = metrics.get("by_phase", {})
        if not by_phase:
            return None
        
        worst = min(by_phase.items(), key=lambda x: x[1].get("avg_tes", 0))
        return worst[0] if worst else None
    
    def generate_report(self) -> str:
        """Generate human-readable report"""
        summary = self.get_agent_summary()
        weak_links = self.identify_weakest_links()
        
        report = ["=" * 70]
        report.append("GRANULAR TES PERFORMANCE REPORT")
        report.append("=" * 70)
        report.append("")
        
        if not summary:
            report.append("No data available yet.")
            return "\n".join(report)
        
        # Overall summary
        report.append("OVERALL AGENT PERFORMANCE")
        report.append("-" * 70)
        report.append(f"{'Agent':<20} {'TES':<10} {'Tasks':<10} {'Success':<10} {'Avg Duration':<15}")
        report.append("-" * 70)
        
        for agent_id, metrics in sorted(summary.items(), key=lambda x: x[1]["overall"]["avg_tes"]):
            overall = metrics["overall"]
            report.append(
                f"{agent_id:<20} "
                f"{overall['avg_tes']:<10.1f} "
                f"{overall['count']:<10} "
                f"{overall['success_rate']*100:<10.1f}% "
                f"{overall['avg_duration']:<15.1f}s"
            )
        
        report.append("")
        
        # Weakest links
        if weak_links:
            report.append("WEAKEST LINKS (TES < 50)")
            report.append("-" * 70)
            for weak in weak_links:
                report.append(f"Agent: {weak['agent_id']}")
                report.append(f"  Average TES: {weak['avg_tes']:.1f}")
                report.append(f"  Task Count: {weak['task_count']}")
                report.append(f"  Success Rate: {weak['success_rate']*100:.1f}%")
                report.append(f"  Worst Task Type: {weak['worst_task_type']}")
                report.append(f"  Worst Phase: {weak['worst_phase']}")
                report.append("")
        
        return "\n".join(report)


def main():
    tracker = GranularTESTracker()
    
    # Generate and save summary
    summary = tracker.get_agent_summary()
    with tracker.agent_summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    # Print report
    report = tracker.generate_report()
    print(report)
    
    # Save report to file
    report_file = ROOT / "reports" / f"granular_tes_report_{datetime.now().strftime('%Y%m%d')}.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()

