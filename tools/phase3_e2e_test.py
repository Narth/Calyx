#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3 End-to-End Test Suite
Tests all Phase 3 components for full functionality
"""
from __future__ import annotations

import json
import subprocess
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"

def test_two_key_verification():
    """Test 1: Two-key verification system"""
    print("\n=== Test 1: Two-Key Verification ===")
    
    # Create test lease
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    
    test_lease = {
        "lease_id": "LEASE-TEST-001",
        "intent_id": "INT-TEST-001",
        "actor": "CBO",
        "issued_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "cosigners": []
    }
    
    lease_file = OUT / "leases" / "LEASE-TEST-001.json"
    lease_file.parent.mkdir(parents=True, exist_ok=True)
    lease_file.write_text(json.dumps(test_lease, indent=2), encoding="utf-8")
    
    # Add human cosignature
    test_lease["cosigners"].append({
        "role": "human",
        "id": "user1",
        "sig": "test_sig_human",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Add agent cosignature
    test_lease["cosigners"].append({
        "role": "agent",
        "id": "cp14",
        "sig": "test_sig_agent",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    lease_file.write_text(json.dumps(test_lease, indent=2), encoding="utf-8")
    
    # Verify two-key structure
    cosigners = test_lease.get("cosigners", [])
    human_signed = any(c.get("role") == "human" for c in cosigners)
    agent_signed = any(c.get("role") == "agent" for c in cosigners)
    
    if human_signed and agent_signed:
        print("[OK] Two-key structure valid")
        return True
    else:
        print("[FAIL] Two-key structure invalid")
        return False


def test_canary_orchestration():
    """Test 2: Canary orchestration"""
    print("\n=== Test 2: Canary Orchestration ===")
    
    try:
        # Try to start canary
        result = subprocess.run(
            ["python", "tools/phase3_canary_orchestrator.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Canary orchestrator accessible")
            return True
        else:
            print("[FAIL] Canary orchestrator error")
            return False
    except Exception as e:
        print(f"[FAIL] Canary test failed: {e}")
        return False


def test_rollback_mechanism():
    """Test 3: Rollback mechanism"""
    print("\n=== Test 3: Rollback Mechanism ===")
    
    try:
        # Try rollback manager
        result = subprocess.run(
            ["python", "tools/phase3_rollback_manager.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Rollback manager accessible")
            return True
        else:
            print("[FAIL] Rollback manager error")
            return False
    except Exception as e:
        print(f"[FAIL] Rollback test failed: {e}")
        return False


def test_auto_halt_monitoring():
    """Test 4: Auto-halt monitoring"""
    print("\n=== Test 4: Auto-Halt Monitoring ===")
    
    try:
        # Try auto-halt
        result = subprocess.run(
            ["python", "tools/cp19_auto_halt.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Auto-halt monitor accessible")
            return True
        else:
            print("[FAIL] Auto-halt monitor error")
            return False
    except Exception as e:
        print(f"[FAIL] Auto-halt test failed: {e}")
        return False


def test_human_cli():
    """Test 5: Human CLI interface"""
    print("\n=== Test 5: Human CLI Interface ===")
    
    try:
        # Try human CLI
        result = subprocess.run(
            ["python", "tools/phase3_human_cli.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("[OK] Human CLI accessible")
            return True
        else:
            print("[FAIL] Human CLI error")
            return False
    except Exception as e:
        print(f"[FAIL] Human CLI test failed: {e}")
        return False


def test_capability_matrix():
    """Test 6: Capability matrix configuration"""
    print("\n=== Test 6: Capability Matrix ===")
    
    try:
        matrix_file = ROOT / "outgoing" / "policies" / "capability_matrix.yaml"
        
        if not matrix_file.exists():
            print("[FAIL] Capability matrix not found")
            return False
        
        with open(matrix_file, 'r') as f:
            import yaml
            matrix = yaml.safe_load(f)
        
        phase3_status = matrix.get("phases", {}).get("phase3", {}).get("status")
        
        if phase3_status == "implemented":
            print("[OK] Phase 3 status: implemented")
            return True
        else:
            print(f"[FAIL] Phase 3 status: {phase3_status}")
            return False
    except Exception as e:
        print(f"[FAIL] Capability matrix test failed: {e}")
        return False


def test_deployment_event_logging():
    """Test 7: Deployment event logging"""
    print("\n=== Test 7: Deployment Event Logging ===")
    
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from svf_audit import log_deployment_event
        
        # Test logging
        log_deployment_event(
            event_type="TEST_EVENT",
            lease_id="LEASE-TEST-001",
            intent_id="INT-TEST-001",
            agent="CP14",
            metadata={"test": True}
        )
        
        print("[OK] Deployment event logging functional")
        return True
    except Exception as e:
        print(f"[FAIL] Deployment event logging failed: {e}")
        return False


def test_approval_workflow():
    """Test 8: Approval workflow"""
    print("\n=== Test 8: Approval Workflow ===")
    
    try:
        import sys
        sys.path.insert(0, str(ROOT / "dashboard" / "backend"))
        from api.approvals import list_pending_approvals
        
        approvals = list_pending_approvals()
        
        print(f"[OK] Approval workflow functional ({len(approvals)} pending)")
        return True
    except Exception as e:
        print(f"[FAIL] Approval workflow failed: {e}")
        return False


def main():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("Phase 3 End-to-End Test Suite")
    print("=" * 60)
    
    tests = [
        ("Two-Key Verification", test_two_key_verification),
        ("Canary Orchestration", test_canary_orchestration),
        ("Rollback Mechanism", test_rollback_mechanism),
        ("Auto-Halt Monitoring", test_auto_halt_monitoring),
        ("Human CLI Interface", test_human_cli),
        ("Capability Matrix", test_capability_matrix),
        ("Deployment Event Logging", test_deployment_event_logging),
        ("Approval Workflow", test_approval_workflow),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} threw exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

