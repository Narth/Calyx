"""Service re-init and operational verification for Phase 3.

Performs preflight snapshot, stops stale processes, clears bytecode caches,
restarts handlers in SAFE MODE, verifies evidence chains for dashboard and
(simulated) Discord, and writes a system status artifact.

Run: python tools/reinit_services.py
"""
from __future__ import annotations

import os
import sys
import subprocess
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from station_calyx.core.evidence import create_event, append_event, load_recent_events
from station_calyx.core.system_mode import set_system_mode, get_system_mode
from station_calyx.core.config import get_config
from tools.svf_channels import send_message, get_recent_messages
from tools.dashboard_message_handler import process_dashboard_messages
from station_calyx.core.intent_gateway import process_inbound_message

SERVICES = [
    {"name": "dashboard_handler", "cmd": [sys.executable, "tools/dashboard_message_handler.py"]},
    {"name": "discord_handler", "cmd": [sys.executable, "station_calyx/integrations/discord_handler.py"]},
]

PIDS: Dict[str, int] = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def emit(evt_type: str, node_role: str, summary: str, payload: Dict[str, Any] = None, tags: List[str] | None = None, session_id: str | None = None):
    evt = create_event(event_type=evt_type, node_role=node_role, summary=summary, payload=payload or {}, tags=tags or [], session_id=session_id)
    append_event(evt)
    return evt


def preflight_snapshot() -> Dict[str, Any]:
    # Git state
    branch = None
    commit = None
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT), stderr=subprocess.DEVNULL).decode().strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        branch = "unknown"
        commit = "unknown"

    py_ver = sys.version
    venv = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX") or None

    cfg = get_config()
    cfg_summary = cfg.to_dict()

    snapshot = {
        "branch": branch,
        "commit": commit,
        "python": py_ver,
        "venv": venv,
        "config": cfg_summary,
        "ts": now_iso(),
    }

    emit("SYSTEM_REINIT_BEGIN", "system_reinit", "System reinit begin", payload=snapshot, tags=["reinit"])
    return snapshot


def stop_stale_processes():
    # Best-effort: attempt to find processes by name using tasklist on Windows or ps on Unix
    stopped = []
    for svc in SERVICES:
        name = svc["name"]
        # emit stop requested
        emit("SERVICE_STOP_REQUESTED", "system_reinit", f"Stop requested for {name}", payload={"service": name})
        # Attempt to kill any process whose cmdline contains the service script
        killed = False
        try:
            import psutil
            for p in psutil.process_iter(attrs=['pid','cmdline']):
                try:
                    cmd = " ".join(p.info.get('cmdline') or [])
                    if svc["cmd"][-1] in cmd or svc["name"] in cmd:
                        p.kill()
                        p.wait(timeout=3)
                        killed = True
                        emit("SERVICE_STOPPED", "system_reinit", f"Stopped {name}", payload={"service": name, "pid": p.pid})
                except Exception:
                    continue
        except Exception:
            # fallback: nothing to kill
            pass
        if not killed:
            # still emit stopped for idempotence
            emit("SERVICE_STOPPED", "system_reinit", f"No running instance of {name}", payload={"service": name})
        stopped.append({"service": name, "stopped": True})
    return stopped


def clear_bytecode_caches():
    # Remove __pycache__ and .pyc files under relevant dirs
    paths = [ROOT / 'tools', ROOT / 'station_calyx', ROOT / 'calyx']
    removed = []
    for p in paths:
        for root, dirs, files in os.walk(p):
            for d in dirs:
                if d == '__pycache__':
                    full = Path(root) / d
                    try:
                        for f in full.iterdir():
                            f.unlink()
                        full.rmdir()
                        removed.append(str(full))
                    except Exception:
                        continue
            for f in files:
                if f.endswith('.pyc'):
                    try:
                        (Path(root) / f).unlink()
                        removed.append(str(Path(root) / f))
                    except Exception:
                        pass
    emit("SYSTEM_BYTECODE_CLEANED", "system_reinit", "Cleared python bytecode caches", payload={"removed": removed})
    return removed


def verify_schemas() -> Dict[str, Any]:
    # Verify IntentArtifact fields and UserModel presence
    ok = True
    details = {}
    try:
        from station_calyx.core.intent_artifact import IntentArtifact
        ia_fields = list(IntentArtifact.__dataclass_fields__.keys())
        details['intent_artifact_fields'] = ia_fields
        if 'inferred_from_user_model' not in ia_fields:
            ok = False
    except Exception as e:
        details['intent_artifact_error'] = str(e)
        ok = False

    try:
        from station_calyx.core.user_model import UserModel
        um_fields = list(UserModel.__dataclass_fields__.keys())
        details['user_model_fields'] = um_fields
    except Exception as e:
        details['user_model_error'] = str(e)
        ok = False

    emit("SYSTEM_SCHEMA_VERIFIED", "system_reinit", "Schema verification", payload={"ok": ok, "details": details})
    return {"ok": ok, "details": details}


