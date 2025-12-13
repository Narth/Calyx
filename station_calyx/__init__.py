# -*- coding: utf-8 -*-
"""
Station Calyx - Core infrastructure for local evidence collection and relay.

This package provides node identity, sequence management, and evidence journaling
for the Calyx Terminal distributed evidence network.

[CBO Governance]: Node Evidence Relay v0 - Laptop Observer Edition
- Append-only local writes only
- No network transmission (manual export bundles)
- Deterministic envelope creation with hash chaining
- Strictly monotonic sequence per node
"""

__version__ = "0.1.0"
__author__ = "Station Calyx"
