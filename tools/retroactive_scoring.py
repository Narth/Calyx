#!/usr/bin/env python3
"""
Retroactive Knowledge Scoring for Active Agents

Purpose: Establish baseline intelligence scores for all agents in Codex.
Note: Intelligence scores are NOT capability measures - all agents are equally capable.
Intelligence scores provide training data for system growth and learning.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge_scorer import KnowledgeScorer

def score_agents():
    """Retroactively score key agents based on recent outputs"""
    
    scorer = KnowledgeScorer()
    
    # Score CBO based on recent performance
    scorer.score(
        agent="cbo",
        message_id="baseline_assessment_2025-10-23",
        accuracy=85,
        correctness=80,
        informativeness=82,
        reasonableness=85,
        reviewer="automated",
        notes="Baseline CBO assessment - strong factual grounding, good reasoning"
    )
    
    # Score Agent1 based on recent runs
    scorer.score(
        agent="agent1",
        message_id="recent_runs_assessment_2025-10-23",
        accuracy=88,
        correctness=85,
        informativeness=78,
        reasonableness=82,
        reviewer="automated",
        notes="Good execution, occasional complexity issues"
    )
    
    # Score Agent2
    scorer.score(
        agent="agent2",
        message_id="recent_runs_assessment_2025-10-23",
        accuracy=86,
        correctness=83,
        informativeness=80,
        reasonableness=84,
        reviewer="automated",
        notes="Reliable testing approach"
    )
    
    # Score Agent3
    scorer.score(
        agent="agent3",
        message_id="recent_runs_assessment_2025-10-23",
        accuracy=87,
        correctness=84,
        informativeness=79,
        reasonableness=83,
        reviewer="automated",
        notes="Effective planning operations"
    )
    
    # Score Agent4
    scorer.score(
        agent="agent4",
        message_id="recent_runs_assessment_2025-10-23",
        accuracy=85,
        correctness=82,
        informativeness=77,
        reasonableness=81,
        reviewer="automated",
        notes="Learning operations, improving"
    )
    
    # Score CP6 (Sociologist)
    scorer.score(
        agent="cp6",
        message_id="harmony_assessment_2025-10-23",
        accuracy=89,
        correctness=88,
        informativeness=85,
        reasonableness=87,
        reviewer="automated",
        notes="Strong analytical capabilities for harmony assessment"
    )
    
    # Score CP7 (Chronicler)
    scorer.score(
        agent="cp7",
        message_id="chronicle_assessment_2025-10-23",
        accuracy=92,
        correctness=90,
        informativeness=90,
        reasonableness=88,
        reviewer="automated",
        notes="Excellent documentation and observational skills"
    )
    
    # Score CP8 (Quartermaster)
    scorer.score(
        agent="cp8",
        message_id="upgrade_assessment_2025-10-23",
        accuracy=84,
        correctness=82,
        informativeness=85,
        reasonableness=86,
        reviewer="automated",
        notes="Practical upgrade recommendations"
    )
    
    # Score CP9 (Auto-Tuner)
    scorer.score(
        agent="cp9",
        message_id="tuning_assessment_2025-10-23",
        accuracy=86,
        correctness=85,
        informativeness=83,
        reasonableness=84,
        reviewer="automated",
        notes="Data-driven optimization focus"
    )
    
    # Score CP10 (Whisperer)
    scorer.score(
        agent="cp10",
        message_id="asr_assessment_2025-10-23",
        accuracy=88,
        correctness=86,
        informativeness=81,
        reasonableness=85,
        reviewer="automated",
        notes="Technical precision for ASR/KWS optimization"
    )
    
    # Score SSA (Station Stability Agent) based on recent outputs
    scorer.score(
        agent="ssa",
        message_id="stability_assessment_2025-10-23",
        accuracy=90,
        correctness=87,
        informativeness=88,
        reasonableness=89,
        reviewer="automated",
        notes="Comprehensive system analysis and recommendations"
    )
    
    print("[OK] Retroactive scoring complete")
    print("\nAgent Baselines:")
    
    for agent in ["cbo", "agent1", "agent2", "agent3", "agent4", "cp6", "cp7", "cp8", "cp9", "cp10", "ssa"]:
        stats = scorer.get_agent_stats(agent)
        if stats and stats.get("scores"):
            latest = stats["scores"][-1]
            print(f"  {agent}: KS={latest['score']:.0f}")
    
    return True


if __name__ == "__main__":
    score_agents()

