"""
Sentinel Tasks - Unchanged gold cases for stability monitoring
Per CGPT requirement: Auto-rollback if sentinel TES dips >5%
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SentinelTask:
    """Represents a sentinel task for stability monitoring"""
    id: str
    name: str
    description: str
    baseline_tes: float
    current_tes: float
    created_date: datetime
    last_run_date: datetime
    run_count: int
    deviation_threshold: float
    
    def to_dict(self) -> dict:
        return asdict(self)


class SentinelTaskManager:
    """
    Manages sentinel tasks for stability monitoring.
    Per CGPT: Auto-rollback if sentinel TES dips >5%
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("outgoing/ai4all/sentinels")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing sentinels
        self.sentinels: Dict[str, SentinelTask] = {}
        self._load_sentinels()
        
        # Default threshold per CGPT
        self.default_threshold = 0.05  # 5%
    
    def _load_sentinels(self):
        """Load existing sentinel tasks"""
        sentinel_file = self.data_dir / "sentinels.json"
        if sentinel_file.exists():
            try:
                with open(sentinel_file, 'r') as f:
                    data = json.load(f)
                    for sent_id, sent_data in data.items():
                        sent_data['created_date'] = datetime.fromisoformat(sent_data['created_date'])
                        sent_data['last_run_date'] = datetime.fromisoformat(sent_data['last_run_date'])
                        self.sentinels[sent_id] = SentinelTask(**sent_data)
                self.logger.info(f"Loaded {len(self.sentinels)} sentinel tasks")
            except Exception as e:
                self.logger.warning(f"Failed to load sentinels: {e}")
    
    def _save_sentinels(self):
        """Save sentinel tasks to persistent storage"""
        sentinel_file = self.data_dir / "sentinels.json"
        try:
            data = {sid: sent.to_dict() for sid, sent in self.sentinels.items()}
            with open(sentinel_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save sentinels Elding {e}")
    
    def create_sentinel(self, name: str, description: str, 
                       baseline_tes: float, threshold: float = None) -> str:
        """
        Create a new sentinel task.
        
        Args:
            name: Name of the sentinel
            description: Description of what it monitors
            baseline_tes: Baseline TES score to maintain
            threshold: Deviation threshold (default 5%)
            
        Returns:
            Sentinel ID
        """
        sent_id = f"sentinel_{int(datetime.now().timestamp())}"
        
        sentinel = SentinelTask(
            id=sent_id,
            name=name,
            description=description,
            baseline_tes=baseline_tes,
            current_tes=baseline_tes,
            created_date=datetime.now(),
            last_run_date=datetime.now(),
            run_count=0,
            deviation_threshold=threshold or self.default_threshold
        )
        
        self.sentinels[sent_id] = sentinel
        self._save_sentinels()
        
        self.logger.info(f"Created sentinel: {sent_id} - {name}")
        return sent_id
    
    def run_sentinel(self, sent_id: str, current_tes: float) -> Dict[str, Any]:
        """
        Run a sentinel task and check for deviation.
        
        Args:
            sent_id: Sentinel ID
            current_tes: Current TES score
            
        Returns:
            Results dictionary with deviation and alert status
        """
        if sent_id not in self.sentinels:
            raise ValueError(f"Sentinel {sent_id} not found")
        
        sentinel = self.sentinels[sent_id]
        
        # Update current TES
        sentinel.current_tes = current_tes
        sentinel.last_run_date = datetime.now()
        sentinel.run_count += 1
        
        # Calculate deviation
        deviation = abs(current_tes - sentinel.baseline_tes) / sentinel.baseline_tes
        
        # Check threshold
        alert = deviation > sentinel.deviation_threshold
        
        # Determine status
        if current_tes < sentinel.baseline_tes * (1 - sentinel.deviation_threshold):
            status = 'degraded'
        elif alert:
            status = 'warning'
        else:
            status = 'healthy'
        
        self._save_sentinels()
        
        result = {
            'sentinel_id': sent_id,
            'baseline_tes': sentinel.baseline_tes,
            'current_tes': current_tes,
            'deviation': deviation,
            'deviation_percent': deviation * 100,
            'threshold': sentinel.deviation_threshold,
            'alert': alert,
            'status': status
        }
        
        if alert:
            self.logger.warning(f"Sentinel {sent_id} alert: {deviation*100:.1f}% deviation")
        
        return result
    
    def check_all_sentinels(self, tes_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Check all sentinel tasks and determine overall system stability.
        
        Args:
            tes_scores: Dictionary mapping sentinel IDs to TES scores
            
        Returns:
            Overall stability assessment
        """
        results = {}
        alerts = []
        
        for sent_id, tes_score in tes_scores.items():
            if sent_id in self.sentinels:
                result = self.run_sentinel(sent_id, tes_score)
                results[sent_id] = result
                
                if result['alert']:
                    alerts.append(sent_id)
        
        # Overall assessment
        total_sentinels = len(results)
        healthy_count = sum(1 for r in results.values() if r['status'] == 'healthy')
        degraded_count = sum(1 for r in results.values() if r['status'] == 'degraded')
        
        overall_status = 'healthy' if len(alerts) == 0 else 'warning' if degraded_count == 0 else 'degraded'
        
        return {
            'overall_status': overall_status,
            'total_sentinels': total_sentinels,
            'healthy_count': healthy_count,
            'degraded_count': degraded_count,
            'alerts': alerts,
            'results': results,
            'rollback_required': degraded_count > 0
        }
    
    def get_sentinel(self, sent_id: str) -> Optional[SentinelTask]:
        """Get a sentinel task by ID"""
        return self.sentinels.get(sent_id)
    
    def list_sentinels(self) -> List[Dict[str, Any]]:
        """List all sentinel tasks"""
        return [sent.to_dict() for sent in self.sentinels.values()]


# Export for use by other modules
__all__ = ['SentinelTask', 'SentinelTaskManager']
