"""
Pattern Synthesis - Constrained pattern combination for safe exponential growth
Per CGPT: Gate synthesis to top-k patterns (k=5 per domain), daily cap ≤20 composites/day
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .pattern_schema import CanonicalPattern, PatternSchemaManager
from .uplift_gates import UpliftGateManager
from .cbo_guardrails import CBOGuardrails


@dataclass
class PatternSynthesis:
    """Represents a synthesized pattern combination"""
    id: str
    parent_patterns: List[str]
    synthesis_method: str
    domain: str
    combined_trigger: str
    combined_preconds: Dict[str, Any]
    combined_action: str
    combined_postconds: Dict[str, Any]
    synthesis_date: datetime
    uplift_validation: Optional[float]
    status: str  # 'pending', 'testing', 'validated', 'rejected'
    
    def to_dict(self) -> dict:
        return asdict(self)


class PatternSynthesisManager:
    """
    Manages constrained pattern synthesis with safety gates.
    Per CGPT: Top-k only (k=5 per domain), daily cap ≤20 composites
    """
    
    def __init__(self, schema_manager: PatternSchemaManager,
                 uplift_manager: UpliftGateManager,
                 guardrails: CBOGuardrails):
        self.schema_manager = schema_manager
        self.uplift_manager = uplift_manager
        self.guardrails = guardrails
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing syntheses
        self.syntheses: Dict[str, PatternSynthesis] = {}
        self.data_dir = Path("outgoing/ai4all/synthesis")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_syntheses()
        
        # Constraints per CGPT
        self.top_k = 5  # Top k patterns per domain
        self.max_daily_synthesis = 20  # Daily cap
        self.max_daily_combos = 50
    
    def _load_syntheses(self):
        """Load existing pattern syntheses"""
        synth_file = self.data_dir / "syntheses.json"
        if synth_file.exists():
            try:
                with open(synth_file, 'r') as f:
                    data = json.load(f)
                    for synth_id, synth_data in data.items():
                        synth_data['synthesis_date'] = datetime.fromisoformat(synth_data['synthesis_date'])
                        self.syntheses[synth_id] = PatternSynthesis(**synth_data)
                self.logger.info(f"Loaded {len(self.syntheses)} pattern syntheses")
            except Exception as e:
                self.logger.warning(f"Failed to load syntheses: {e}")
    
    def _save_syntheses(self):
        """Save pattern syntheses"""
        synth_file = self.data_dir / "syntheses.json"
        try:
            data = {sid: synth.to_dict() for sid, synth in self.syntheses.items()}
            with open(synth_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save syntheses: {e}")
    
    def get_top_k_patterns(self, domain: str) -> List[CanonicalPattern]:
        """
        Get top-k patterns for a domain per CGPT requirement.
        
        Args:
            domain: Domain to get patterns for
            
        Returns:
            Top k patterns by confidence + win_rate
        """
        # Get all active patterns in domain
        all_patterns = self.schema_manager.list_patterns(status='active')
        domain_patterns = [p for p in all_patterns if p['domain'] == domain]
        
        # Sort by combined score (confidence * win_rate)
        sorted_patterns = sorted(
            domain_patterns,
            key=lambda p: p['confidence'] * p['win_rate'],
            reverse=True
        )
        
        # Return top k
        top_k = sorted_patterns[:self.top_k]
        
        self.logger.info(f"Selected top {len(top_k)} patterns for domain {domain}")
        return top_k
    
    def check_synthesis_allowance(self) -> Tuple[bool, str]:
        """
        Check if synthesis is allowed under daily caps.
        
        Returns:
            (allowed, reason)
        """
        # Check daily cap for new patterns
        if not self.guardrails.check_daily_cap('new_patterns'):
            return False, "Daily new_patterns cap exceeded"
        
        # Check daily cap for synth combos
        if not self.guardrails.check_daily_cap('synth_combos'):
            return False, "Daily synth_combos cap exceeded"
        
        return True, "Allowed"
    
    def synthesize_patterns(self, domain: str, pattern_ids: List[str],
                          synthesis_method: str = 'merge') -> Optional[str]:
        """
        Synthesize patterns with safety gates enforced.
        
        Args:
            domain: Domain for synthesis
            pattern_ids: Parent pattern IDs to combine
            synthesis_method: How to combine ('merge', 'intersect', 'union')
            
        Returns:
            Synthesis ID if successful, None if rejected
        """
        # Safety check: Daily cap allowance
        allowed, reason = self.check_synthesis_allowance()
        if not allowed:
            self.logger.warning(f"Synthesis rejected: {reason}")
            return None
        
        # Safety check: Only use top-k patterns
        top_k_patterns = self.get_top_k_patterns(domain)
        valid_ids = [p['pattern_id'] for p in top_k_patterns]
        
        if not all(pid in valid_ids for pid in pattern_ids):
            self.logger.warning(f"Synthesis rejected: Not all patterns in top-k")
            return None
        
        # Get parent patterns
        parent_patterns = []
        for pid in pattern_ids:
            pattern = self.schema_manager.get_pattern(pid)
            if pattern:
                parent_patterns.append(pattern)
        
        if len(parent_patterns) < 2:
            self.logger.warning("Synthesis rejected: Need at least 2 patterns")
            return None
        
        # Perform synthesis
        combined_pattern = self._combine_patterns(parent_patterns, synthesis_method)
        
        # Create synthesis record
        synth_id = f"synthesis_{int(datetime.now().timestamp())}"
        synthesis = PatternSynthesis(
            id=synth_id,
            parent_patterns=pattern_ids,
            synthesis_method=synthesis_method,
            domain=domain,
            combined_trigger=combined_pattern['trigger'],
            combined_preconds=combined_pattern['preconds'],
            combined_action=combined_pattern['action'],
            combined_postconds=combined_pattern['postconds'],
            synthesis_date=datetime.now(),
            uplift_validation=None,
            status='pending'
        )
        
        self.syntheses[synth_id] = synthesis
        self._save_syntheses()
        
        # Increment daily cap
        self.guardrails.increment_daily_cap('synth_combos')
        
        self.logger.info(f"Created synthesis: {synth_id} from {len(pattern_ids)} parents")
        return synth_id
    
    def _combine_patterns(self, patterns: List[CanonicalPattern],
                         method: str) -> Dict[str, Any]:
        """Combine patterns using specified method"""
        if method == 'merge':
            # Merge triggers (union)
            triggers = set()
            for p in patterns:
                triggers.add(p.trigger)
            combined_trigger = " AND ".join(sorted(triggers))
            
            # Merge preconditions (intersection - stricter)
            preconds = {}
            for p in patterns:
                preconds.update(p.preconds)
            
            # Use first action (simple merge)
            combined_action = patterns[0].action
            
            # Merge postconditions (union)
            postconds = {}
            for p in patterns:
                postconds.update(p.postconds)
            
        elif method == 'intersect':
            # Intersection of triggers and conditions
            triggers = set(patterns[0].trigger.split(" AND "))
            for p in patterns[1:]:
                triggers = triggers.intersection(set(p.trigger.split(" AND ")))
            combined_trigger = " AND ".join(sorted(triggers))
            
            # Intersection of preconditions
            preconds = patterns[0].preconds.copy()
            for p in patterns[1:]:
                preconds = {k: v for k, v in preconds.items() if k in p.preconds}
            
            combined_action = patterns[0].action
            
            postconds = patterns[0].postconds.copy()
            for p in patterns[1:]:
                postconds = {k: v for k, v in postconds.items() if k in p.postconds}
        
        else:  # union
            # Union of all triggers and conditions
            triggers = set()
            for p in patterns:
                triggers.update(p.trigger.split(" AND "))
            combined_trigger = " AND ".join(sorted(triggers))
            
            preconds = {}
            for p in patterns:
                preconds.update(p.preconds)
            
            combined_action = "; ".join([p.action for p in patterns])
            
            postconds = {}
            for p in patterns:
                postconds.update(p.postconds)
        
        return {
            'trigger': combined_trigger,
            'preconds': preconds,
            'action': combined_action,
            'postconds': postconds
        }
    
    def validate_synthesis(self, synth_id: str, benchmark_results: Dict[str, float]) -> bool:
        """
        Validate synthesis meets uplift requirements.
        
        Args:
            synth_id: Synthesis ID
            benchmark_results: Baseline and test TES scores
            
        Returns:
            True if validated (≥+10% uplift), False otherwise
        """
        if synth_id not in self.syntheses:
            return False
        
        synthesis = self.syntheses[synth_id]
        
        # Get parent patterns for comparison
        if not synthesis.parent_patterns:
            return False
        
        # Use first parent as baseline
        parent_id = synthesis.parent_patterns[0]
        parent_pattern = self.schema_manager.get_pattern(parent_id)
        
        if not parent_pattern:
            return False
        
        # Validate uplift via uplift manager
        validated = self.uplift_manager.validate_uplift(
            pattern_id=synth_id,
            parent_pattern_id=parent_id,
            benchmark_results=benchmark_results
        )
        
        # Update synthesis status
        if validated:
            synthesis.status = 'validated'
            synthesis.uplift_validation = benchmark_results.get('test', 0) - benchmark_results.get('baseline', 0)
            self.logger.info(f"Synthesis {synth_id} validated")
        else:
            synthesis.status = 'rejected'
            self.logger.warning(f"Synthesis {synth_id} rejected")
        
        self._save_syntheses()
        return validated
    
    def promote_synthesis(self, synth_id: str) -> Optional[str]:
        """
        Promote validated synthesis to pattern status.
        
        Args:
            synth_id: Synthesis ID
            
        Returns:
            New pattern ID if promoted, None otherwise
        """
        if synth_id not in self.syntheses:
            return None
        
        synthesis = self.syntheses[synth_id]
        
        # Check validation status
        if synthesis.status != 'validated':
            self.logger.warning(f"Cannot promote synthesis {synth_id}: not validated")
            return None
        
        # Create canonical pattern from synthesis
        pattern_id = self.schema_manager.create_pattern(
            domain=synthesis.domain,
            trigger=synthesis.combined_trigger,
            preconds=synthesis.combined_preconds,
            action=synthesis.combined_action,
            postconds=synthesis.combined_postconds,
            success_metric='tes',
            parents=synthesis.parent_patterns,
            ttl=90
        )
        
        # Increment daily cap for new pattern
        self.guardrails.increment_daily_cap('new_patterns')
        
        self.logger.info(f"Promoted synthesis {synth_id} to pattern {pattern_id}")
        return pattern_id


# Export for use by other modules
__all__ = ['PatternSynthesis', 'PatternSynthesisManager']
