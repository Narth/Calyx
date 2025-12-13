"""
Teaching Safety System - Integrated safety framework for AI-for-All
Coordinates all Phase 1 & 2 safety components: benchmarks, sentinels, gates, guardrails, synthesis
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .frozen_benchmark import FrozenBenchmarkSuite
from .causal_testing import CausalTestingFramework
from .sentinel_tasks import SentinelTaskManager
from .uplift_gates import UpliftGateManager
from .cbo_guardrails import CBOGuardrails
from .pattern_schema import PatternSchemaManager
from .pattern_synthesis import PatternSynthesisManager


class TeachingSafetySystem:
    """
    Integrated safety system coordinating all teaching safety components.
    Provides unified interface for validation, monitoring, and promotion.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize all components
        self.benchmarks = FrozenBenchmarkSuite()
        self.causal_testing = CausalTestingFramework()
        self.sentinels = SentinelTaskManager()
        self.uplift_gates = UpliftGateManager()
        self.guardrails = CBOGuardrails()
        self.schema_manager = PatternSchemaManager()
        self.synthesis_manager = PatternSynthesisManager(
            self.schema_manager,
            self.uplift_gates,
            self.guardrails
        )
        
        self.logger.info("Teaching Safety System initialized")
    
    def monitor_system_status(self) -> Dict[str, Any]:
        """
        Monitor overall system safety status.
        
        Returns:
            Comprehensive status report
        """
        status = {
            'timestamp': datetime.now().isoformat(),
            'guardrails': self.guardrails.get_daily_status(),
            'sentinels': self._check_sentinels(),
            'patterns': self._get_pattern_summary(),
            'safety_level': self._calculate_safety_level()
        }
        
        return status
    
    def _check_sentinels(self) -> Dict[str, Any]:
        """Check sentinel task health"""
        sentinels = self.sentinels.list_sentinels()
        
        # For now, return summary (in production, would run actual checks)
        return {
            'total_sentinels': len(sentinels),
            'healthy_count': len([s for s in sentinels if s.get('status') == 'healthy']),
            'alert_count': len([s for s in sentinels if s.get('alert', False)])
        }
    
    def _get_pattern_summary(self) -> Dict[str, Any]:
        """Get pattern summary statistics"""
        all_patterns = self.schema_manager.list_patterns()
        
        return {
            'total_patterns': len(all_patterns),
            'active': len([p for p in all_patterns if p['status'] == 'active']),
            'quarantine': len([p for p in all_patterns if p['status'] == 'quarantine']),
            'archived': len([p for p in all_patterns if p['status'] == 'archived'])
        }
    
    def _calculate_safety_level(self) -> str:
        """Calculate overall safety level"""
        # Check daily caps
        guardrail_status = self.guardrails.get_daily_status()
        
        # Safety indicators
        patterns_over_75_percent = sum(
            1 for cap_type in ['new_patterns', 'synth_combos', 'causal_claims']
            if guardrail_status[cap_type]['used'] / guardrail_status[cap_type]['limit'] > 0.75
        )
        
        if patterns_over_75_percent >= 2:
            return 'warning'
        elif patterns_over_75_percent >= 1:
            return 'caution'
        else:
            return 'safe'
    
    def create_test_benchmark(self, name: str, inputs: Dict, 
                             expected_outputs: Dict) -> str:
        """Create a test benchmark"""
        return self.benchmarks.create_benchmark(
            name=name,
            description=f"Test benchmark: {name}",
            inputs=inputs,
            expected_outputs=expected_outputs
        )
    
    def run_benchmark(self, bench_id: str, test_function) -> Dict[str, Any]:
        """Run a benchmark test"""
        return self.benchmarks.run_benchmark(bench_id, test_function)
    
    def create_sentinel(self, name: str, baseline_tes: float) -> str:
        """Create a sentinel task"""
        return self.sentinels.create_sentinel(
            name=name,
            description=f"Sentinel: {name}",
            baseline_tes=baseline_tes
        )
    
    def check_sentinel(self, sent_id: str, current_tes: float) -> Dict[str, Any]:
        """Check a sentinel task"""
        return self.sentinels.run_sentinel(sent_id, current_tes)
    
    def synthesize_patterns(self, domain: str, pattern_ids: List[str]) -> Optional[str]:
        """Synthesize patterns with all safety checks"""
        return self.synthesis_manager.synthesize_patterns(domain, pattern_ids)
    
    def validate_synthesis(self, synth_id: str, benchmark_results: Dict[str, float]) -> bool:
        """Validate synthesis uplift requirements"""
        return self.synthesis_manager.validate_synthesis(synth_id, benchmark_results)
    
    def promote_synthesis(self, synth_id: str) -> Optional[str]:
        """Promote validated synthesis to pattern"""
        return self.synthesis_manager.promote_synthesis(synth_id)
    
    def get_promotion_evaluation(self, pattern_id: str, uses: int,
                                 uplift_vs_parent: float, tes_stable_dev: float,
                                 sentinel_ok: bool) -> Dict[str, Any]:
        """Evaluate pattern for promotion"""
        gate = self.guardrails.evaluate_promotion_gate(
            pattern_id, uses, uplift_vs_parent, tes_stable_dev, sentinel_ok
        )
        return gate.to_dict()
    
    def check_rollback_required(self, tes_stable_history: List[float],
                                baseline_tes: float) -> Dict[str, Any]:
        """Check if rollback is required"""
        return self.guardrails.evaluate_rollback(tes_stable_history, baseline_tes)
    
    def cleanup_expired_patterns(self):
        """Clean up expired patterns"""
        self.schema_manager.cleanup_expired_patterns()


# Export for use by other modules
__all__ = ['TeachingSafetySystem']
