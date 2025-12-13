"""
Canonical Pattern Schema - Mandatory pattern structure per CGPT
Required fields: pattern_id, parents[], creation_ts, domain, trigger, preconds,
action, postconds, success_metric, uses, win_rate, uplift_vs_parent, confidence,
provenance(commit, data_hash), ttl, status(active|quarantine|archived)
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class PatternProvenance:
    """Provenance information for pattern tracking"""
    commit: str
    data_hash: str
    created_by: str
    validation_tests: List[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CanonicalPattern:
    """
    Canonical pattern schema per CGPT requirements.
    Ensures auditability, traceability, and verifiability.
    """
    pattern_id: str
    parents: List[str]
    creation_ts: datetime
    domain: str
    trigger: str
    preconds: Dict[str, Any]
    action: str
    postconds: Dict[str, Any]
    success_metric: str
    uses: int
    win_rate: float
    uplift_vs_parent: float
    confidence: float
    provenance: PatternProvenance
    ttl: int  # Time to live in days
    status: str  # 'active', 'quarantine', 'archived'
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def is_expired(self) -> bool:
        """Check if pattern has exceeded TTL"""
        age = datetime.now() - self.creation_ts
        return age.days > self.ttl
    
    def should_archive(self) -> bool:
        """Check if pattern should be archived per CGPT criteria"""
        # Archive if expired
        if self.is_expired():
            return True
        
        # Archive if low usage (≤5 uses) and poor performance
        if self.uses <= 5 and self.win_rate < 0.5:
            return True
        
        # Archive if low confidence
        if self.confidence < 0.3:
            return True
        
        return False


class PatternSchemaManager:
    """
    Manages canonical pattern schema enforcement.
    Ensures all patterns follow mandatory structure per CGPT.
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("outgoing/ai4all/patterns")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing patterns
        self.patterns: Dict[str, CanonicalPattern] = {}
        self._load_patterns()
    
    def _load_patterns(self):
        """Load existing patterns"""
        pattern_file = self.data_dir / "canonical_patterns.json"
        if pattern_file.exists():
            try:
                with open(pattern_file, 'r') as f:
                    data = json.load(f)
                    for pat_id, pat_data in data.items():
                        pat_data['creation_ts'] = datetime.fromisoformat(pat_data['creation_ts'])
                        pat_data['provenance'] = PatternProvenance(**pat_data['provenance'])
                        self.patterns[pat_id] = CanonicalPattern(**pat_data)
                self.logger.info(f"Loaded {len(self.patterns)} canonical patterns")
            except Exception as e:
                self.logger.warning(f"Failed to load patterns: {e}")
    
    def _save_patterns(self):
        """Save patterns to persistent storage"""
        pattern_file = self.data_dir / "canonical_patterns.json"
        try:
            data = {pid: pat.to_dict() for pid, pat in self.patterns.items()}
            with open(pattern_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save patterns: {e}")
    
    def create_pattern(self, domain: str, trigger: str, preconds: Dict[str, Any],
                     action: str, postconds: Dict[str, Any], success_metric: str,
                     parents: List[str] = None, created_by: str = "system",
                     commit: str = None, ttl: int = 90) -> str:
        """
        Create a new canonical pattern.
        
        Args:
            domain: Domain this pattern applies to
            trigger: Trigger condition
            preconds: Preconditions
            action: Action to take
            postconds: Postconditions
            success_metric: Metric to evaluate success
            parents: Parent pattern IDs
            created_by: Creator identifier
            commit: Git commit hash
            ttl: Time to live in days
            
        Returns:
            Pattern ID
        """
        pattern_id = f"pattern_{int(datetime.now().timestamp())}"
        
        # Generate data hash
        data_str = json.dumps({
            'trigger': trigger,
            'preconds': preconds,
            'action': action,
            'postconds': postconds
        }, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        # Create provenance
        provenance = PatternProvenance(
            commit=commit or "manual",
            data_hash=data_hash,
            created_by=created_by,
            validation_tests=[]
        )
        
        # Create pattern
        pattern = CanonicalPattern(
            pattern_id=pattern_id,
            parents=parents or [],
            creation_ts=datetime.now(),
            domain=domain,
            trigger=trigger,
            preconds=preconds,
            action=action,
            postconds=postconds,
            success_metric=success_metric,
            uses=0,
            win_rate=0.0,
            uplift_vs_parent=0.0,
            confidence=0.5,
            provenance=provenance,
            ttl=ttl,
            status='quarantine'  # Start in quarantine per CGPT
        )
        
        self.patterns[pattern_id] = pattern
        self._save_patterns()
        
        self.logger.info(f"Created canonical pattern: {pattern_id} in domain {domain}")
        return pattern_id
    
    def update_pattern_metrics(self, pattern_id: str, uses: int = None,
                              win_rate: float = None, uplift_vs_parent: float = None,
                              confidence: float = None):
        """Update pattern metrics"""
        if pattern_id not in self.patterns:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        pattern = self.patterns[pattern_id]
        
        if uses is not None:
            pattern.uses = uses
        if win_rate is not None:
            pattern.win_rate = win_rate
        if uplift_vs_parent is not None:
            pattern.uplift_vs_parent = uplift_vs_parent
        if confidence is not None:
            pattern.confidence = confidence
        
        self._save_patterns()
    
    def promote_pattern(self, pattern_id: str):
        """Promote pattern from quarantine to active"""
        if pattern_id not in self.patterns:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        pattern = self.patterns[pattern_id]
        if pattern.status == 'quarantine':
            pattern.status = 'active'
            self._save_patterns()
            self.logger.info(f"Promoted pattern {pattern_id} to active")
    
    def archive_pattern(self, pattern_id: str):
        """Archive a pattern"""
        if pattern_id not in self.patterns:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        pattern = self.patterns[pattern_id]
        pattern.status = 'archived'
        self._save_patterns()
        self.logger.info(f"Archived pattern {pattern_id}")
    
    def cleanup_expired_patterns(self):
        """Clean up expired patterns per CGPT GC requirements"""
        patterns_to_archive = []
        
        for pat_id, pattern in self.patterns.items():
            if pattern.should_archive():
                patterns_to_archive.append(pat_id)
        
        for pat_id in patterns_to_archive:
            self.archive_pattern(pat_id)
        
        if patterns_to_archive:
            self.logger.info(f"Archived {len(patterns_to_archive)} expired patterns")
    
    def get_pattern(self, pattern_id: str) -> Optional[CanonicalPattern]:
        """Get a pattern by ID"""
        return self.patterns.get(pattern_id)
    
    def list_patterns(self, status: str = None) -> List[Dict[str, Any]]:
        """List patterns, optionally filtered by status"""
        patterns = self.patterns.values()
        if status:
            patterns = [p for p in patterns if p.status == status]
        return [pat.to_dict() for pat in patterns]


# Export for use by other modules
__all__ = ['PatternProvenance', 'CanonicalPattern', 'PatternSchemaManager']
