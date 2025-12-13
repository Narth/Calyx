"""Intent Pipeline - Intent scoring, prioritization, and deduplication"""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import Intent


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

