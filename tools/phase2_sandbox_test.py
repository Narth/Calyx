#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 Sandbox Test - Dry Run
Test complete sandbox execution flow
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

sys.path.insert(0, str(Path(__file__).parent))

def test_lease_flow():
    """Test complete lease → execution flow"""
    print("="*60)
    print("PHASE 2 SANDBOX TEST - Dry Run")
    print("="*60)
    
    # Step 1: Issue lease
    print("\n1. Issuing lease...")
    from cp20_issue_lease import issue_lease
    lease_file = issue_lease(
        intent_id="INT-TEST-SANDBOX",
        commands=["python --version"],
        paths=["repo://calyx/tools/*"],
        minutes=5
    )
    print(f"[OK] Lease issued: {lease_file}")
    
    # Step 2: Verify lease
    print("\n2. Verifying lease...")
    from cp14_verify_lease import verify_lease
    is_valid, reason = verify_lease(lease_file)
    if is_valid:
        print(f"[OK] Lease verified: {reason}")
    else:
        print(f"[FAIL] Lease invalid: {reason}")
        return False
    
    # Step 3: Execute in sandbox
    print("\n3. Executing in sandbox...")
    from cp20_sandbox_run import run_in_sandbox
    exit_code = run_in_sandbox(lease_file, "python --version")
    print(f"[OK] Execution complete: exit_code={exit_code}")
    
    # Step 4: Check resources
    print("\n4. Checking resources...")
    from cp19_resource_sentinel import check_lease_resources
    import json
    lease_data = json.loads(Path(lease_file).read_text())
    status = check_lease_resources(lease_data["lease_id"])
    print(f"[OK] Resource status: {status['status']}")
    
    # Step 5: Verify artifacts
    print("\n5. Verifying artifacts...")
    import json
    from pathlib import Path as PathLib
    artifacts_dir = PathLib("outgoing/staging_runs") / lease_data["lease_id"]
    if artifacts_dir.exists():
        print(f"[OK] Artifacts directory exists")
        print(f"Files: {list(artifacts_dir.glob('*'))}")
    else:
        print("[FAIL] Artifacts directory not found")
        return False
    
    print("\n" + "="*60)
    print("SANDBOX TEST COMPLETE")
    print("="*60)
    print("[OK] Lease issued")
    print("[OK] Lease verified")
    print("[OK] Execution completed")
    print("[OK] Resources monitored")
    print("[OK] Artifacts persisted")
    
    return True


if __name__ == "__main__":
    success = test_lease_flow()
    sys.exit(0 if success else 1)

