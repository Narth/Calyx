#!/usr/bin/env python3
"""Test TES calculation with graduated stability scoring"""
from agent_metrics import RunContext, compute_scores

# Test case: Recent tests mode run with failure
print("Testing TES calculation with graduated stability scoring...")
print()

ctx = RunContext(
    ts=1.0,
    run_dir='test',
    duration_s=144.0,
    status='done',
    applied=False,
    changed_files_count=0,
    run_tests=True,
    failure=True,
    model_id='test',
    autonomy_mode='tests'
)

scores = compute_scores(ctx)

print(f"Test Context:")
print(f"  Mode: {ctx.autonomy_mode}")
print(f"  Applied: {ctx.applied}")
print(f"  Status: {ctx.status}")
print(f"  Failure: {ctx.failure}")
print()

print(f"TES Scores:")
print(f"  TES: {scores['tes']}")
print(f"  Stability: {scores['stability']}")
print(f"  Velocity: {scores['velocity']}")
print(f"  Footprint: {scores['footprint']}")
print()

print(f"Expected:")
print(f"  TES: 76.6-78.0 (was 46.6-48.0)")
print(f"  Stability: 0.6 (was 0.0)")
print()

if 76.0 <= scores['tes'] <= 80.0:
    print("✅ PASS: TES calculation correct")
else:
    print(f"❌ FAIL: TES {scores['tes']} not in expected range")

if scores['stability'] == 0.6:
    print("✅ PASS: Stability partial credit working")
else:
    print(f"❌ FAIL: Stability {scores['stability']} not 0.6")

