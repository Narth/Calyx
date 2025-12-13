#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Smoke Test - CGPT Playbook
Tests A, B, C with expected outcomes
"""
from __future__ import annotations

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"
REVIEWS_DIR = ROOT / "outgoing" / "reviews"
REPORTS_DIR = ROOT / "outgoing" / "reports"
INTENTS_DIR = ROOT / "outgoing" / "intents"


def check_prechecks():
    """Pre-check: Verify all required files exist"""
    print("\n" + "="*60)
    print("PRECHECKS")
    print("="*60)
    
    checks = [
        ("tools/review_orchestrator.py", ROOT / "tools" / "review_orchestrator.py"),
        ("tools/cp14_sentinel.py", ROOT / "tools" / "cp14_sentinel.py"),
        ("tools/cp18_validator.py", ROOT / "tools" / "cp18_validator.py"),
        ("outgoing/policies/scan_rules.yaml", ROOT / "outgoing" / "policies" / "scan_rules.yaml"),
        ("outgoing/policies/validation_rules.yaml", ROOT / "outgoing" / "policies" / "validation_rules.yaml"),
    ]
    
    all_pass = True
    for name, path in checks:
        if path.exists():
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name} not found")
            all_pass = False
    
    # Check directories
    dirs = [PROPOSALS_DIR, REVIEWS_DIR, REPORTS_DIR, ROOT / "logs" / "svf_audit"]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Directory exists/writable: {dir_path}")
    
    return all_pass


def test_a_happy_path():
    """Test A: Happy Path - both PASS → approved_pending_human"""
    print("\n" + "="*60)
    print("TEST A: Happy Path")
    print("="*60)
    
    intent_id = f"INT-SMOKE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Create minimal diff
    old_content = "def add(a,b): return a+b\n"
    new_content = 'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'
    
    print(f"Intent ID: {intent_id}")
    
    # Generate diff
    try:
        from diff_generator import generate_diff
        result = generate_diff(
            intent_id,
            [("test_file.py", old_content, new_content)],
            str(PROPOSALS_DIR)
        )
        print(f"[OK] Diff generated: {result['output_dir']}")
    except Exception as e:
        print(f"[FAIL] Diff generation failed: {e}")
        return False
    
    # Create intent.json in proposals directory
    intent_file = PROPOSALS_DIR / intent_id / "intent.json"
    intent_data = {
        "intent_id": intent_id,
        "proposed_by": "cbo",
        "goal": "Add docstring to function",
        "change_set": ["test_file.py"],
        "risk_level": "low",
        "reviewers": ["cp14", "cp18"],
        "tests_reference": ["test_file.py::test_add"],
        "status": "under_review"
    }
    intent_file.write_text(json.dumps(intent_data, indent=2), encoding="utf-8")
    print(f"[OK] Intent created: {intent_file}")
    
    # Run processors
    print("\nRunning CP14 processor...")
    cp14_cmd = [
        "python", "tools/cp14_sentinel.py",
        "--patch", str(PROPOSALS_DIR / intent_id / "change.patch"),
        "--metadata", str(PROPOSALS_DIR / intent_id / "metadata.json"),
        "--intent-id", intent_id,
    ]
    cp14_result = subprocess.run(cp14_cmd, capture_output=True, text=True)
    print(f"CP14 output: {cp14_result.stdout[:200]}")
    
    print("\nRunning CP18 processor...")
    cp18_cmd = [
        "python", "tools/cp18_validator.py",
        "--patch", str(PROPOSALS_DIR / intent_id / "change.patch"),
        "--metadata", str(PROPOSALS_DIR / intent_id / "metadata.json"),
        "--intent-id", intent_id,
    ]
    cp18_result = subprocess.run(cp18_cmd, capture_output=True, text=True)
    print(f"CP18 output: {cp18_result.stdout[:200]}")
    
    # Check verdicts
    cp14_verdict_file = REVIEWS_DIR / f"{intent_id}.CP14.verdict.json"
    cp18_verdict_file = REVIEWS_DIR / f"{intent_id}.CP18.verdict.json"
    
    if not cp14_verdict_file.exists():
        print("[FAIL] CP14 verdict file not found")
        return False
    
    if not cp18_verdict_file.exists():
        print("[FAIL] CP18 verdict file not found")
        return False
    
    cp14_verdict = json.loads(cp14_verdict_file.read_text())
    cp18_verdict = json.loads(cp18_verdict_file.read_text())
    
    print(f"\nCP14 Verdict: {cp14_verdict.get('verdict')}")
    print(f"CP18 Verdict: {cp18_verdict.get('verdict')}")
    
    if cp14_verdict.get('verdict') == 'PASS' and cp18_verdict.get('verdict') == 'PASS':
        print("[OK] Both passed - expected approved_pending_human")
        return True
    else:
        print("[FAIL] Expected both PASS")
        return False


def test_b_security_fail():
    """Test B: Security FAIL - CP14 blocks proposal"""
    print("\n" + "="*60)
    print("TEST B: Security FAIL")
    print("="*60)
    
    intent_id = f"INT-SMOKE-SECRET-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Create diff with fake secret
    old_content = "config = {}\n"
    new_content = 'config = {"aws_secret_access_key": "FAKEABC123XYZFAKEABC123XYZ"}\n'
    
    print(f"Intent ID: {intent_id}")
    
    # Generate diff
    try:
        from diff_generator import generate_diff
        result = generate_diff(
            intent_id,
            [("config.py", old_content, new_content)],
            str(PROPOSALS_DIR)
        )
        print(f"[OK] Diff generated: {result['output_dir']}")
    except Exception as e:
        print(f"[FAIL] Diff generation failed: {e}")
        return False
    
    # Create intent.json
    intent_file = PROPOSALS_DIR / intent_id / "intent.json"
    intent_data = {
        "intent_id": intent_id,
        "proposed_by": "cbo",
        "goal": "Test secret detection",
        "change_set": ["config.py"],
        "risk_level": "high",
        "reviewers": ["cp14", "cp18"],
        "tests_reference": ["test_config.py"],
        "status": "under_review"
    }
    intent_file.write_text(json.dumps(intent_data, indent=2), encoding="utf-8")
    
    # Run CP14 processor
    print("\nRunning CP14 processor...")
    cp14_cmd = [
        "python", "tools/cp14_sentinel.py",
        "--patch", str(PROPOSALS_DIR / intent_id / "change.patch"),
        "--metadata", str(PROPOSALS_DIR / intent_id / "metadata.json"),
        "--intent-id", intent_id,
    ]
    cp14_result = subprocess.run(cp14_cmd, capture_output=True, text=True)
    print(f"CP14 output: {cp14_result.stdout[:200]}")
    
    # Check verdict
    cp14_verdict_file = REVIEWS_DIR / f"{intent_id}.CP14.verdict.json"
    if not cp14_verdict_file.exists():
        print("[FAIL] CP14 verdict file not found")
        return False
    
    cp14_verdict = json.loads(cp14_verdict_file.read_text())
    print(f"\nCP14 Verdict: {cp14_verdict.get('verdict')}")
    print(f"Findings: {len(cp14_verdict.get('findings', []))}")
    
    if cp14_verdict.get('verdict') == 'FAIL':
        print("[OK] CP14 FAIL - expected rejected")
        return True
    else:
        print("[FAIL] Expected CP14 FAIL")
        return False


def test_c_validation_fail():
    """Test C: Validation FAIL - CP18 blocks proposal"""
    print("\n" + "="*60)
    print("TEST C: Validation FAIL")
    print("="*60)
    
    intent_id = f"INT-SMOKE-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Create diff with broken test
    old_content = "def test_example():\n    assert True\n"
    new_content = "def test_example():\n    assert False\n"
    
    print(f"Intent ID: {intent_id}")
    
    # Generate diff
    try:
        from diff_generator import generate_diff
        result = generate_diff(
            intent_id,
            [("test_example.py", old_content, new_content)],
            str(PROPOSALS_DIR)
        )
        print(f"[OK] Diff generated: {result['output_dir']}")
    except Exception as e:
        print(f"[FAIL] Diff generation failed: {e}")
        return False
    
    # Create intent.json
    intent_file = PROPOSALS_DIR / intent_id / "intent.json"
    intent_data = {
        "intent_id": intent_id,
        "proposed_by": "cbo",
        "goal": "Test validation detection",
        "change_set": ["test_example.py"],
        "risk_level": "medium",
        "reviewers": ["cp14", "cp18"],
        "tests_reference": ["test_example.py::test_example"],
        "status": "under_review"
    }
    intent_file.write_text(json.dumps(intent_data, indent=2), encoding="utf-8")
    
    # Run CP18 processor
    print("\nRunning CP18 processor...")
    cp18_cmd = [
        "python", "tools/cp18_validator.py",
        "--patch", str(PROPOSALS_DIR / intent_id / "change.patch"),
        "--metadata", str(PROPOSALS_DIR / intent_id / "metadata.json"),
        "--intent-id", intent_id,
    ]
    cp18_result = subprocess.run(cp18_cmd, capture_output=True, text=True)
    print(f"CP18 output: {cp18_result.stdout[:200]}")
    
    # Check verdict
    cp18_verdict_file = REVIEWS_DIR / f"{intent_id}.CP18.verdict.json"
    if not cp18_verdict_file.exists():
        print("[FAIL] CP18 verdict file not found")
        return False
    
    cp18_verdict = json.loads(cp18_verdict_file.read_text())
    print(f"\nCP18 Verdict: {cp18_verdict.get('verdict')}")
    
    if cp18_verdict.get('verdict') == 'FAIL':
        print("[OK] CP18 FAIL - expected rejected")
        return True
    else:
        print("[FAIL] Expected CP18 FAIL")
        return False


def main():
    print("="*60)
    print("PHASE 1 SMOKE TEST - CGPT Playbook")
    print("="*60)
    
    results = {}
    
    # Pre-checks
    if not check_prechecks():
        print("\n[FAIL] Pre-checks failed")
        return 1
    
    # Test A: Happy Path
    try:
        results["test_a"] = test_a_happy_path()
    except Exception as e:
        print(f"[FAIL] Test A failed: {e}")
        results["test_a"] = False
    
    # Test B: Security FAIL
    try:
        results["test_b"] = test_b_security_fail()
    except Exception as e:
        print(f"[FAIL] Test B failed: {e}")
        results["test_b"] = False
    
    # Test C: Validation FAIL
    try:
        results["test_c"] = test_c_validation_fail()
    except Exception as e:
        print(f"[FAIL] Test C failed: {e}")
        results["test_c"] = False
    
    # Summary
    print("\n" + "="*60)
    print("SMOKE TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n[GO] Phase-1 Shadow Mode validated")
        return 0
    else:
        print("\n[NO-GO] Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())

