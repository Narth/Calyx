#!/usr/bin/env python3
"""
Test script to debug framework initialization
"""

import sys
import traceback

try:
    from teaching.framework import TeachingFramework

    print("Testing TeachingFramework initialization...")

    # Test 1: Direct instantiation
    print("1. Creating framework...")
    framework = TeachingFramework("config/teaching_config.json")

    print("2. Checking config...")
    print(f"Config loaded: {hasattr(framework, 'config')}")
    if hasattr(framework, 'config'):
        print(f"Config keys: {list(framework.config.keys())}")

    print("3. Checking logger...")
    print(f"Logger available: {hasattr(framework, 'logger')}")

    print("4. Testing components...")
    print(f"Adaptive learner: {hasattr(framework, 'adaptive_learner')}")
    print(f"Performance tracker: {hasattr(framework, 'performance_tracker')}")
    print(f"Knowledge integrator: {hasattr(framework, 'knowledge_integrator')}")
    print(f"Pattern recognition: {hasattr(framework, 'pattern_recognition')}")

    print("Framework test completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    print("Full traceback:")
    traceback.print_exc()
