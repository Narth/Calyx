"""Input adapters that keep the CBO informed about Station state."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ensure_list

try:  # Optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


LOGGER = logging.getLogger("cbo.sensors")


class SensorHub:
    """Aggregates policy, registry, and metrics into a unified snapshot."""

    def __init__(
        self,
        root: Path,
        *,
        policy_path: Optional[Path] = None,
        registry_path: Optional[Path] = None,
        metrics_path: Optional[Path] = None,
    ) -> None:
        self.root = root
        self.policy_path = policy_path or (root / "calyx" / "core" / "policy.yaml")
        self.registry_path = registry_path or (root / "calyx" / "core" / "registry.jsonl")
        self.metrics_path = metrics_path or (root / "metrics" / "bridge_pulse.csv")

    def load_policy(self) -> Dict[str, Any]:
        """Return current policy document, defaulting to safe values."""

        if not self.policy_path.exists():
            LOGGER.warning("Policy file missing at %s", self.policy_path)
            return {
                "allow_api": False,
                "max_cpu_pct": 60,
                "max_ram_pct": 70,
                "allow_unregistered_agents": False,
            }

        contents = self.policy_path.read_text(encoding="utf-8")

        if yaml:
            try:
                parsed = yaml.safe_load(contents) or {}
                if isinstance(parsed, dict):
                    return parsed
                LOGGER.warning("Unexpected policy structure (not dict)")
            except Exception as exc:  # pragma: no cover
                LOGGER.error("Failed to parse policy.yaml: %s", exc)

        # Minimal fallback parser for simple key-value pairs
        policy: Dict[str, Any] = {}
        for line in contents.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            policy[key.strip()] = value.strip()
        return policy

    def load_registry(self) -> List[Dict[str, Any]]:
        """Read the agent registry JSONL file."""

        if not self.registry_path.exists():
            LOGGER.warning("Registry missing at %s", self.registry_path)
            return []

        records: List[Dict[str, Any]] = []
        try:
            for line in self.registry_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    LOGGER.error("Invalid JSON in registry: %s", line)
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Failed to read registry: %s", exc)
        return records

    def load_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the latest metrics records, if available."""

        if not self.metrics_path.exists():
            LOGGER.debug("Metrics file missing at %s", self.metrics_path)
            return []

        rows: List[Dict[str, Any]] = []
        try:
            with self.metrics_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append(row)
            if limit > 0:
                rows = rows[-limit:]
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Failed to read metrics: %s", exc)
        return rows

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Calculate disk usage for monitoring and alerting."""
        outgoing_dir = self.root / "outgoing"
        logs_dir = self.root / "logs"
        archive_dir = logs_dir / "archive"
        
        def get_size(path: Path) -> int:
            """Get total size of directory in bytes."""
            if not path.exists():
                return 0
            total = 0
            try:
                for item in path.rglob('*'):
                    if item.is_file():
                        total += item.stat().st_size
            except Exception as e:
                LOGGER.debug(f"Error calculating size for {path}: {e}")
            return total
        
        def get_file_count(path: Path) -> int:
            """Get total file count in directory."""
            if not path.exists():
                return 0
            try:
                return sum(1 for _ in path.rglob('*') if _.is_file())
            except Exception:
                return 0
        
        outgoing_size = get_size(outgoing_dir)
        logs_size = get_size(logs_dir)
        archive_size = get_size(archive_dir)
        total_size = outgoing_size + logs_size
        
        outgoing_files = get_file_count(outgoing_dir)
        archive_files = get_file_count(archive_dir)
        
        # Convert to GB
        outgoing_gb = outgoing_size / (1024 ** 3)
        logs_gb = logs_size / (1024 ** 3)
        archive_gb = archive_size / (1024 ** 3)
        total_gb = total_size / (1024 ** 3)
        
        # Alert thresholds (configurable via policy)
        warning_threshold = 10.0  # GB
        critical_threshold = 20.0  # GB
        
        return {
            "outgoing": {
                "size_bytes": outgoing_size,
                "size_gb": round(outgoing_gb, 2),
                "file_count": outgoing_files,
            },
            "logs": {
                "size_bytes": logs_size,
                "size_gb": round(logs_gb, 2),
                "file_count": get_file_count(logs_dir),
            },
            "archive": {
                "size_bytes": archive_size,
                "size_gb": round(archive_gb, 2),
                "file_count": archive_files,
            },
            "total": {
                "size_bytes": total_size,
                "size_gb": round(total_gb, 2),
                "file_count": outgoing_files + archive_files,
            },
            "alert_status": (
                "critical" if total_gb >= critical_threshold
                else "warning" if total_gb >= warning_threshold
                else "ok"
            ),
            "last_archival": self._get_last_archival_date(),
        }
    
    def _get_last_archival_date(self) -> Optional[str]:
        """Get the date of the most recent archival operation."""
        archive_dir = self.root / "logs" / "archive"
        if not archive_dir.exists():
            return None
        
        try:
            # Find most recent archive report
            reports = list(archive_dir.glob("archive_report_*.json"))
            if reports:
                most_recent = max(reports, key=lambda p: p.stat().st_mtime)
                return datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat()
        except Exception:
            pass
        
        return None

    def snapshot(self) -> Dict[str, Any]:
        """Gather a unified view of the Station for planning."""

        return {
            "observed_at": datetime.utcnow().isoformat(),
            "policy": self.load_policy(),
            "registry": ensure_list(self.load_registry()),
            "metrics": ensure_list(self.load_recent_metrics()),
            "disk_usage": self._get_disk_usage(),
        }
