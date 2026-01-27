#!/usr/bin/env python3
"""Test governance protection"""
from station_calyx.clawdbot.bridge import propose_action

# Test 1: Attempt to modify governance artifact (should be denied)
print("Test 1: Attempt to modify governance artifact")
result = propose_action(
    category='file_write',
    description='Modify governance artifact',
    parameters={'path': 'governance/HVD-1.md'},
    reasoning='Test governance protection'
)
print(f"  Result: {result['status']}")
print(f"  Reason: {result['reason']}")
print()

# Test 2: Attempt to read from allowed workspace (should be pending)
print("Test 2: Read from allowed workspace")
result = propose_action(
    category='file_read',
    description='Read Clawdbot status',
    parameters={'path': 'station_calyx/data/clawdbot/'},
    reasoning='Check Clawdbot workspace'
)
print(f"  Result: {result['status']}")
print(f"  Reason: {result['reason']}")
print()

# Test 3: Attempt shell command (high risk)
print("Test 3: Shell command proposal")
result = propose_action(
    category='shell_command',
    description='List directory contents',
    parameters={'command': 'dir'},
    reasoning='Exploration of workspace'
)
print(f"  Result: {result['status']}")
print(f"  Reason: {result['reason']}")
