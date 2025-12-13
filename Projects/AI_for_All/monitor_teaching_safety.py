#!/usr/bin/env python3
"""
Teaching Safety Monitor - Real-time monitoring of teaching system safety
Run this script to monitor daily caps, sentinels, and pattern status
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add teaching module to path
sys.path.insert(0, str(Path(__file__).parent))

from teaching.teaching_safety_system import TeachingSafetySystem


def print_header():
    """Print monitoring header"""
    print("=" * 70)
    print("Teaching Safety System Monitor")
    print("Station Calyx - AI-for-All Teaching")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    print()


def print_guardrails(status):
    """Print guardrails status"""
    print("DAILY CAPS STATUS")
    print("-" * 70)
    
    guardrails = status['guardrails']
    
    for cap_type in ['new_patterns', 'synth_combos', 'causal_claims']:
        cap_data = guardrails[cap_type]
        used = cap_data['used']
        limit = cap_data['limit']
        remaining = cap_data['remaining']
        percent = (used / limit * 100) if limit > 0 else 0
        
        # Status indicator
        if percent >= 90:
            indicator = "[CRITICAL]"
        elif percent >= 75:
            indicator = "[WARNING]"
        else:
            indicator = "[OK]"
        
        print(f"{cap_type.replace('_', ' ').title():20} {used:3}/{limit:3} used ({remaining:3} remaining) {percent:5.1f}% {indicator}")
    
    print()


def print_sentinels(status):
    """Print sentinel status"""
    print("SENTINEL MONITORING")
    print("-" * 70)
    
    sentinels = status['sentinels']
    total = sentinels['total_sentinels']
    healthy = sentinels['healthy_count']
    alerts = sentinels['alert_count']
    
    if total == 0:
        print("No sentinels configured")
    else:
        print(f"Total Sentinels: {total}")
        print(f"Healthy: {healthy}")
        print(f"Alerts: {alerts}")
        
        if alerts > 0:
            print("[WARNING] Sentinel alerts detected")
        else:
            print("[OK] All sentinels healthy")
    
    print()


def print_patterns(status):
    """Print pattern summary"""
    print("PATTERN STATUS")
    print("-" * 70)
    
    patterns = status['patterns']
    total = patterns['total_patterns']
    active = patterns['active']
    quarantine = patterns['quarantine']
    archived = patterns['archived']
    
    print(f"Total Patterns: {total}")
    print(f"  Active:      {active:3}")
    print(f"  Quarantine:  {quarantine:3}")
    print(f"  Archived:    {archived:3}")
    
    print()


def print_safety_level(status):
    """Print overall safety level"""
    print("SAFETY LEVEL")
    print("-" * 70)
    
    level = status['safety_level']
    
    if level == 'safe':
        print("[SAFE] All systems operating within normal parameters")
    elif level == 'caution':
        print("[CAUTION] Some resource usage approaching limits")
    elif level == 'warning':
        print("[WARNING] Resource usage high, monitor closely")
    
    print()


def main():
    """Main monitoring function"""
    try:
        # Initialize safety system
        safety_system = TeachingSafetySystem()
        
        # Get status
        status = safety_system.monitor_system_status()
        
        # Print report
        print_header()
        print_guardrails(status)
        print_sentinels(status)
        print_patterns(status)
        print_safety_level(status)
        
        # Print footer
        print("=" * 70)
        print("Monitoring complete")
        print("Run again to refresh status")
        print("=" * 70)
        
        # Return JSON status for programmatic access
        return status
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
