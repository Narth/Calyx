#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 End-to-End Validation
CGPT Sanity Drills - 4 Tests
"""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

sys.path.insert(0, str(Path(__file__).parent))
from intent_system import create_intent, update_intent_status
from diff_generator import generate_diff
from intent_linker import attach_artifacts
from review_orchestrator import route_for_review
from cp17_report_generator import generate_report


def test_aws_secret():
    """Test 1: AWS secret → CP14 must FAIL; CP16 keeps it rejected"""
    print("\n" + "="*60)
    print("SANITY DRILL 1: AWS Secret Injection")
    print("="*60)
    
    # Create intent
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test AWS secret detection",
        change_set=["config.py"],
        risk_level="high",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate diff with AWS secret
    old_content = "config = {}\n"
    new_content = "config = {'aws_secret_access_key': 'ABC123XYZ456DEF789GHI012JKL345MNO678PQR901STU234VWX567YZ890'}\n"
    
    try:
        result = generate_diff(
            intent_id,
            [("config.py", old_content, new_content)],
            "outgoing/proposals"
        )
        print(f"[OK] Diff generated: {intent_id}")
        
        # Attach artifacts
        attach_artifacts(f"outgoing/intents/intents.jsonl")
        
        # Route for review
        status = route_for_review("outgoing/intents/intents.jsonl")
        
        print(f"[OK] Status: {status}")
        return status == "rejected"
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_broken_test():
    """Test 2: assert False in tests → CP18 must FAIL; stays rejected"""
    print("\n" + "="*60)
    print("SANITY DRILL 2: Broken Test Pattern")
    print("="*60)
    
    # Create intent
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test broken test detection",
        change_set=["test_example.py"],
        risk_level="medium",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate diff with broken test
    old_content = "def test_example():\n    assert True\n"
    new_content = "def test_example():\n    assert False\n"
    
    try:
        result = generate_diff(
            intent_id,
            [("test_example.py", old_content, new_content)],
            "outgoing/proposals"
        )
        print(f"[OK] Diff generated: {intent_id}")
        
        # Attach artifacts
        attach_artifacts("outgoing/intents/intents.jsonl")
        
        # Route for review
        status = route_for_review("outgoing/intents/intents.jsonl")
        
        print(f"[OK] Status: {status}")
        return status == "rejected"
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_happy_path():
    """Test 3: Happy path → both PASS → approved_pending_human; no execution"""
    print("\n" + "="*60)
    print("SANITY DRILL 3: Happy Path")
    print("="*60)
    
    # Create intent
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test happy path - valid optimization",
        change_set=["optimize.py"],
        risk_level="low",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate valid diff
    old_content = "def slow_function():\n    return [x*2 for x in range(100)]\n"
    new_content = "def fast_function():\n    return list(map(lambda x: x*2, range(100)))\n"
    
    try:
        result = generate_diff(
            intent_id,
            [("optimize.py", old_content, new_content)],
            "outgoing/proposals"
        )
        print(f"[OK] Diff generated: {intent_id}")
        
        # Attach artifacts
        attach_artifacts("outgoing/intents/intents.jsonl")
        
        # Route for review
        status = route_for_review("outgoing/intents/intents.jsonl")
        
        print(f"[OK] Status: {status}")
        return status == "approved_pending_human"
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_no_execution():
    """Test 4: No exec artifacts anywhere outside /outgoing/* and /logs/*"""
    print("\n" + "="*60)
    print("SANITY DRILL 4: No Execution Artifacts")
    print("="*60)
    
    # Check directories
    check_dirs = [
        "outgoing/proposals",
        "outgoing/reviews",
        "outgoing/intents",
        "logs"
    ]
    
    for dir_path in check_dirs:
        dir_obj = Path(dir_path)
        if dir_obj.exists():
            print(f"[OK] {dir_path} exists")
        else:
            print(f"[WARN] {dir_path} does not exist")
    
    # Verify no execution artifacts
    forbidden_paths = [
        "container",
        "sandbox",
        "execution",
        "deployment"
    ]
    
    all_files = []
    for dir_path in check_dirs:
        dir_obj = Path(dir_path)
        if dir_obj.exists():
            all_files.extend(dir_obj.rglob("*"))
    
    for file_path in all_files:
        if any(forbidden in str(file_path).lower() for forbidden in forbidden_paths):
            print(f"[FAIL] Found forbidden path: {file_path}")
            return False
    
    print("[OK] No execution artifacts found")
    return True


def main():
    print("="*60)
    print("PHASE 1 END-TO-END VALIDATION")
    print("CGPT Sanity Drills")
    print("="*60)
    
    results = {}
    
    # Run drills
    try:
        results["test1"] = test_aws_secret()
    except Exception as e:
        print(f"[FAIL] Test 1 failed: {e}")
        results["test1"] = False
    
    try:
        results["test2"] = test_broken_test()
    except Exception as e:
        print(f"[FAIL] Test 2 failed: {e}")
        results["test2"] = False
    
    try:
        results["test3"] = test_happy_path()
    except Exception as e:
        print(f"[FAIL] Test 3 failed: {e}")
        results["test3"] = False
    
    try:
        results["test4"] = test_no_execution()
    except Exception as e:
        print(f"[FAIL] Test 4 failed: {e}")
        results["test4"] = False
    
    # Summary
    print("\n" + "="*60)
    print("SANITY DRILL SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())

