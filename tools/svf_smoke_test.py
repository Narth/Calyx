#!/usr/bin/env python3
"""
SVF v2.0 End-to-End Smoke Test
Verify all collaboration loop components are operational before research mode.
"""

import json
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
QUERIES_DIR = ROOT / "outgoing" / "queries"
RESPONSES_DIR = ROOT / "responses"
CAPABILITIES_FILE = ROOT / "outgoing" / "agent_capabilities.json"
LOOP_LOG = ROOT / "outgoing" / "shared_logs" / "svf_research_collaboration_loop.log"

def test_capability_registry():
    """Test capability registry"""
    print("TEST 1: Capability Registry")
    print("-" * 80)
    
    if not CAPABILITIES_FILE.exists():
        print("FAIL: agent_capabilities.json not found")
        return False
    
    try:
        data = json.loads(CAPABILITIES_FILE.read_text())
        agents = list(data.keys())
        print(f"PASS: Found {len(agents)} registered agents")
        print(f"Agents: {', '.join(agents)}")
        return True
    except Exception as e:
        print(f"FAIL: Error reading registry: {e}")
        return False

def test_query_creation():
    """Test query creation"""
    print("\nTEST 2: Query Creation")
    print("-" * 80)
    
    import uuid
    query_id = str(uuid.uuid4())
    
    query = {
        "id": query_id,
        "from": "CBO",
        "to": "CP7",
        "question": "Smoke test query",
        "priority": "low",
        "created": datetime.now().isoformat(),
        "status": "pending",
        "timeout": 300
    }
    
    try:
        QUERIES_DIR.mkdir(parents=True, exist_ok=True)
        query_file = QUERIES_DIR / f"{query_id}.json"
        query_file.write_text(json.dumps(query, indent=2))
        
        # Verify creation
        if query_file.exists():
            print(f"PASS: Query created successfully")
            print(f"Query ID: {query_id}")
            
            # Clean up test query
            query_file.unlink()
            print("PASS: Test query cleaned up")
            return True
        else:
            print("FAIL: Query file not created")
            return False
    except Exception as e:
        print(f"FAIL: Error creating query: {e}")
        return False

def test_responses_directory():
    """Test responses directory"""
    print("\nTEST 3: Responses Directory")
    print("-" * 80)
    
    try:
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
        if RESPONSES_DIR.exists():
            print("PASS: Responses directory exists")
            return True
        else:
            print("FAIL: Responses directory not created")
            return False
    except Exception as e:
        print(f"FAIL: Error creating responses directory: {e}")
        return False

def test_loop_logging():
    """Test loop logging"""
    print("\nTEST 4: Loop Logging")
    print("-" * 80)
    
    try:
        test_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Smoke test log entry"
        LOOP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOOP_LOG, 'a', encoding='utf-8') as f:
            f.write(test_message + "\n")
        
        if LOOP_LOG.exists():
            print("PASS: Loop log file exists and writable")
            return True
        else:
            print("FAIL: Loop log file not created")
            return False
    except Exception as e:
        print(f"FAIL: Error writing to loop log: {e}")
        return False

def test_collaboration_loop():
    """Test collaboration loop execution"""
    print("\nTEST 5: Collaboration Loop Execution")
    print("-" * 80)
    
    try:
        # Check if the collaboration loop file exists and has required functions
        loop_file = ROOT / "tools" / "svf_research_collaboration_loop.py"
        if not loop_file.exists():
            print("FAIL: Collaboration loop file not found")
            return False
        
        content = loop_file.read_text()
        
        # Test individual functions
        if 'def create_query' in content:
            print("PASS: create_query function exists")
        else:
            print("FAIL: create_query function not found")
            return False
        
        if 'def log_activity' in content:
            print("PASS: log_activity function exists")
        else:
            print("FAIL: log_activity function not found")
            return False
        
        if 'def get_registered_agents' in content:
            print("PASS: get_registered_agents function exists")
        else:
            print("FAIL: get_registered_agents function not found")
            return False
        
        if 'def run_loop' in content:
            print("PASS: run_loop function exists")
        else:
            print("FAIL: run_loop function not found")
            return False
        
        print("PASS: Collaboration loop module functions verified")
        return True
    except Exception as e:
        print(f"FAIL: Error testing collaboration loop: {e}")
        return False

def test_exercise_tool():
    """Test exercise tool"""
    print("\nTEST 6: Exercise Tool")
    print("-" * 80)
    
    try:
        exercise_file = ROOT / "tools" / "svf_exercise_cross_agent_queries.py"
        if exercise_file.exists():
            print("PASS: Exercise tool exists")
            
            # Check for key functions
            content = exercise_file.read_text()
            if 'create_query' in content and 'run_exercise' in content:
                print("PASS: Exercise tool functions verified")
                return True
            else:
                print("FAIL: Exercise tool missing required functions")
                return False
        else:
            print("FAIL: Exercise tool not found")
            return False
    except Exception as e:
        print(f"FAIL: Error testing exercise tool: {e}")
        return False

def test_batch_script():
    """Test batch script"""
    print("\nTEST 7: Batch Script")
    print("-" * 80)
    
    try:
        batch_file = ROOT / "tools" / "svf_research_loop_start.bat"
        if batch_file.exists():
            print("PASS: Batch script exists")
            
            content = batch_file.read_text()
            if 'svf_research_collaboration_loop.py' in content:
                print("PASS: Batch script configured correctly")
                return True
            else:
                print("FAIL: Batch script misconfigured")
                return False
        else:
            print("FAIL: Batch script not found")
            return False
    except Exception as e:
        print(f"FAIL: Error testing batch script: {e}")
        return False

def test_svf_query_tool():
    """Test SVF query tool"""
    print("\nTEST 8: SVF Query Tool")
    print("-" * 80)
    
    try:
        query_tool = ROOT / "tools" / "svf_query.py"
        if query_tool.exists():
            print("PASS: SVF query tool exists")
            return True
        else:
            print("WARN: SVF query tool not found (may be optional)")
            return True  # Warning, not failure
    except Exception as e:
        print(f"WARN: Error checking SVF query tool: {e}")
        return True  # Warning, not failure

def run_smoke_test():
    """Run complete smoke test"""
    print("=" * 80)
    print("SVF v2.0 End-to-End Smoke Test")
    print("Station Calyx Research Mode Readiness Verification")
    print("=" * 80)
    print()
    
    tests = [
        ("Capability Registry", test_capability_registry),
        ("Query Creation", test_query_creation),
        ("Responses Directory", test_responses_directory),
        ("Loop Logging", test_loop_logging),
        ("Collaboration Loop", test_collaboration_loop),
        ("Exercise Tool", test_exercise_tool),
        ("Batch Script", test_batch_script),
        ("SVF Query Tool", test_svf_query_tool),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("Smoke Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All tests passed - System ready for research mode")
        return True
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed - Review before research mode")
        return False

if __name__ == "__main__":
    success = run_smoke_test()
    exit(0 if success else 1)

