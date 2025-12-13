"""
CBO Guardrails - Drop-in safety mechanisms for teaching system
Per CGPT recommendation: Promotion gates, auto-rollback, daily caps, quarantine
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class PromotionGate:
    """Represents a promotion gate evaluation result"""
    pattern_id: str
    uses: int
    uplift_vs_parent: float
    tes_stable_dev: float
    sentinel_ok: bool
    should_promote: bool
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DailyCapTracker:
    """Tracks daily resource caps"""
    date: str
    new_patterns: int
    synth_combos: int
    causal_claims: int
    last_reset: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


class CBOGuardrails:
    """
    Implements CBO guardrails for teaching system safety.
    Per CGPT: Promotion gates, auto-rollback, daily caps, quarantine
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("outgoing/ai4all/guardrails")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing data
        self.promotion_gates: List[PromotionGate] = []
        self.daily_caps: DailyCapTracker = None
        self.rollback_history: List[Dict] = []
        self._load_data()
        
        # Thresholds per CGPT
        self.min_uses = 10
        self.min_uplift = 0.10  # 10%
        self.max_deviation = 0.05  # 5%
        self.tes_baseline_deviation = 0.05  # 5%
        self.pulse_window = 3
        
        # Daily caps per CGPT
        self.max_new_patterns = 20
        self.max_synth_combos = 50
        self.max_causal_claims = 3
    
    def _load_data(self):
        """Load existing guardrail data"""
        try:
            # Load promotion gates
            gate_file = self.data_dir / "promotion_gates.json"
            if gate_file.exists():
                with open(gate_file, 'r') as f:
                    data = json.load(f)
                    for gate_data in data:
                        gate_data['timestamp'] = datetime.fromisoformat(gate_data['timestamp'])
                        self.promotion_gates.append(PromotionGate(**gate_data))
            
            # Load daily caps
            cap_file = self.data_dir / "daily_caps.json"
            if cap_file.exists():
                with open(cap_file, 'r') as f:
                    data = json.load(f)
                    data['last_reset'] = datetime.fromisoformat(data['last_reset'])
                    self.daily_caps = DailyCapTracker(**data)
                self._check_reset_daily_caps()
            else:
                self._initialize_daily_caps()
            
            # Load rollback history
            rollback_file = self.data_dir / "rollback_history.json"
            if rollback_file.exists():
                with open(rollback_file, 'r') as f:
                    self.rollback_history = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load guardrail data: {e}")
    
    def _save_data(self):
        """Save guardrail data"""
        try:
            # Save promotion gates
            gate_file = self.data_dir / "promotion_gates.json"
            with open(gate_file, 'w') as f:
                data = [gate.to_dict() for gate in self.promotion_gates]
                json.dump(data, f, indent=2, default=str)
            
            # Save daily caps
            cap_file = self.data_dir / "daily_caps.json"
            with open(cap_file, 'w') as f:
                json.dump(self.daily_caps.to_dict(), f, indent=2, default=str)
            
            # Save rollback history
            rollback_file = self.data_dir / "rollback_history.json"
            with open(rollback_file, 'w') as f:
                json.dump(self.rollback_history, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save guardrail data: {e}")
    
    def _initialize_daily_caps(self):
        """Initialize daily caps tracker"""
        self.daily_caps = DailyCapTracker(
            date=datetime.now().strftime('%Y-%m-%d'),
            new_patterns=0,
            synth_combos=0,
            causal_claims=0,
            last_reset=datetime.now()
        )
        self._save_data()
    
    def _check_reset_daily_caps(self):
        """Reset daily caps if new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_caps.date != today:
            self._initialize_daily_caps()
    
    def evaluate_promotion_gate(self, pattern_id: str, uses: int,
                              uplift_vs_parent: float, tes_stable_dev: float,
                              sentinel_ok: bool) -> PromotionGate:
        """
        Evaluate promotion gate per CGPT requirements.
        
        Args:
            pattern_id: Pattern to evaluate
            uses: Number of times pattern used
            uplift_vs_parent: Uplift vs parent pattern
            tes_stable_dev: TES stable deviation
            sentinel_ok: Sentinel tasks healthy
            
        Returns:
            PromotionGate evaluation result
        """
        # Check all criteria
        meets_uses = uses >= self.min_uses
        meets_uplift = uplift_vs_parent >= self.min_uplift
        meets_deviation = tes_stable_dev <= self.max_deviation
        meets_sentinel = sentinel_ok
        
        should_promote = meets_uses and meets_uplift and meets_deviation and meets_sentinel
        
        gate = PromotionGate(
            pattern_id=pattern_id,
            uses=uses,
            uplift_vs_parent=uplift_vs_parent,
            tes_stable_dev=tes_stable_dev,
            sentinel_ok=sentinel_ok,
            should_promote=should_promote,
            timestamp=datetime.now()
        )
        
        self.promotion_gates.append(gate)
        self._save_data()
        
        if should_promote:
            self.logger.info(f"Pattern {pattern_id} approved for promotion")
        else:
            self.logger.warning(f"Pattern {pattern_id} rejected for promotion")
        
        return gate
    
    def check_daily_cap(self, resource_type: str) -> bool:
        """
        Check if daily cap allows more of resource type.
        
        Args:
            resource_type: 'new_patterns', 'synth_combos', or 'causal_claims'
            
        Returns:
            True if cap not exceeded, False otherwise
        """
        self._check_reset_daily_caps()
        
        if resource_type == 'new_patterns':
            return self.daily_caps.new_patterns < self.max_new_patterns
        elif resource_type == 'synth_combos':
            return self.daily_caps.synth_combos < self.max_synth_combos
        elif resource_type == 'causal_claims':
            return self.daily_caps.causal_claims < self.max_causal_claims
        else:
            return True
    
    def increment_daily_cap(self, resource_type: str):
        """Increment daily cap counter"""
        self._check_reset_daily_caps()
        
        if resource_type == 'new_patterns':
            self.daily_caps.new_patterns += 1
        elif resource_type == 'synth_combos':
            self.daily_caps.synth_combos += 1
        elif resource_type == 'causal_claims':
            self.daily_caps.causal_claims += 1
        
        self._save_data()
    
    def evaluate_rollback(self, tes_stable_history: List[float], 
                        baseline_tes: float) -> Dict[str, Any]:
        """
        Evaluate if rollback is required.
        Per CGPT: Auto-rollback if tes_stable < baseline - 5% over 3 pulses
        
        Args:
            tes_stable_history: Last N TES stable values
            baseline_tes: Baseline TES to maintain
            
        Returns:
            Rollback evaluation result
        """
        if len(tes_stable_history) < self.pulse_window:
            return {'rollback_required': False, 'reason': 'insufficient_data'}
        
        # Check last N pulses
        recent_tes = tes_stable_history[-self.pulse_window:]
        min_tes = min(recent_tes)
        
        threshold = baseline_tes * (1 - self.tes_baseline_deviation)
        
        rollback_required = min_tes < threshold
        
        result = {
            'rollback_required': rollback_required,
            'baseline_tes': baseline_tes,
            'min_recent_tes': min_tes,
            'threshold': threshold,
            'recent_tes': recent_tes,
            'reason': 'degradation' if rollback_required else 'stable'
        }
        
        if rollback_required:
            self.logger.warning(f"Rollback required: TES {min_tes:.2f} < threshold {threshold:.2f}")
            self.rollback_history.append({
                'timestamp': datetime.now().isoformat(),
                'reason': result['reason'],
                'min_tes': min_tes,
                'baseline': baseline_tes
            })
            self._save_data()
        
        return result
    
    def get_daily_status(self) -> Dict[str, Any]:
        """Get current daily cap status"""
        self._check_reset_daily_caps()
        
        return {
            'date': self.daily_caps.date,
            'new_patterns': {
                'used': self.daily_caps.new_patterns,
                'limit': self.max_new_patterns,
                'remaining': self.max_new_patterns - self.daily_caps.new_patterns
            },
            'synth_combos': {
                'used': self.daily_caps.synth_combos,
                'limit': self.max_synth_combos,
                'remaining': self.max_synth_combos - self.daily_caps.synth_combos
            },
            'causal_claims': {
                'used': self.daily_caps.causal_claims,
                'limit': self.max_causal_claims,
                'remaining': self.max_causal_claims - self.daily_caps.causal_claims
            }
        }


# Export for use by other modules
__all__ = ['PromotionGate', 'DailyCapTracker', 'CBOGuardrails']
