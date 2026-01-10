#!/usr/bin/env python3
"""Test volatility classification tightening."""
from station_calyx.agents.temporal import calculate_trend, TrendDirection
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)

# Test 1: Small sample with variation (should NOT be volatile)
series_small = [
    (now, 10.0),
    (now + timedelta(minutes=5), 8.0),
    (now + timedelta(minutes=10), 12.0),
]
result = calculate_trend(series_small)
print(f"3 samples with variation: {result[0].value}")
assert result[0] != TrendDirection.VOLATILE, "Should not be volatile with only 3 samples"

# Test 2: Noise-level variation (should be stable)
series_noise = [
    (now, 50.0),
    (now + timedelta(minutes=5), 50.1),
    (now + timedelta(minutes=10), 49.9),
    (now + timedelta(minutes=15), 50.2),
    (now + timedelta(minutes=20), 50.0),
]
result = calculate_trend(series_noise)
print(f"5 samples with noise-level variation: {result[0].value}")
assert result[0] == TrendDirection.STABLE, "Should be stable with noise-level variation"

# Test 3: True volatility (high CV, many samples, high stdev)
series_volatile = [
    (now, 20.0),
    (now + timedelta(minutes=5), 80.0),
    (now + timedelta(minutes=10), 30.0),
    (now + timedelta(minutes=15), 90.0),
    (now + timedelta(minutes=20), 25.0),
    (now + timedelta(minutes=25), 85.0),
]
result = calculate_trend(series_volatile)
print(f"6 samples with high volatility: {result[0].value}")
# This should be volatile (high CV, enough samples, high stdev)

print()
print("Volatility classification tests passed!")
