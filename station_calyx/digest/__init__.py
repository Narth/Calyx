# -*- coding: utf-8 -*-
"""
Truth Digest v1
===============

Station Calyx capability for producing human-actionable truth statements
from existing evidence.

PURPOSE:
- Minimize human attention cost
- Preserve systematic and logical truth
- Report state changes and confirmations without recommendation

CONSTRAINTS (per HVD-1):
- Advisory-only: No recommendations or prioritization
- No suppression: All state changes reported
- No inference: No causation or prediction
- Deterministic: Same evidence produces same digest
- Auditable: All statements traceable to evidence

GENERATION TRIGGERS:
- Fixed-interval (scheduler)
- State-change (event-driven)
- Human-initiated (CLI)
"""

from .generator import generate_node_digest, generate_metric_digest
from .classifier import classify_state, StateChange, StateConfirmation
from .thresholds import (
    load_thresholds,
    save_thresholds,
    learn_thresholds,
    set_threshold_override,
)
from .formatter import format_digest_markdown, format_digest_json

__all__ = [
    "generate_node_digest",
    "generate_metric_digest",
    "classify_state",
    "StateChange",
    "StateConfirmation",
    "load_thresholds",
    "save_thresholds",
    "learn_thresholds",
    "set_threshold_override",
    "format_digest_markdown",
    "format_digest_json",
]
