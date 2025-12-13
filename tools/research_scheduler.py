#!/usr/bin/env python3
"""
Research Mode Scheduler - Optimized for TES improvement
Generates TES-focused goals based on current performance metrics
"""

from __future__ import annotations
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent


class ResearchScheduler:
    """Generates research-optimized goals for TES improvement."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (ROOT / "config.yaml")
        self.config = self._load_config()
        self.research_config = self.config.get("settings", {}).get("scheduler", {}).get("research_mode", {})
        self.goal_templates = self.research_config.get("goal_templates", {})
        self.tes_thresholds = self.research_config.get("tes_thresholds", {})

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def get_current_tes_metrics(self) -> Dict[str, float]:
        """Get current TES metrics from CSV."""
        csv_path = ROOT / "logs" / "agent_metrics.csv"
        if not csv_path.exists():
            return {}

        try:
            import csv
            metrics_list = []
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    metrics_list.append({
                        "tes": float(row.get("tes", 0)),
                        "stability": float(row.get("stability", 0)),
                        "velocity": float(row.get("velocity", 0)),
                        "footprint": float(row.get("footprint", 0)),
                    })

            if metrics_list:
                # Get mean of last 20 runs
                recent = metrics_list[-20:]
                return {
                    "tes": sum(m["tes"] for m in recent) / len(recent),
                    "stability": sum(m["stability"] for m in recent) / len(recent),
                    "velocity": sum(m["velocity"] for m in recent) / len(recent),
                    "footprint": sum(m["footprint"] for m in recent) / len(recent),
                }
        except Exception:
            pass

        return {}

    def determine_focus_area(self) -> str:
        """Determine which TES component needs most improvement."""
        metrics = self.get_current_tes_metrics()
        if not metrics:
            return "balanced"

        # Get target thresholds
        stability_target = self.tes_thresholds.get("stability_target", 0.85)
        velocity_target = self.tes_thresholds.get("velocity_target", 0.70)
        footprint_target = self.tes_thresholds.get("footprint_target", 0.70)

        current_stability = metrics.get("stability", 0)
        current_velocity = metrics.get("velocity", 0)
        current_footprint = metrics.get("footprint", 0)

        # Calculate gaps
        gaps = {
            "stability": stability_target - current_stability,
            "velocity": velocity_target - current_velocity,
            "footprint": footprint_target - current_footprint,
        }

        # Prioritize if research mode config says so
        if self.research_config.get("execution_strategy", {}).get("prioritize_stability", False):
            if gaps["stability"] > 0:
                return "stability"

        # Return component with largest gap
        largest_gap_component = max(gaps.items(), key=lambda x: x[1])[0]
        if gaps[largest_gap_component] > 0:
            return largest_gap_component

        return "balanced"

    def generate_research_goal(self) -> str:
        """Generate a research-focused goal based on current performance."""
        focus = self.determine_focus_area()
        template = self.goal_templates.get(focus, self.goal_templates.get("balanced", ""))

        if not template:
            # Fallback goal
            return (
                "Research mode: Make one targeted improvement. "
                "Complete in ≤90s with ≤2 files changed. "
                "Target: TES ≥85"
            )

        return template

    def should_use_research_mode(self) -> bool:
        """Determine if research mode should be active."""
        return self.research_config.get("enabled", False) and self.research_config.get("tes_focus", False)

    def get_execution_constraints(self) -> Dict[str, any]:
        """Get execution constraints for research mode."""
        strategy = self.research_config.get("execution_strategy", {})
        return {
            "max_duration_sec": strategy.get("max_duration_sec", 90),
            "max_files_changed": strategy.get("max_files_changed", 2),
            "conservative_first": strategy.get("conservative_first", True),
            "validation_required": strategy.get("validation_required", True),
        }


def generate_research_goal() -> str:
    """Convenience function to generate a research goal."""
    scheduler = ResearchScheduler()
    if scheduler.should_use_research_mode():
        return scheduler.generate_research_goal()
    return ""


if __name__ == "__main__":
    scheduler = ResearchScheduler()
    
    print("=== Research Mode Scheduler ===")
    print(f"Research Mode Enabled: {scheduler.should_use_research_mode()}")
    
    if scheduler.should_use_research_mode():
        metrics = scheduler.get_current_tes_metrics()
        print(f"\nCurrent TES Metrics:")
        print(f"  TES: {metrics.get('tes', 0):.2f}")
        print(f"  Stability: {metrics.get('stability', 0):.2f}")
        print(f"  Velocity: {metrics.get('velocity', 0):.2f}")
        print(f"  Footprint: {metrics.get('footprint', 0):.2f}")
        
        focus = scheduler.determine_focus_area()
        print(f"\nFocus Area: {focus}")
        
        goal = scheduler.generate_research_goal()
        print(f"\nGenerated Goal:")
        print(f"  {goal}")
        
        constraints = scheduler.get_execution_constraints()
        print(f"\nExecution Constraints:")
        print(f"  Max Duration: {constraints['max_duration_sec']}s")
        print(f"  Max Files: {constraints['max_files_changed']}")
        print(f"  Conservative First: {constraints['conservative_first']}")
        print(f"  Validation Required: {constraints['validation_required']}")
    else:
        print("\nResearch mode not enabled in config.yaml")
