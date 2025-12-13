#!/usr/bin/env python3
"""
Knowledge Scorer: Measure agentic intelligence across four dimensions.

Scoring Framework:
- Accuracy (30%): Factual correctness
- Correctness (25%): Logical soundness  
- Informativeness (20%): Usefulness and completeness
- Reasonableness (25%): Contextual appropriateness

Composite Knowledge Score (KS) = Weighted average 0-100
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent


class KnowledgeScorer:
    """Measure and track agentic intelligence"""
    
    def __init__(self):
        self.metrics_dir = ROOT / "outgoing" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.scores_file = self.metrics_dir / "knowledge_scores.csv"
        self.progression_file = self.metrics_dir / "knowledge_progression.json"
        
    def score(
        self,
        agent: str,
        message_id: str,
        accuracy: float,
        correctness: float,
        informativeness: float,
        reasonableness: float,
        reviewer: str = "automated",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Calculate knowledge score from component scores"""
        
        composite = (
            accuracy * 0.30 +
            correctness * 0.25 +
            informativeness * 0.20 +
            reasonableness * 0.25
        )
        
        score_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "message_id": message_id,
            "accuracy": accuracy,
            "correctness": correctness,
            "informativeness": informativeness,
            "reasonableness": reasonableness,
            "composite_score": round(composite, 2),
            "reviewer": reviewer,
            "notes": notes
        }
        
        # Append to CSV
        self._append_csv(score_data)
        
        # Update progression tracking
        self._update_progression(agent, composite)
        
        return score_data
    
    def _append_csv(self, data: Dict[str, Any]) -> None:
        """Append score to CSV file"""
        import csv
        
        # Create file with header if needed
        file_exists = self.scores_file.exists()
        
        with open(self.scores_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
    
    def _update_progression(self, agent: str, score: float) -> None:
        """Update progression tracking"""
        if self.progression_file.exists():
            with open(self.progression_file, 'r') as f:
                progression = json.load(f)
        else:
            progression = {}
        
        if agent not in progression:
            progression[agent] = {
                "scores": [],
                "rolling_7d_avg": None,
                "rolling_30d_avg": None,
                "trend": "stable",
                "improvement_rate": 0.0
            }
        
        progression[agent]["scores"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": score
        })
        
        # Keep last 1000 scores
        progression[agent]["scores"] = progression[agent]["scores"][-1000:]
        
        # Calculate rolling averages
        scores_list = [s["score"] for s in progression[agent]["scores"]]
        if len(scores_list) >= 7:
            progression[agent]["rolling_7d_avg"] = round(sum(scores_list[-7:]) / 7, 2)
        if len(scores_list) >= 30:
            progression[agent]["rolling_30d_avg"] = round(sum(scores_list[-30:]) / 30, 2)
        
        # Calculate trend
        if len(scores_list) >= 10:
            recent_avg = sum(scores_list[-5:]) / 5
            previous_avg = sum(scores_list[-10:-5]) / 5
            diff = recent_avg - previous_avg
            
            if diff > 2:
                progression[agent]["trend"] = "improving"
            elif diff < -2:
                progression[agent]["trend"] = "declining"
            else:
                progression[agent]["trend"] = "stable"
            
            progression[agent]["improvement_rate"] = round(diff, 2)
        
        with open(self.progression_file, 'w') as f:
            json.dump(progression, f, indent=2)
    
    def get_agent_stats(self, agent: str) -> Optional[Dict[str, Any]]:
        """Get statistics for an agent"""
        if not self.progression_file.exists():
            return None
        
        with open(self.progression_file, 'r') as f:
            progression = json.load(f)
        
        return progression.get(agent)
    
    def format_score(self, agent: str, message_id: str, accuracy: float, 
                    correctness: float, informativeness: float, reasonableness: float) -> str:
        """Generate formatted score string for SVF messages"""
        score_data = self.score(agent, message_id, accuracy, correctness, 
                               informativeness, reasonableness)
        
        return (f"Knowledge Score: KS={score_data['composite_score']:.0f} "
                f"(Acc:{accuracy:.0f}, Cor:{correctness:.0f}, "
                f"Inf:{informativeness:.0f}, Rea:{reasonableness:.0f})")


def main():
    """Example usage"""
    scorer = KnowledgeScorer()
    
    # Example score
    result = scorer.score(
        agent="agent1",
        message_id="msg_test_001",
        accuracy=92,
        correctness=85,
        informativeness=88,
        reasonableness=82,
        reviewer="automated",
        notes="Test scoring"
    )
    
    print(f"Scored: {result['composite_score']}")
    
    # Get stats
    stats = scorer.get_agent_stats("agent1")
    if stats:
        print(f"Agent1 Stats: {stats}")


if __name__ == "__main__":
    main()

