#!/usr/bin/env python3
"""Recreate station_calyx core files with proper encoding."""
from pathlib import Path

# Evidence.py
evidence_py = '''"""Station Calyx Evidence Log"""
from __future__ import annotations
import hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

COMPONENT_ROLE = "evidence_store"
DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "data" / "evidence.jsonl"

def compute_sha256(payload_bytes: bytes) -> str:
    return hashlib.sha256(payload_bytes).hexdigest()

def generate_session_id() -> str:
    return str(uuid.uuid4())[:8]

def create_event(event_type: str, node_role: str, summary: str, payload: dict[str, Any], tags: Optional[list[str]] = None, session_id: Optional[str] = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    event = {"ts": now.isoformat(), "event_type": event_type, "node_role": node_role, "session_id": session_id or generate_session_id(), "summary": summary, "payload": payload, "tags": tags or []}
    event["_hash"] = compute_sha256(json.dumps(event, sort_keys=True).encode("utf-8"))
    return event

def append_event(event: dict[str, Any], evidence_path: Optional[Path] = None) -> None:
    path = evidence_path or DEFAULT_EVIDENCE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\\n")

def load_recent_events(n: int = 100, evidence_path: Optional[Path] = None) -> list[dict[str, Any]]:
    path = evidence_path or DEFAULT_EVIDENCE_PATH
    if not path.exists(): return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try: events.append(json.loads(line))
                except: pass
    return events[-n:] if len(events) > n else events

def get_last_event_ts(evidence_path: Optional[Path] = None) -> Optional[str]:
    events = load_recent_events(1, evidence_path)
    return events[-1]["ts"] if events else None
'''
Path('station_calyx/core/evidence.py').write_text(evidence_py, encoding='utf-8')
print("Created: evidence.py")

# Policy.py
policy_py = '''"""Station Calyx Policy Gate"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

COMPONENT_ROLE = "policy_gate"

class ExecutionResult(Enum):
    DENIED = "DENIED"
    ALLOWED = "ALLOWED"

@dataclass
class PolicyDecision:
    result: ExecutionResult
    reason: str
    timestamp: str
    request_type: str
    request_summary: str
    policy_version: str = "v1-deny-all"
    def to_dict(self) -> dict[str, Any]:
        return {"result": self.result.value, "reason": self.reason, "timestamp": self.timestamp, "request_type": self.request_type, "request_summary": self.request_summary, "policy_version": self.policy_version}

@dataclass
class ExecutionPolicy:
    deny_all: bool = True
    allow_list: list[str] = field(default_factory=list)
    policy_version: str = "v1-deny-all"
    advisory_only: bool = True
    execution_enabled: bool = False

class PolicyGate:
    def __init__(self, policy: Optional[ExecutionPolicy] = None):
        self.policy = policy or ExecutionPolicy()
        self._decision_count = 0
        self._denied_count = 0
    
    def evaluate(self, request_type: str, request_summary: str, context: Optional[dict[str, Any]] = None, log_decision: bool = True) -> PolicyDecision:
        now = datetime.now(timezone.utc)
        self._decision_count += 1
        self._denied_count += 1
        return PolicyDecision(result=ExecutionResult.DENIED, reason="EXECUTION_GATE: deny-all active (v1 advisory-only mode)", timestamp=now.isoformat(), request_type=request_type, request_summary=request_summary, policy_version=self.policy.policy_version)
    
    def get_stats(self) -> dict[str, Any]:
        return {"policy_version": self.policy.policy_version, "deny_all": self.policy.deny_all, "advisory_only": self.policy.advisory_only, "execution_enabled": self.policy.execution_enabled, "total_decisions": self._decision_count, "denied_count": self._denied_count}

_default_gate: Optional[PolicyGate] = None

def get_policy_gate() -> PolicyGate:
    global _default_gate
    if _default_gate is None: _default_gate = PolicyGate()
    return _default_gate

def request_execution(request_type: str, request_summary: str, context: Optional[dict[str, Any]] = None) -> PolicyDecision:
    return get_policy_gate().evaluate(request_type, request_summary, context)
'''
Path('station_calyx/core/policy.py').write_text(policy_py, encoding='utf-8')
print("Created: policy.py")

# Config.py
config_py = '''"""Station Calyx Configuration"""
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
'''
Path('station_calyx/core/config.py').write_text(config_py, encoding='utf-8')
print("Created: config.py")

print("All core files recreated!")
