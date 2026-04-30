"""
Failure Event Writer — rate-limited, append-only, lifecycle-aware.
Writes to runtime/failure_events/*.jsonl and optionally emits a ledger event.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _resolve_repo_root() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def _failure_events_dir(root: Path) -> Path:
    return root / "runtime" / "failure_events"


def _index_path(root: Path) -> Path:
    return _failure_events_dir(root) / "_index.json"


def _lock_path(root: Path) -> Path:
    return _failure_events_dir(root) / ".lock"


def _events_path(root: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _failure_events_dir(root) / f"failure_events__{day}.jsonl"


def _read_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return json.loads(text)


def _internal_errors_path(root: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _failure_events_dir(root) / f"internal_errors__{day}.log"


def _log_internal_error(where: str, exc: Exception, fingerprint: str | None = None) -> None:
    try:
        root = _resolve_repo_root()
        _failure_events_dir(root).mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        err = (str(exc) or "unknown")[:300].replace("\n", "\\n")
        fp = (fingerprint or "")[:64]
        line = f"{ts} | {where} | {err} | fp={fp}\n"
        with _internal_errors_path(root).open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc2:
        try:
            from calyx.kernel.event_ledger import emit as ledger_emit
            ledger_emit(
                level="WARN",
                component="failure_event",
                event="failure_event.internal_error",
                msg="Internal failure_event error",
                data={"where": where[:120], "err": (str(exc2) or "unknown")[:200]},
            )
        except Exception:
            return


def _load_index(root: Path) -> dict:
    try:
        path = _index_path(root)
        if not path.exists():
            return {"entries": {}}
        data = _read_json(path)
        if isinstance(data, dict) and "entries" in data:
            return data
        return {"entries": {}}
    except Exception as exc:
        _log_internal_error("failure_event.load_index", exc)
        return {"entries": {}}


def _write_index(root: Path, index: dict) -> None:
    try:
        path = _index_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        _log_internal_error("failure_event.write_index", exc)


def _normalize_data(data: dict | None) -> str:
    if not isinstance(data, dict):
        return ""
    subset: dict[str, str] = {}
    exclude = {"ts", "ts_utc", "duration_ms", "wall_time_ms"}
    present_keys = {"stdout_tail", "stderr_tail", "stdout", "stderr"}
    for k in sorted(data.keys())[:12]:
        key = str(k)[:64]
        if key in exclude:
            continue
        v = data.get(k)
        if key in present_keys:
            v = "<present>" if v else ""
        if isinstance(v, (dict, list)):
            v = json.dumps(v, sort_keys=True, ensure_ascii=False)
        else:
            v = str(v)
        subset[key] = v[:200]
    return json.dumps(subset, sort_keys=True, ensure_ascii=False)


def _fingerprint(level: str, component: str, event: str, msg: str, data: dict | None) -> str:
    payload = "|".join(
        [
            (level or "").strip().upper(),
            (component or "").strip(),
            (event or "").strip(),
            (msg or "").strip(),
            _normalize_data(data),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_lifecycle(root: Path) -> dict[str, Any] | None:
    try:
        path = root / "runtime" / "station_heartbeat.json"
        if not path.exists():
            return None
        data = _read_json(path)
        lifecycle: dict[str, Any] = {}
        for key in (
            "heartbeat_emitted_ts",
            "station_boot_ts",
            "boot_session_id",
            "memory_pressure_tier",
            "heartbeat_payload_sha256",
            "service_snapshot_sha256",
        ):
            val = data.get(key)
            if val not in (None, "", []):
                lifecycle[key] = val
        return lifecycle or None
    except Exception as exc:
        _log_internal_error("failure_event.load_lifecycle", exc)
        return None


def _acquire_lock(root: Path, timeout_s: float = 0.2) -> bool:
    path = _lock_path(root)
    deadline = time.perf_counter() + max(0.0, float(timeout_s))
    while time.perf_counter() < deadline:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8"))
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            time.sleep(0.02)
        except Exception as exc:
            _log_internal_error("failure_event.acquire_lock", exc)
            return False
    return False


def _release_lock(root: Path) -> None:
    try:
        os.remove(_lock_path(root))
    except Exception as exc:
        _log_internal_error("failure_event.release_lock", exc)


def write_failure_event(
    level: str,
    component: str,
    event: str,
    msg: str,
    data: dict | None = None,
    *,
    task_corr_id: str | None = None,
    task_name: str | None = None,
    schedule_id: str | None = None,
    trigger_reason: str | None = None,
    cooldown_s: int = 300,
) -> dict[str, Any]:
    """
    Write a rate-limited failure event to runtime/failure_events/*.jsonl.
    Returns a result dict with written/suppressed info.
    """
    root = _resolve_repo_root()
    _failure_events_dir(root).mkdir(parents=True, exist_ok=True)

    level_norm = (level or "WARN").strip().upper()
    component_norm = (component or "unknown").strip()[:64]
    event_norm = (event or "unknown").strip()[:128]
    msg_norm = (msg or "").strip()[:1024]
    fp = _fingerprint(level_norm, component_norm, event_norm, msg_norm, data)

    now_epoch = time.time()
    lock_acquired = _acquire_lock(root, timeout_s=0.2)
    entry = {"last_written_epoch": 0, "suppressed_count": 0}
    last_written = 0.0
    index = {"entries": {}}
    entries = index.get("entries", {})
    try:
        if lock_acquired:
            index = _load_index(root)
            entries = index.get("entries", {})
            entry = entries.get(fp) or {"last_written_epoch": 0, "suppressed_count": 0}
            last_written = float(entry.get("last_written_epoch") or 0)
            if now_epoch - last_written < max(0, int(cooldown_s)):
                entry["suppressed_count"] = int(entry.get("suppressed_count") or 0) + 1
                entries[fp] = entry
                index["entries"] = entries
                _write_index(root, index)
                return {
                    "written": False,
                    "suppressed": True,
                    "fingerprint": fp,
                    "suppressed_count": entry["suppressed_count"],
                    "cooldown_s": cooldown_s,
                    "last_written_epoch": last_written,
                }

        lifecycle = _load_lifecycle(root)
        record: dict[str, Any] = {
            "schema": "failure_event.v1",
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "level": level_norm,
            "component": component_norm,
            "event": event_norm,
            "msg": msg_norm,
            "data": data or {},
            "fingerprint": fp,
            "task_corr_id": task_corr_id,
            "task_name": task_name,
            "schedule_id": schedule_id,
            "trigger_reason": trigger_reason,
        }
        if lifecycle:
            record["lifecycle"] = lifecycle

        try:
            path = _events_path(root)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            _log_internal_error("failure_event.write_jsonl", exc, fp)

        if lock_acquired:
            entry["last_written_epoch"] = now_epoch
            entries[fp] = entry
            index["entries"] = entries
            _write_index(root, index)

        try:
            from calyx.kernel.event_ledger import emit as ledger_emit
            ledger_emit(
                level="INFO",
                component=component_norm,
                event="failure_event.logged",
                msg="Failure event written",
                data={"fingerprint": fp, "event": event_norm, "level": level_norm, "path": str(_events_path(root))},
                task_corr_id=task_corr_id,
                task_name=task_name,
                schedule_id=schedule_id,
                trigger_reason=trigger_reason,
            )
        except Exception as exc:
            _log_internal_error("failure_event.emit_ledger", exc, fp)
    finally:
        if lock_acquired:
            _release_lock(root)

    return {
        "written": True,
        "suppressed": False,
        "fingerprint": fp,
        "suppressed_count": entry.get("suppressed_count", 0),
        "cooldown_s": cooldown_s,
        "last_written_epoch": now_epoch,
    }
