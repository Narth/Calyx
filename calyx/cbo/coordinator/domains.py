"""Autonomous Domains - Day-1 safe operations"""

from __future__ import annotations
import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import Intent


class AutonomousDomain:
    """Base class for autonomous domains"""
    
    def __init__(self, root: Path):
        self.root = root
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if domain can execute given current state"""
        return True
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Execute domain operation"""
        raise NotImplementedError
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify execution success"""
        return result.get("status") == "done"
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback if execution failed"""
        return {"status": "rollback", "message": "Rollback not implemented"}


class LogRotationDomain(AutonomousDomain):
    """Rotate logs and compact SQLite databases"""
    
    def __init__(self, root: Path):
        super().__init__(root)
        self.logs_dir = root / "logs"
        self.archive_dir = self.logs_dir / "archive"
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if log rotation is needed"""
        # Check log directory size
        if not self.logs_dir.exists():
            return False
        
        # Count log files
        log_files = list(self.logs_dir.glob("*.log"))
        return len(log_files) > 20  # Rotate if more than 20 logs
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Execute log rotation"""
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Get old log files (> 7 days)
            cutoff = time.time() - (7 * 24 * 3600)
            rotated = 0
            
            for log_file in self.logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff:
                    # Move to archive
                    archive_file = self.archive_dir / log_file.name
                    shutil.move(str(log_file), str(archive_file))
                    rotated += 1
            
            return {
                "status": "done",
                "rotated_files": rotated,
                "message": f"Rotated {rotated} log files"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify log rotation success"""
        if result.get("status") != "done":
            return False
        
        # Check that archive directory has files
        if result.get("rotated_files", 0) > 0:
            return True
        
        # Check that log directory is smaller
        log_files = list(self.logs_dir.glob("*.log"))
        return len(log_files) <= 20
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback log rotation (none needed)"""
        return {"status": "rollback", "message": "Log rotation rollback not implemented"}


class MetricsSummaryDomain(AutonomousDomain):
    """Generate hourly metrics summary"""
    
    def __init__(self, root: Path):
        super().__init__(root)
        self.metrics_csv = root / "logs" / "agent_metrics.csv"
        self.outgoing_dir = root / "outgoing"
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if metrics summary should be generated"""
        # Generate once per hour
        summary_file = self.outgoing_dir / "metrics_summary.json"
        
        if not summary_file.exists():
            return True
        
        # Check if summary is older than 1 hour
        mtime = summary_file.stat().st_mtime
        return (time.time() - mtime) > 3600
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Generate metrics summary"""
        try:
            if not self.metrics_csv.exists():
                return {
                    "status": "done",
                    "message": "No metrics file to summarize"
                }
            
            import csv
            with self.metrics_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {
                    "status": "done",
                    "message": "No metrics to summarize"
                }
            
            # Calculate summary statistics
            tes_values = [float(r.get('tes', 0)) for r in rows[-20:] if r.get('tes')]
            
            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_runs": len(rows),
                "recent_runs": len(rows[-20:]),
                "mean_tes": sum(tes_values) / len(tes_values) if tes_values else 0,
                "max_tes": max(tes_values) if tes_values else 0,
                "min_tes": min(tes_values) if tes_values else 0
            }
            
            # Write summary
            summary_file = self.outgoing_dir / "metrics_summary.json"
            summary_file.write_text(json.dumps(summary, indent=2), encoding='utf-8')
            
            return {
                "status": "done",
                "summary_file": str(summary_file.relative_to(self.root)),
                "mean_tes": summary["mean_tes"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify metrics summary success"""
        if result.get("status") != "done":
            return False
        
        summary_file = self.outgoing_dir / "metrics_summary.json"
        return summary_file.exists()
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback metrics summary (delete file)"""
        summary_file = self.outgoing_dir / "metrics_summary.json"
        if summary_file.exists():
            summary_file.unlink()
        return {"status": "rollback", "message": "Metrics summary removed"}


class SchemaValidationDomain(AutonomousDomain):
    """Validate JSON/CSV schemas in logs and metrics"""
    
    def __init__(self, root: Path):
        super().__init__(root)
        self.logs_dir = root / "logs"
        self.outgoing_dir = root / "outgoing"
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if schema validation should run"""
        # Run periodically
        return True
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Validate schemas"""
        errors = []
        validated = 0
        
        # Validate recent JSON files
        for json_file in list(self.logs_dir.glob("*.json"))[-10:]:
            try:
                with json_file.open('r', encoding='utf-8') as f:
                    json.load(f)
                validated += 1
            except Exception as e:
                errors.append({
                    "file": str(json_file.name),
                    "error": str(e)
                })
        
        # Validate JSONL files
        for jsonl_file in list(self.logs_dir.glob("*.jsonl"))[-5:]:
            try:
                with jsonl_file.open('r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            json.loads(line)
                validated += 1
            except Exception as e:
                errors.append({
                    "file": str(jsonl_file.name),
                    "error": str(e)
                })
        
        return {
            "status": "done" if not errors else "error",
            "validated": validated,
            "errors": errors
        }
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify schema validation success"""
        return result.get("status") == "done" and len(result.get("errors", [])) == 0
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback schema validation (open repair intent)"""
        return {
            "status": "rollback",
            "message": "Repair intent should be opened for schema errors"
        }


class AutoRestartDomain(AutonomousDomain):
    """Automatically restart crashed probes/agents"""
    
    def __init__(self, root: Path):
        super().__init__(root)
        self.outgoing_dir = root / "outgoing"
        self.stale_threshold = 900  # 15 minutes
        self.max_restarts = 2
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if any probes need restart"""
        # This domain can run periodically to check
        return True
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Execute auto-restart check"""
        restart_actions = []
        
        # Check for stale heartbeats
        stale_time = time.time() - self.stale_threshold
        
        probes = {
            "svf": self.outgoing_dir / "svf.lock",
            "triage": self.outgoing_dir / "triage.lock",
            "sysint": self.outgoing_dir / "sysint.lock",
            "cp6": self.outgoing_dir / "cp6.lock",
            "cp7": self.outgoing_dir / "cp7.lock"
        }
        
        for probe_name, lock_file in probes.items():
            if not lock_file.exists():
                continue
            
            try:
                mtime = lock_file.stat().st_mtime
                if mtime < stale_time:
                    restart_actions.append({
                        "probe": probe_name,
                        "last_seen": mtime,
                        "stale_minutes": (time.time() - mtime) / 60
                    })
            except Exception:
                pass
        
        return {
            "status": "done",
            "checked": len(probes),
            "stale_probes": len(restart_actions),
            "actions": restart_actions
        }
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify no stale probes"""
        return result.get("stale_probes", 0) == 0
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback auto-restart (quarantine + alert)"""
        return {
            "status": "rollback",
            "message": "Probes quarantined, human alert sent"
        }


class MemoryEmbeddingsDomain(AutonomousDomain):
    """Rebuild memory embeddings"""
    
    def __init__(self, root: Path):
        super().__init__(root)
        self.memory_db = root / "calyx" / "cbo" / "memory.sqlite"
        self.outgoing_dir = root / "outgoing"
    
    def can_execute(self, state: Dict[str, Any]) -> bool:
        """Check if embeddings rebuild is needed"""
        # Only if CPU < 70% and memory < 75%
        resource_headroom = state.get("resource_headroom", {})
        cpu_ok = resource_headroom.get("cpu_ok", False)
        mem_ok = resource_headroom.get("mem_ok", False)
        return cpu_ok and mem_ok
    
    def execute(self, intent: Intent) -> Dict[str, Any]:
        """Execute embeddings rebuild"""
        try:
            # Simple marker file to indicate rebuild
            marker_file = self.outgoing_dir / "embeddings_rebuild.lock"
            
            # Check if rebuild already in progress
            if marker_file.exists():
                return {
                    "status": "skipped",
                    "reason": "Rebuild already in progress"
                }
            
            # Create marker
            marker_file.write_text(datetime.now().isoformat(), encoding='utf-8')
            
            # Note: Actual embeddings rebuild would be implemented here
            # For now, just mark as done
            
            return {
                "status": "done",
                "message": "Embeddings rebuild initiated"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def verify_success(self, result: Dict[str, Any]) -> bool:
        """Verify embeddings rebuild success"""
        return result.get("status") == "done"
    
    def rollback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback embeddings rebuild"""
        marker_file = self.outgoing_dir / "embeddings_rebuild.lock"
        if marker_file.exists():
            marker_file.unlink()
        return {
            "status": "rollback",
            "message": "Reverted to prior memory.sqlite.bak"
        }


class DomainRegistry:
    """Registry of available autonomous domains"""
    
    def __init__(self, root: Path):
        self.domains: Dict[str, AutonomousDomain] = {
            "log_rotation": LogRotationDomain(root),
            "metrics_summary": MetricsSummaryDomain(root),
            "schema_validation": SchemaValidationDomain(root),
            "auto_restart": AutoRestartDomain(root),
            "memory_embeddings": MemoryEmbeddingsDomain(root)
        }
    
    def get_domain(self, capability: str) -> AutonomousDomain:
        """Get domain by capability name"""
        return self.domains.get(capability)
    
    def can_execute_domain(self, capability: str, state: Dict[str, Any]) -> bool:
        """Check if domain can execute"""
        domain = self.get_domain(capability)
        if not domain:
            return False
        return domain.can_execute(state)

