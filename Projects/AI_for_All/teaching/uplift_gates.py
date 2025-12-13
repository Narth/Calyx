"""
Uplift Gates - Validate pattern improvements before promotion
Per CGPT requirement: Require parent→child uplift ≥+10% TES on hold-out bench
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class UpliftGate:
    """Represents an uplift gate for validating pattern improvements"""
    id: str
    pattern_id: str
    parent_pattern_id: str
    baseline_tes: float
    test_tes: float
    uplift_percent: float
    benchmark_id: str
    status: str  # 'pending', 'validated', 'rejected'
    created_date: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


class UpliftGateManager:
    """
    Manages uplift gates for validating pattern improvements.
    Per CGPT: Require parent→child uplift ≥+10% TES before promotion
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("outgoing/ai4all/uplift_gates")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing gates
        self.gates: Dict[str, UpliftGate] = {}
        self._load_gates()
        
        # Minimum uplift per CGPT
        self.min_uplift = 0.10  # 10%
    
    def _load_gates(self):
        """Load existing uplift gates"""
        gate_file = self.data_dir / "gates.json"
        if gate_file.exists():
            try:
                with open(gate_file, 'r') as f:
                    data = json.load(f)
                    for gate_id, gate_data in data.items():
                        gate_data['created_date'] = datetime.fromisoformat(gate_data['created_date'])
                        self.gates[gate_id] = UpliftGate(**gate_data)
                self.logger.info(f"Loaded {len(self.gates)} uplift gates")
            except Exception as e:
                self.logger.warning(f"Failed to load gates: {e}")
    
    def _save_gates(self):
        """Save uplift gates to persistent storage"""
        gate_file = self.data_dir / "gates.json"
        try:
            data = {gid: gate.to_dict() for gid, gate in self.gates.items()}
            with open(gate_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save gates: {e}")
    
    def create_gate(self, pattern_id: str, parent_pattern_id: str,
                   baseline_tes: float, test_tes: float, 
                   benchmark_id: str) -> str:
        """
        Create an uplift gate to validate pattern improvement.
        
        Args:
            pattern_id: New pattern being tested
            parent_pattern_id: Parent pattern to compare against
            baseline_tes: TES of parent pattern
            test_tes: TES of new pattern
            benchmark_id: Benchmark used for testing
            
        Returns:
            Gate ID
        """
        gate_id = f"gate_{int(datetime.now().timestamp())}"
        
        # Calculate uplift
        uplift_percent = (test_tes - baseline_tes) / baseline_tes if baseline_tes > 0 else 0
        
        # Determine status
        if uplift_percent >= self.min_uplift:
            status = 'validated'
        else:
            status = 'rejected'
        
        gate = UpliftGate(
            id=gate_id,
            pattern_id=pattern_id,
            parent_pattern_id=parent_pattern_id,
            baseline_tes=baseline_tes,
            test_tes=test_tes,
            uplift_percent=uplift_percent,
            benchmark_id=benchmark_id,
            status=status,
            created_date=datetime.now()
        )
        
        self.gates[gate_id] = gate
        self._save_gates()
        
        self.logger.info(f"Created uplift gate: {gate_id} - {uplift_percent*100:.1f}% uplift")
        return gate_id
    
    def validate_uplift(self, pattern_id: str, parent_pattern_id: str,
                       benchmark_results: Dict[str, float]) -> bool:
        """
        Validate that a pattern meets uplift requirements.
        
        Args:
            pattern_id: Pattern to validate
            parent_pattern_id: Parent pattern
            benchmark_results: Dictionary with 'baseline' and 'test' TES scores
            
        Returns:
            True if uplift ≥10%, False otherwise
        """
        baseline_tes = benchmark_results.get('baseline', 0)
        test_tes = benchmark_results.get('test', 0)
        
        if baseline_tes == 0:
            return False
        
        uplift_percent = (test_tes - baseline_tes) / baseline_tes
        
        # Create gate record
        gate_id = self.create_gate(
            pattern_id=pattern_id,
            parent_pattern_id=parent_pattern_id,
            baseline_tes=baseline_tes,
            test_tes=test_tes,
            benchmark_id='benchmark'
        )
        
        meets_threshold = uplift_percent >= self.min_uplift
        
        if meets_threshold:
            self.logger.info(f"Pattern {pattern_id} validated: {uplift_percent*100:.1f}% uplift")
        else:
            self.logger.warning(f"Pattern {pattern_id} rejected: {uplift_percent*100:.1f}% uplift < {self.min_uplift*100}%")
        
        return meets_threshold
    
    def get_gate(self, gate_id: str) -> Optional[UpliftGate]:
        """Get an uplift gate by ID"""
        return self.gates.get(gate_id)
    
    def list_gates(self) -> List[Dict[str, Any]]:
        """List all uplift gates"""
        return [gate.to_dict() for gate in self.gates.values()]


# Export for use by other modules
__all__ = ['UpliftGate', 'UpliftGateManager']
