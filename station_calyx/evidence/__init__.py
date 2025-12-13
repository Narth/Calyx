# -*- coding: utf-8 -*-
"""
Evidence subsystem - Schema, journaling, and export for Node Evidence Relay.

[CBO Governance]: This module provides the core evidence infrastructure for
distributed truth capture across Station Calyx nodes. All evidence is:
- Append-only (never modified after write)
- Hash-chained (prev_hash links to previous envelope)
- Sequence-numbered (monotonic ordering)
- Node-attributed (traceable to origin)
"""

from .schemas import EvidenceEnvelopeV1, EvidenceType
from .journal import EvidenceJournal, append_evidence

__all__ = [
    "EvidenceEnvelopeV1",
    "EvidenceType",
    "EvidenceJournal",
    "append_evidence",
]
