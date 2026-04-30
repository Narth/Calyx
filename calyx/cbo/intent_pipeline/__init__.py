"""CBO Intent Pipeline: Mail Envelope -> Intent Artifact -> Work Envelope (CBO-minted only)."""

from __future__ import annotations

from .ingest import ingest_mail_envelope, list_pending_mail
from .intake_card import INTAKE_CARD_FIELDS, normalize_intake_card, validate_intake_card
from .routing_proof import normalize_routing_proof
from .registry import get_intent_dir, load_intent_artifact, save_critique_checkpoint, save_intent_artifact
from .plan import build_plan, mint_work_envelope
from .clarify import needs_clarification, mark_ready

__all__ = [
    "ingest_mail_envelope",
    "list_pending_mail",
    "INTAKE_CARD_FIELDS",
    "get_intent_dir",
    "load_intent_artifact",
    "normalize_intake_card",
    "normalize_routing_proof",
    "save_critique_checkpoint",
    "save_intent_artifact",
    "validate_intake_card",
    "build_plan",
    "mint_work_envelope",
    "needs_clarification",
    "mark_ready",
]
