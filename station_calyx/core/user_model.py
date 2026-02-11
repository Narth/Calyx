"""UserModel artifact

One UserModel per user_id. Append-only/versioned storage in data/users/.
Records confirmed intents, rejected interpretations, clarification history and
confidence adjustments. Emits evidence events on updates.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .evidence import create_event, append_event
from .config import get_config


@dataclass
class ConfirmedIntentRecord:
    intent_id: str
    interpreted_goal: str
    confirmed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RejectedInterpretationRecord:
    intent_id: str
    interpreted_goal: str
    rejected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ClarificationRecord:
    intent_id: str
    question: str
    answer: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConfidenceAdjustment:
    reason: str
    delta: float
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserModel:
    user_id: str
    confirmed_intents: List[Dict[str, Any]] = field(default_factory=list)
    rejected_interpretations: List[Dict[str, Any]] = field(default_factory=list)
    clarification_history: List[Dict[str, Any]] = field(default_factory=list)
    confidence_adjustments: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "confirmed_intents": self.confirmed_intents,
            "rejected_interpretations": self.rejected_interpretations,
            "clarification_history": self.clarification_history,
            "confidence_adjustments": self.confidence_adjustments,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        return cls(
            user_id=data.get("user_id"),
            confirmed_intents=data.get("confirmed_intents", []),
            rejected_interpretations=data.get("rejected_interpretations", []),
            clarification_history=data.get("clarification_history", []),
            confidence_adjustments=data.get("confidence_adjustments", []),
            last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat()),
        )


def _users_dir() -> Path:
    cfg = get_config()
    p = cfg.data_dir / "users"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_user_model_path(user_id: str) -> Path:
    return _users_dir() / f"{user_id}.json"


def get_user_audit_sink_path() -> Path:
    return _users_dir() / "users.jsonl"


def load_user_model(user_id: str) -> UserModel:
    path = get_user_model_path(user_id)
    if not path.exists():
        return UserModel(user_id=user_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserModel.from_dict(data)
    except Exception:
        return UserModel(user_id=user_id)


def persist_user_model(model: UserModel) -> None:
    path = get_user_model_path(model.user_id)
    # Overwrite per-user snapshot for quick reads, but append full model to audit sink for versioning
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model.to_dict(), f, indent=2, ensure_ascii=False)

    sink = get_user_audit_sink_path()
    with open(sink, "a", encoding="utf-8") as f:
        f.write(json.dumps(model.to_dict(), ensure_ascii=False) + "\n")

    # Emit evidence event
    try:
        evt = create_event(
            event_type="USER_MODEL_UPDATED",
            node_role="user_model",
            summary=f"UserModel updated: {model.user_id}",
            payload={"user_id": model.user_id},
            tags=["user_model", "update"],
            session_id=model.user_id,
        )
        append_event(evt)
    except Exception:
        pass


def record_confirmation(user_id: str, intent_id: str, interpreted_goal: str) -> None:
    model = load_user_model(user_id)
    entry = {"intent_id": intent_id, "interpreted_goal": interpreted_goal, "confirmed_at": datetime.now(timezone.utc).isoformat()}
    model.confirmed_intents.append(entry)
    model.last_updated = datetime.now(timezone.utc).isoformat()
    # record confidence adjustment
    adj = {"reason": "user_confirmation", "delta": 0.2, "ts": model.last_updated}
    model.confidence_adjustments.append(adj)
    persist_user_model(model)


def record_rejection(user_id: str, intent_id: str, interpreted_goal: str) -> None:
    model = load_user_model(user_id)
    entry = {"intent_id": intent_id, "interpreted_goal": interpreted_goal, "rejected_at": datetime.now(timezone.utc).isoformat()}
    model.rejected_interpretations.append(entry)
    model.last_updated = datetime.now(timezone.utc).isoformat()
    adj = {"reason": "user_rejection", "delta": -0.25, "ts": model.last_updated}
    model.confidence_adjustments.append(adj)
    persist_user_model(model)


def record_clarification(user_id: str, intent_id: str, question: str, answer: str) -> None:
    model = load_user_model(user_id)
    entry = {"intent_id": intent_id, "question": question, "answer": answer, "ts": datetime.now(timezone.utc).isoformat()}
    model.clarification_history.append(entry)
    model.last_updated = datetime.now(timezone.utc).isoformat()
    persist_user_model(model)
