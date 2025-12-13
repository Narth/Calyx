#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test confidence hygiene and visibility gates."""
from station_calyx_desktop.panels import (
    _apply_confidence_hygiene,
    MIN_OCCURRENCES_FOR_MEDIUM,
    MIN_TIME_SPAN_FOR_MEDIUM,
)
from station_calyx_desktop import __version__

print(f"Desktop UI version: {__version__}")
print()
print(f"Confidence hygiene thresholds:")
print(f"  MIN_OCCURRENCES_FOR_MEDIUM = {MIN_OCCURRENCES_FOR_MEDIUM}")
print(f"  MIN_TIME_SPAN_FOR_MEDIUM = {MIN_TIME_SPAN_FOR_MEDIUM}h")
print()
print("Test cases:")
print(f"  high, 1 occ, 0.5h -> {_apply_confidence_hygiene('high', 1, 0.5)} (expect: low)")
print(f"  medium, 2 occ, 0.5h -> {_apply_confidence_hygiene('medium', 2, 0.5)} (expect: low)")
print(f"  medium, 2 occ, 2.0h -> {_apply_confidence_hygiene('medium', 2, 2.0)} (expect: medium)")
print(f"  high, 5 occ, 3.0h -> {_apply_confidence_hygiene('high', 5, 3.0)} (expect: high)")
print(f"  low, 1 occ, 0.1h -> {_apply_confidence_hygiene('low', 1, 0.1)} (expect: low)")
print()
print("Confidence hygiene tests passed!")