def start_services() -> List[Dict[str, Any]]:
    started = []
    for svc in SERVICES:
        name = svc['name']
        cmd = svc['cmd']
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            PIDS[name] = p.pid
            emit("SERVICE_ONLINE", name, f"Service {name} online", payload={"service": name, "pid": p.pid, "cmd": cmd, "mode": get_system_mode()}, tags=["service","online"])
            started.append({"service": name, "pid": p.pid})
        except Exception as e:
            emit("SERVICE_START_FAILED", name, f"Failed to start {name}", payload={"error": str(e)})
    return started


def healthcheck_dashboard() -> Dict[str, Any]:
    # Send a dashboard message (router must be set)
    mid = send_message(sender='dashboard', message='ping-ui-live-1', channel='standard', context={})
    # allow handlers to pick up
    time.sleep(0.5)
    process_dashboard_messages()
    # collect recent events
    ev = load_recent_events(100)
    types = [e.get('event_type') for e in ev[-40:]]
    chain = ['OUTBOUND_MESSAGE_WRITTEN','MESSAGE_RECEIVED','INTENT_ARTIFACT_CREATED','CLARIFICATION_REQUESTED','MESSAGE_ACK_SENT']
    found = {t: (t in types) for t in chain}
    emit('HEALTHCHECK_DASHBOARD', 'system_reinit', 'Dashboard healthcheck completed', payload={'message_id': mid, 'found': found})
    return {'message_id': mid, 'found': found}


def healthcheck_discord() -> Dict[str, Any]:
    # Simulated ping via SVF file
    discord_sender = '1234567890'
    mid = send_message(sender=discord_sender, message='ping-live-1', channel='standard', context={})
    # Ingest directly
    res = process_inbound_message(channel='discord', sender=discord_sender, message='ping-live-1', metadata={'message_id': mid, 'user_id': discord_sender})
    ev = load_recent_events(100)
    types = [e.get('event_type') for e in ev[-40:]]
    chain = ['OUTBOUND_MESSAGE_WRITTEN','MESSAGE_RECEIVED','INTENT_ARTIFACT_CREATED','CLARIFICATION_REQUESTED','MESSAGE_ACK_SENT']
    found = {t: (t in types) for t in chain}
    # Determine discord online status: in this env, we consider simulated ok; real token not checked here
    status = 'SIMULATED'
    emit('HEALTHCHECK_DISCORD', 'system_reinit', 'Discord healthcheck completed', payload={'message_id': mid, 'found': found, 'status': status})
    return {'message_id': mid, 'found': found, 'status': status}


def write_status_artifact(start_snapshot: Dict[str, Any], started: List[Dict[str, Any]], dash_check: Dict[str, Any], disc_check: Dict[str, Any]) -> Path:
    cfg = get_config()
    out = Path.cwd() / 'outgoing' / 'shared_logs'
    out.mkdir(parents=True, exist_ok=True)
    status = out / 'system_status.md'
    lines = []
    lines.append(f"# System Status - {now_iso()}\n")
    lines.append(f"SAFE_MODE: {get_system_mode()}\n")
    lines.append("## Services")
    for s in started:
        lines.append(f"- {s['service']}: pid={s['pid']}\n")
    lines.append("## Dashboard healthcheck")
    lines.append(json.dumps(dash_check, indent=2))
    lines.append("\n## Discord healthcheck")
    lines.append(json.dumps(disc_check, indent=2))
    status.write_text("\n".join(lines), encoding='utf-8')
    emit('SYSTEM_REINIT_COMPLETE', 'system_reinit', 'Reinit complete', payload={'status_path': str(status)})
    return status


def main():
    snap = preflight_snapshot()
    stop_stale_processes()
    clear_bytecode_caches()
    verify_schemas()
    # Ensure safe mode
    set_system_mode(safe_mode=True, deny_execution=True, reason='Phase 3/Intent Operational Reinit')
    started = start_services()
    time.sleep(0.5)
    dash = healthcheck_dashboard()
    disc = healthcheck_discord()
    status_path = write_status_artifact(snap, started, dash, disc)
    print('Reinit complete. Status:', status_path)


if __name__ == '__main__':
    main()
