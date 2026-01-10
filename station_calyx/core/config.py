"""Station Calyx Configuration"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

COMPONENT_ROLE = "config"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

@dataclass
class StationConfig:
    station_name: str = "Station Calyx"
    version: str = "1.0.0-alpha"
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
    
    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict[str, Any]:
        return {"station_name": self.station_name, "version": self.version, "api_host": self.api_host, "api_port": self.api_port, "advisory_only": self.advisory_only, "execution_enabled": self.execution_enabled}

_config: Optional[StationConfig] = None

def get_config() -> StationConfig:
    global _config
    if _config is None:
        _config = StationConfig()
        _config.ensure_directories()
    return _config
