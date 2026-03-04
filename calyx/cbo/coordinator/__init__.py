"""
Legacy coordinator moved to archive/legacy_cbo_coordinator.
Do not import. Use calyx.cbo.intent_pipeline for the canonical spine.
"""
from __future__ import annotations

def __getattr__(name: str):
    raise ImportError(
        "calyx.cbo.coordinator is deprecated and moved to archive/legacy_cbo_coordinator. "
        "Use calyx.cbo.intent_pipeline for the canonical intent pipeline."
    )
