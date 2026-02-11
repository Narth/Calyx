"""Intent Artifact - Phase 1
=================================

Defines the Intent Artifact as a first-class object and helpers to persist
and audit intent artifacts. This module intentionally accepts artifacts as-
provided and does not reinterpret user meaning.

Minimum fields:
 - intent_id
 - raw_user_input
 - interpreted_goal
 - constraints
 - confidence_score
 - clarification_required (bool)

Responsibilities:
 - Persist intent artifact to disk (per-intent JSON)
 - Append intent artifact to immutable audit sink (JSONL)
 - Emit an evidence event for intent creation
 - Provide a check that enforces clarification threshold
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .evidence import append_event, create_event
from .config import get_config

DEFAULT_CONFIDENCE_THRESHOLD = 0.80
# Rotation / retention configuration
# Read from environment to avoid changing global config structure.
import os
DEFAULT_AUDIT_MAX_MB = int(os.environ.get("CALYX_INTENT_AUDIT_MAX_MB", "5"))
DEFAULT_AUDIT_KEEP_DAYS = int(os.environ.get("CALYX_INTENT_AUDIT_KEEP_DAYS", "30"))


class ClarificationRequired(Exception):
    """Raised when an intent artifact requires clarification before proceeding."""


@dataclass
class IntentArtifact:
    intent_id: str
    raw_user_input: str
    interpreted_goal: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    clarification_required: bool = False
    inferred_from_user_model: bool = False
    user_model_summary: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "raw_user_input": self.raw_user_input,
            "interpreted_goal": self.interpreted_goal,
            "constraints": self.constraints,
            "confidence_score": float(self.confidence_score),
            "clarification_required": bool(self.clarification_required),
            "inferred_from_user_model": bool(self.inferred_from_user_model),
            "user_model_summary": self.user_model_summary,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentArtifact":
        return cls(
            intent_id=data["intent_id"],
            raw_user_input=data.get("raw_user_input", ""),
            interpreted_goal=data.get("interpreted_goal", ""),
            constraints=data.get("constraints", {}),
            confidence_score=float(data.get("confidence_score", 0.0)),
            clarification_required=bool(data.get("clarification_required", False)),
            inferred_from_user_model=bool(data.get("inferred_from_user_model", False)),
            user_model_summary=data.get("user_model_summary", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


def _intents_dir() -> Path:
    cfg = get_config()
    p = cfg.data_dir / "intents"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_artifact_path(intent_id: str) -> Path:
    return _intents_dir() / f"{intent_id}.json"


def get_audit_sink_path() -> Path:
    return _intents_dir() / "artifacts.jsonl"


def persist_intent_artifact(artifact: IntentArtifact) -> None:
    """Persist artifact to disk and append to immutable audit sink."""
    path = get_artifact_path(artifact.intent_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
    # Append to immutable audit sink (JSON Lines)
    sink = get_audit_sink_path()
    # Acquire simple lock while writing to the audit sink
    lock_path = sink.with_suffix('.lock')
    with _file_lock(lock_path):
        _rotate_audit_sink_if_needed(sink)
        # Atomic append: write to temp file then append
        tmp = sink.with_suffix('.tmp')
        with open(tmp, "a", encoding="utf-8") as f:
            f.write(json.dumps(artifact.to_dict(), ensure_ascii=False) + "\n")
        try:
            with open(sink, "a", encoding="utf-8") as fs, open(tmp, "r", encoding="utf-8") as ft:
                fs.write(ft.read())
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
        # Stale-lock protection: if lockfile exists and contains PID/timestamp, ignore if older than expiry
        try:
            if lock_path.exists():
                try:
                    content = lock_path.read_text(encoding='utf-8')
                    # Expected format: "pid:<pid>\nts:<iso>"
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    info = {k: v for k, v in (ln.split(':',1) for ln in lines if ':' in ln)}
                    ts = info.get('ts')
                    if ts:
                        try:
                            tstamp = datetime.fromisoformat(ts).timestamp()
                            if (time.time() - tstamp) > 3600:
                                try:
                                    lock_path.unlink()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # Emit evidence event for auditability
    evt = create_event(
        event_type="INTENT_ARTIFACT_CREATED",
        node_role="intent_manager",
        summary=f"Intent artifact created: {artifact.intent_id}",
        payload={"intent_id": artifact.intent_id, "confidence_score": artifact.confidence_score},
        tags=["intent", "artifact"],
        session_id=artifact.intent_id,
    )
    append_event(evt)


def load_intent_artifact(intent_id: str) -> Optional[IntentArtifact]:
    path = get_artifact_path(intent_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return IntentArtifact.from_dict(data)
    except Exception:
        return None


def _rotate_audit_sink_if_needed(sink: Path, max_mb: int = DEFAULT_AUDIT_MAX_MB, keep_days: int = DEFAULT_AUDIT_KEEP_DAYS) -> None:
    """Rotate audit sink if it exceeds size threshold and remove old rotations.

    Rotation strategy: if current sink size > max_mb, rename it with timestamp
    suffix and start a new sink file. Then remove rotated files older than
    keep_days.
    """
    try:
        if not sink.exists():
            return
        size_mb = sink.stat().st_size / (1024 * 1024)
        if size_mb <= float(max_mb):
            return

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rotated = sink.with_name(sink.name + "." + ts)
        try:
            sink.replace(rotated)
        except Exception:
            # best-effort rename
            sink.rename(rotated)

        # Cleanup old rotated files
        cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 24 * 3600)
        for f in sink.parent.iterdir():
            if f.is_file() and f.name.startswith(sink.name + "."):
                try:
                    mtime = f.stat().st_mtime
                    if mtime < cutoff:
                        f.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def maintain_audit_sink(sink: Optional[Path] = None, max_mb: Optional[int] = None, keep_days: Optional[int] = None) -> None:
    """Public maintenance utility to rotate and clean up audit sink deterministically.

    This can be invoked by operator CLI to run rotation and retention cleanup.
    """
    sink = sink or get_audit_sink_path()
    _rotate_audit_sink_if_needed(sink, max_mb or DEFAULT_AUDIT_MAX_MB, keep_days or DEFAULT_AUDIT_KEEP_DAYS)


import time
from contextlib import contextmanager


@contextmanager
def _file_lock(lock_path: Path, timeout: float = 5.0):
    """Simple cross-platform lock using os.O_EXCL on a lockfile.

    This is not a high-performance lock but avoids simple race conditions.
    """
    start = time.time()
    acquired = False
    while True:
        try:
            # Write PID and timestamp into lockfile for stale-lock analysis
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(f"pid:{os.getpid()}\n")
                fh.write(f"ts:{datetime.now(timezone.utc).isoformat()}\n")
            acquired = True
            break
        except FileExistsError:
            if (time.time() - start) > timeout:
                break
            time.sleep(0.05)
        except Exception:
            break

    try:
        yield
    finally:
        if acquired:
            try:
                lock_path.unlink()
            except Exception:
                pass
        else:
            # If lock couldn't be acquired, check for stale lock older than 1 hour and remove
            try:
                if lock_path.exists():
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) > 3600:
                        try:
                            lock_path.unlink()
                        except Exception:
                            pass
            except Exception:
                pass


def require_clarified(artifact: IntentArtifact, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
    """Enforce that the artifact meets the confidence threshold.

    If the artifact confidence is below threshold, raise ClarificationRequired.
    Governance or execution stages MUST call this function before acting on
    an intent artifact to guarantee that clarification has occurred.
    """
    if artifact.confidence_score < float(threshold) or artifact.clarification_required:
        # Log a low-confidence event
        evt = create_event(
            event_type="INTENT_CLARIFICATION_REQUIRED",
            node_role="intent_manager",
            summary=f"Intent requires clarification: {artifact.intent_id}",
            payload={"intent_id": artifact.intent_id, "confidence_score": artifact.confidence_score},
            tags=["intent", "clarification", "hold"],
            session_id=artifact.intent_id,
        )
        append_event(evt)
        raise ClarificationRequired(f"Intent {artifact.intent_id} requires clarification (confidence={artifact.confidence_score})")


def accept_intent_artifact(artifact: IntentArtifact) -> None:
    """Accept and persist an intent artifact as-is.

    This function does NOT reinterpret or mutate the artifact; it only
    persists and logs it for downstream stages. Downstream stages (planner,
    governance) must call `require_clarified` before taking action.
    """
    persist_intent_artifact(artifact)
