#!/usr/bin/env python3
"""
Test script for the Calyx Terminal workflow:
Bat file -> Wake command -> Journal entry command -> Software launch -> Transcription
"""

import subprocess
import time
import sys
import os

def test_workflow():
    print("=== Calyx Terminal Workflow Test ===")
    print()
    
    # Test 1: Check if bat file exists
    print("1. Testing bat file...")
    bat_path = "Scripts\\Calyx-Launch.bat"
    if os.path.exists(bat_path):
        print(f"   [OK] Bat file exists: {bat_path}")
    else:
        print(f"   [FAIL] Bat file missing: {bat_path}")
        return False
    
    # Test 2: Check if wake listener exists
    print("2. Testing wake listener...")
    wake_path = "Scripts\\listener_wake.py"
    if os.path.exists(wake_path):
        print(f"   [OK] Wake listener exists: {wake_path}")
    else:
        print(f"   [FAIL] Wake listener missing: {wake_path}")
        return False
    
    # Test 3: Check if command router has journal commands
    print("3. Testing command router...")
    try:
        with open("Scripts\\command_router.py", "r") as f:
            content = f.read()
            if "create_journal_entry" in content and "start_transcription" in content:
                print("   [OK] Command router has journal commands")
            else:
                print("   [FAIL] Command router missing journal commands")
                return False
    except Exception as e:
        print(f"   [FAIL] Error reading command router: {e}")
        return False
    
    # Test 4: Check if console has new functions
    print("4. Testing console functions...")
    try:
        with open("Scripts\\calyx_console.py", "r") as f:
            content = f.read()
            if "create_journal_entry" in content and "start_transcription" in content:
                print("   [OK] Console has new functions")
            else:
                print("   [FAIL] Console missing new functions")
                return False
    except Exception as e:
        print(f"   [FAIL] Error reading console: {e}")
        return False
    
    # Test 5: Check if transcription listener exists
    print("5. Testing transcription listener...")
    transcribe_path = "Scripts\\listener_transcribe.py"
    if os.path.exists(transcribe_path):
        print(f"   [OK] Transcription listener exists: {transcribe_path}")
    else:
        print(f"   [FAIL] Transcription listener missing: {transcribe_path}")
        return False
    
    print()
    print("=== All Tests Passed! ===")
    print()
    print("Workflow is ready to test:")
    print("1. Run: Scripts\\Calyx-Launch.bat")
    print("2. Say: 'Aurora' or 'Calyx' to wake")
    print("3. Say: 'Create journal entry' or 'Start transcription'")
    print("4. Watch the magic happen!")
    print()
    
    return True

if __name__ == "__main__":
    success = test_workflow()
    sys.exit(0 if success else 1)
