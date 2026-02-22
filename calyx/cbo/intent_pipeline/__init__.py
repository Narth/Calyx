"""CBO Intent Pipeline: Mail Envelope -> Intent Artifact -> Work Envelope (CBO-minted only)."""

from __future__ import annotations

from .ingest import ingest_mail_envelope, list_pending_mail
from .registry import get_intent_dir, load_intent_artifact, save_intent_artifact
from .plan import build_plan, mint_work_envelope
from .clarify import needs_clarification, mark_ready

__all__ = [
    "ingest_mail_envelope",
    "list_pending_mail",
    "get_intent_dir",
    "load_intent_artifact",
    "save_intent_artifact",
    "build_plan",
    "mint_work_envelope",
    "needs_clarification",
    "mark_ready",
]
