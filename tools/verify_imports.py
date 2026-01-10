#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify module import paths and data flow.
Run with: python -B tools/verify_imports.py
"""
import sys
import os

# Force local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("MODULE IMPORT VERIFICATION")
print("=" * 60)

# 1. Check station_calyx_desktop path
import station_calyx_desktop
print(f"\n1. station_calyx_desktop.__file__:")
print(f"   {station_calyx_desktop.__file__}")

# 2. Check station_calyx path  
import station_calyx
print(f"\n2. station_calyx.__file__:")
print(f"   {station_calyx.__file__}")

# 3. Check status_surface
from station_calyx.ui import status_surface
print(f"\n3. status_surface.__file__:")
print(f"   {status_surface.__file__}")

# 4. Verify _format_evidence_description exists and works
print(f"\n4. _format_evidence_description function:")
if hasattr(status_surface, '_format_evidence_description'):
    result = status_surface._format_evidence_description("Test", 5, 2.5, "low")
    print(f"   EXISTS - Output: '{result}'")
else:
    print("   MISSING!")

# 5. Check get_system_state output
print(f"\n5. get_system_state output:")
from station_calyx.core.evidence import load_recent_events
events = load_recent_events(100)
state = status_surface.get_system_state(events)
print(f"   state: {state['state']}")
print(f"   description: {state['description']}")
print(f"   snapshot_count: {state.get('snapshot_count', 'N/A')}")

# 6. Check API client
print(f"\n6. API client test:")
from station_calyx_desktop.api_client import get_client, is_service_running
print(f"   Service running: {is_service_running()}")
if is_service_running():
    client = get_client()
    response = client.get_human_status()
    if response.success:
        data = response.data
        sys_state = data.get("system_state", {})
        print(f"   API state: {sys_state.get('state', 'N/A')}")
        print(f"   API description: {sys_state.get('description', 'N/A')}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
