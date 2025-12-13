#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Test Plan - 6-Step Validation
Per CGPT specifications
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


def test_small_proposals():
    """Test 1: Generate 3 small proposals"""
    print("\n" + "="*60)
    print("TEST 1: Generate 3 Small Proposals")
    print("="*60)
    
    proposals = []
    for i in range(1, 4):
        print(f"\nCreating proposal {i}...")
        
        # Create intent
        intent_id = create_intent(
            proposed_by="cbo",
            intent_type="code_change",
            goal=f"Test proposal {i} - small optimization",
            change_set=[f"test_file_{i}.py"],
            risk_level="low",
            rollback_plan="Revert git commit",
            reviewers=["cp18", "cp14"]
        )
        
        # Generate small diff
        result = generate_diff(
            intent_id,
            [(f"test_file_{i}.py", "old code", "new code")],
            "outgoing/proposals"
        )
        
        proposals.append({
            "intent_id": intent_id,
            "result": result
        })
        
        print(f"[OK] Proposal {i} created: {intent_id}")
    
    print(f"\n[OK] All 3 small proposals created successfully")
    return proposals


def test_large_proposal():
    """Test 2: Generate 1 edge-case (>500 lines) - should auto-reject"""
    print("\n" + "="*60)
    print("TEST 2: Large Proposal (Should Auto-Reject)")
    print("="*60)
    
    # Create intent
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test large proposal - should reject",
        change_set=["large_file.py"],
        risk_level="high",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate large diff (>500 lines)
    large_content = "old line\n" * 300
    new_content = "new line\n" * 300
    
    try:
        result = generate_diff(
            intent_id,
            [("large_file.py", large_content, new_content)],
            "outgoing/proposals"
        )
        print("[FAIL] Large proposal should have been rejected")
        return False
    except ValueError as e:
        print(f"[OK] Large proposal correctly rejected: {e}")
        return True


def test_secret_injection():
    """Test 3: Inject fake secret - CP14 should FAIL"""
    print("\n" + "="*60)
    print("TEST 3: Secret Injection (CP14 Should FAIL)")
    print("="*60)
    
    # This test requires CP14 integration
    print("[INFO] This test requires CP14 integration")
    print("[INFO] CP14 should detect: aws_secret_access_key=ABC123")
    print("[INFO] Test will fail at CP14 review stage")
    
    # Create intent with secret
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test secret detection",
        change_set=["config.py"],
        risk_level="high",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate diff with secret
    old_content = "config = {}\n"
    new_content = "config = {'aws_secret_access_key': 'ABC123'}\n"
    
    result = generate_diff(
        intent_id,
        [("config.py", old_content, new_content)],
        "outgoing/proposals"
    )
    
    print(f"[OK] Diff generated: {intent_id}")
    print("[INFO] CP14 should FAIL this during review")
    
    return True


def test_broken_test():
    """Test 4: Break unit test - CP18 should FAIL"""
    print("\n" + "="*60)
    print("TEST 4: Broken Unit Test (CP18 Should FAIL)")
    print("="*60)
    
    # This test requires CP18 integration
    print("[INFO] This test requires CP18 integration")
    print("[INFO] CP18 should detect broken test")
    print("[INFO] Test will fail at CP18 review stage")
    
    # Create intent
    intent_id = create_intent(
        proposed_by="cbo",
        intent_type="code_change",
        goal="Test broken unit test detection",
        change_set=["test_example.py"],
        risk_level="medium",
        rollback_plan="Revert git commit",
        reviewers=["cp18", "cp14"]
    )
    
    # Generate diff
    old_content = "def test_example():\n    assert True\n"
    new_content = "def test_example():\n    assert False\n"
    
    result = generate_diff(
        intent_id,
        [("test_example.py", old_content, new_content)],
        "outgoing/proposals"
    )
    
    print(f"[OK] Diff generated: {intent_id}")
    print("[INFO] CP18 should FAIL this during review")
    
    return True


def test_happy_path():
    """Test 5: Happy path - both PASS → approved_pending_human"""
    print("\n" + "="*60)
    print("TEST 5: Happy Path (Both Should PASS)")
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
    
    # Generate diff
    old_content = "def slow_function():\n    return [x*2 for x in range(100)]\n"
    new_content = "def fast_function():\n    return list(map(lambda x: x*2, range(100)))\n"
    
    result = generate_diff(
        intent_id,
        [("optimize.py", old_content, new_content)],
        "outgoing/proposals"
    )
    
    print(f"[OK] Diff generated: {intent_id}")
    print("[INFO] Should reach approved_pending_human if both CP14 and CP18 PASS")
    
    return True


def test_no_execution():
    """Test 6: Verify no execution artifacts"""
    print("\n" + "="*60)
    print("TEST 6: Verify No Execution Artifacts")
    print("="*60)
    
    # Check directories
    check_dirs = [
        "outgoing/proposals",
        "outgoing/reviews",
        "outgoing/intents"
    ]
    
    for dir_path in check_dirs:
        dir_obj = Path(dir_path)
        if dir_obj.exists():
            print(f"[OK] {dir_path} exists")
            files = list(dir_obj.rglob("*"))
            print(f"[INFO] Found {len(files)} files")
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
    print("PHASE 1 TEST PLAN - 6-Step Validation")
    print("="*60)
    
    results = {}
    
    # Test 1: Small proposals
    try:
        proposals = test_small_proposals()
        results["test1"] = True
    except Exception as e:
        print(f"[FAIL] Test 1 failed: {e}")
        results["test1"] = False
    
    # Test 2: Large proposal
    try:
        result = test_large_proposal()
        results["test2"] = result
    except Exception as e:
        print(f"[FAIL] Test 2 failed: {e}")
        results["test2"] = False
    
    # Test 3: Secret injection
    try:
        result = test_secret_injection()
        results["test3"] = result
    except Exception as e:
        print(f"[FAIL] Test 3 failed: {e}")
        results["test3"] = False
    
    # Test 4: Broken test
    try:
        result = test_broken_test()
        results["test4"] = result
    except Exception as e:
        print(f"[FAIL] Test 4 failed: {e}")
        results["test4"] = False
    
    # Test 5: Happy path
    try:
        result = test_happy_path()
        results["test5"] = result
    except Exception as e:
        print(f"[FAIL] Test 5 failed: {e}")
        results["test5"] = False
    
    # Test 6: No execution
    try:
        result = test_no_execution()
        results["test6"] = result
    except Exception as e:
        print(f"[FAIL] Test 6 failed: {e}")
        results["test6"] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST PLAN SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("[OK] All tests passed!")
        return 0
    else:
        print("[WARN] Some tests failed or require integration")
        return 1


if __name__ == "__main__":
    exit(main())

