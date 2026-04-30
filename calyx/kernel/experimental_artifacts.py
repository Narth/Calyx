from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def experimental_mode_enabled() -> bool:
    return os.environ.get("CALYX_EXPERIMENTAL_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def stamp_tag() -> str:
    return now_utc().strftime("%Y%m%d_%H%M%S")


def experimental_dir(runtime_dir: Path, component: str) -> Path:
    _ = component
    return runtime_dir / "receipts" / "experimental"


def with_experimental_labels(payload: dict[str, Any]) -> dict[str, Any]:
    labeled = dict(payload)
    labeled["surface_label"] = "experimental"
    labeled["execution_surface"] = "experimental"
    return labeled


def ensure_experimental_path(path: Path) -> None:
    parts = [p.lower() for p in path.parts]
    if "experimental" not in parts:
        raise RuntimeError(f"experimental artifact path required, got: {path}")


def write_experimental_json(path: Path, payload: dict[str, Any]) -> Path:
    ensure_experimental_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(with_experimental_labels(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def exact_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confirmation_path_for(receipt_path: Path, confirmer: str) -> Path:
    name = receipt_path.stem
    return receipt_path.parent / f"{confirmer}.receipt_confirmation__{name}.json"


def confirm_receipt(receipt_path: Path, confirmer: str = "openclaw") -> tuple[Path, bool]:
    sha = exact_sha256(receipt_path)
    path = confirmation_path_for(receipt_path, confirmer)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if (
            existing.get("confirmed_receipt_path") == str(receipt_path)
            and existing.get("confirmed_receipt_sha256") == sha
            and existing.get("confirmer") == confirmer
        ):
            return path, False
    payload = {
        "schema": "experimental.receipt_confirmation.v1",
        "confirmed_receipt_path": str(receipt_path),
        "confirmed_receipt_sha256": sha,
        "confirmed_at_ts_utc": now_utc().isoformat(),
        "confirmer": confirmer,
        "claim_scope": "Experimental observation indicates receipt was read and hash-confirmed by OpenClaw.",
        "clarifier": "Confirmation asserts comprehension only, not agreement, readiness, or baseline authority.",
    }
    write_experimental_json(path, payload)
    return path, True
