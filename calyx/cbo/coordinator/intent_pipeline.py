"""Intent Pipeline - Intent scoring, prioritization, and deduplication"""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import Intent
from station_calyx.core.intent_artifact import (
    load_intent_artifact,
    require_clarified,
    ClarificationRequired,
)
from station_calyx.core.evidence import create_event, append_event
from station_calyx.core.config import get_config
from datetime import datetime, timezone


class IntentPipeline:
    """Manages intent queue with scoring and deduplication"""
    
    def __init__(self, root: Path):
        self.root = root
        self.intents_file = root / "state" / "coordinator_intents.jsonl"
        self.intents: List[Intent] = []
        self._load_intents()
    
    def _load_intents(self):
        """Load persisted intents"""
        if not self.intents_file.exists():
            return
        
        try:
            with self.intents_file.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        self.intents.append(Intent.from_dict(data))
        except Exception:
            pass
    
    def _save_intents(self):
        """Persist intents"""
        try:
            with self.intents_file.open('w', encoding='utf-8') as f:
                for intent in self.intents:
                    f.write(json.dumps(intent.to_dict()) + '\n')
        except Exception:
            pass
    
    def add_intent(self, intent: Intent) -> bool:
        """Add intent with deduplication check"""
        # Enforce: require an intent artifact to exist and be clarified.
        try:
            art = load_intent_artifact(intent.id)
            if art is None:
                # No artifact: reject per Calyx "no assumed intent" policy
                reason = "No intent artifact present; ingestion required"
                evt = create_event(
                    event_type="INTENT_REJECTED_NO_ARTIFACT",
                    node_role="intent_pipeline",
                    summary=f"Intent {intent.id} rejected: no artifact",
                    payload={"intent_id": intent.id, "reason": reason},
                    tags=["intent", "rejection", "no_artifact"],
                    session_id=intent.id,
                )
                append_event(evt)
                return False

            # Will raise ClarificationRequired if not clarified
            require_clarified(art)
        except ClarificationRequired as cr:
            # Explicit refusal: do not add unclarified intents
            # Emit an explicit rejection event with details
            try:
                evt = create_event(
                    event_type="INTENT_REJECTED_UNCLARIFIED",
                    node_role="intent_pipeline",
                    summary=f"Intent {intent.id} rejected: unclarified",
                    payload={
                        "intent_id": intent.id,
                        "threshold": float(art.confidence_score) if hasattr(art, 'confidence_score') else None,
                        "confidence_score": float(getattr(art, 'confidence_score', 0.0)),
                        "reason": str(cr),
                    },
                    tags=["intent", "rejection", "clarification_required"],
                    session_id=intent.id,
                )
                append_event(evt)
            except Exception:
                pass
            return False
        except Exception:
            # If artifact can't be loaded for unexpected reasons, reject for safety
            reason = "Failed to load intent artifact"
            try:
                evt = create_event(
                    event_type="INTENT_REJECTED_ARTIFACT_ERROR",
                    node_role="intent_pipeline",
                    summary=f"Intent {intent.id} rejected: artifact error",
                    payload={"intent_id": intent.id, "reason": reason},
                    tags=["intent", "rejection", "artifact_error"],
                    session_id=intent.id,
                )
                append_event(evt)
            except Exception:
                pass
            return False
        # Check for duplicates within last 4 pulses (16 minutes)
        cutoff_time = time.time() - (16 * 60)
        
        for existing in self.intents:
            if (existing.description == intent.description and
                existing.required_capabilities == intent.required_capabilities):
                # Similar intent exists, don't add duplicate
                return False
        
        self.intents.append(intent)
        self._save_intents()
        return True
    
    def get_prioritized_intents(self, limit: int = 5) -> List[Intent]:
        """Get top N prioritized intents"""
        now = time.time()
        
        # Calculate priorities with freshness boost
        scored = []
        for intent in self.intents:
            freshness = 0.0
            if intent.expiry:
                try:
                    expiry_time = datetime.fromisoformat(intent.expiry).timestamp()
                    hours_until_expiry = (expiry_time - now) / 3600
                    if hours_until_expiry > 0:
                        freshness = min(20.0, hours_until_expiry * 2)  # Max 20 point boost
                except Exception:
                    pass
            
            priority = intent.calculate_priority(freshness_boost=freshness)
            scored.append((priority, intent))
        
        # Sort by priority (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N
        return [intent for _, intent in scored[:limit]]
    
    def remove_intent(self, intent_id: str):
        """Remove intent by ID"""
        self.intents = [i for i in self.intents if i.id != intent_id]
        self._save_intents()
    
    def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID"""
        for intent in self.intents:
            if intent.id == intent_id:
                return intent
        return None
    
    def expire_intents(self):
        """Remove expired intents"""
        now = time.time()
        expired = []
        
        for intent in self.intents:
            if intent.expiry:
                try:
                    expiry_time = datetime.fromisoformat(intent.expiry).timestamp()
                    if expiry_time < now:
                        expired.append(intent.id)
                except Exception:
                    pass
        
        for intent_id in expired:
            self.remove_intent(intent_id)
        
        return len(expired)

