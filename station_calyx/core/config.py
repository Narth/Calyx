"""Station Calyx Configuration"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

COMPONENT_ROLE = "config"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

@dataclass
class IngestConfig:
    """Configuration for network evidence ingest."""
    # Token for authentication (required for network ingest)
    token: Optional[str] = field(default_factory=lambda: os.environ.get("CALYX_INGEST_TOKEN"))
    # Allowed node IDs (comma-separated, empty = allow all)
    allowed_node_ids: list[str] = field(default_factory=lambda: [
        n.strip() for n in os.environ.get("CALYX_ALLOWED_NODE_IDS", "").split(",") if n.strip()
    ])
    # Maximum envelopes per request
    max_envelopes: int = field(default_factory=lambda: int(os.environ.get("CALYX_INGEST_MAX_ENVELOPES", "100")))
    # Maximum request body size in bytes
    max_bytes: int = field(default_factory=lambda: int(os.environ.get("CALYX_INGEST_MAX_BYTES", "1048576")))  # 1MB default
    # Enable network ingest (must be explicitly enabled)
    enabled: bool = field(default_factory=lambda: os.environ.get("CALYX_INGEST_ENABLED", "").lower() == "true")

@dataclass
class StationConfig:
    station_name: str = "Station Calyx"
    version: str = "1.7.0-alpha"
    api_host: str = "127.0.0.1"
    api_port: int = 8420
    data_dir: Path = field(default_factory=lambda: DATA_DIR)
    evidence_path: Path = field(default_factory=lambda: DATA_DIR / "evidence.jsonl")
    summaries_dir: Path = field(default_factory=lambda: DATA_DIR / "summaries")
    decisions_dir: Path = field(default_factory=lambda: DATA_DIR / "decisions")
    execution_enabled: bool = False
    advisory_only: bool = True
    default_reflection_window: int = 100
    llm_enabled: bool = False
    llm_model: Optional[str] = None
    ingest: IngestConfig = field(default_factory=IngestConfig)
    
    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs" / "ingest").mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict[str, Any]:
        return {"station_name": self.station_name, "version": self.version, "api_host": self.api_host, "api_port": self.api_port, "advisory_only": self.advisory_only, "execution_enabled": self.execution_enabled}

_config: Optional[StationConfig] = None

def get_config() -> StationConfig:
    global _config
    if _config is None:
        _config = StationConfig()
        _config.ensure_directories()
    return _config
