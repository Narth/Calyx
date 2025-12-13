#!/usr/bin/env python3
"""
Clean up teaching system load test agents

Removes load test agent sessions and metrics to optimize learning system.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
AI4ALL_DIR = ROOT / "Projects" / "AI_for_All" / "outgoing" / "ai4all"


def cleanup_load_test_agents(dry_run: bool = False) -> dict:
    """Clean up load test agent files"""
    stats = {
        "sessions_deleted": 0,
        "metrics_deleted": 0,
        "knowledge_files_deleted": 0,
        "errors": []
    }
    
    # Clean session files
    sessions_dir = AI4ALL_DIR / "sessions"
    if sessions_dir.exists():
        for session_file in sessions_dir.glob("load_test_agent_*.json"):
            try:
                if not dry_run:
                    session_file.unlink()
                stats["sessions_deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"Failed to delete {session_file}: {e}")
    
    # Clean metric files
    metrics_dir = AI4ALL_DIR / "metrics" / "snapshots"
    if metrics_dir.exists():
        for metric_file in metrics_dir.glob("load_test_agent_*.json"):
            try:
                if not dry_run:
                    metric_file.unlink()
                stats["metrics_deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"Failed to delete {metric_file}: {e}")
    
    # Clean knowledge files
    knowledge_dir = AI4ALL_DIR / "knowledge"
    if knowledge_dir.exists():
        # Note: We'll leave the main knowledge files intact, just clean agent-specific ones
        for knowledge_file in knowledge_dir.glob("*load_test_agent*.json"):
            try:
                if not dry_run:
                    knowledge_file.unlink()
                stats["knowledge_files_deleted"] += 1
            except Exception as e:
                stats["errors"].append(f"Failed to delete {knowledge_file}: {e}")
    
    return stats


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Clean up teaching system load test agents")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    
    args = ap.parse_args(argv)
    
    print("\n[TEACHING SYSTEM CLEANUP]")
    print("=" * 60)
    
    if args.dry_run:
        print("[DRY RUN MODE] - No files will be deleted")
    
    stats = cleanup_load_test_agents(dry_run=args.dry_run)
    
    print(f"\nSession files: {stats['sessions_deleted']}")
    print(f"Metric files: {stats['metrics_deleted']}")
    print(f"Knowledge files: {stats['knowledge_files_deleted']}")
    
    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"  {error}")
    
    print("=" * 60)
    
    if args.dry_run:
        print("\n[INFO] Run without --dry-run to actually delete files")
    else:
        print("\n[OK] Cleanup complete")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

