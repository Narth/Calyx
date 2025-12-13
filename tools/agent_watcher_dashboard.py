"""Agent Watcher Dashboard (FastAPI)

Serves a simple web dashboard that shows system diagnostics, discovered agent
heartbeats (outgoing/*.lock files) and an interactive chat box to post commands
to the watcher/CBO via the existing file-based command mechanism
(`tools.agent_control.post_command`).

Run:
    python -u tools/agent_watcher_dashboard.py

Then open http://127.0.0.1:8000/

Notes / assumptions:
- Uses FastAPI (project already lists FastAPI in requirements).
- Chat box posts a command named `cbo_chat` with args {message: ...}.
  The watcher/CBO must implement handling for `cbo_chat`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import psutil
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from tools.agent_control import post_command
import asyncio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
REPLIES_DIR = OUT / "watcher_replies"
REPLIES_DIR.mkdir(parents=True, exist_ok=True)
LOCK_GLOB = OUT.glob("*.lock")

# bridge path (CBO integration)
BRIDGE_DIR = OUT / "bridge"
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)


def _write_bridge_request(kind: str, payload: Dict[str, Any]) -> Path:
    """Write a request file under outgoing/bridge to be picked up by CBO/bridge.

    Returns the path written.
    """
    import uuid
    name = f"{kind}_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}.json"
    p = BRIDGE_DIR / name
    body = {
        "ts": time.time(),
        "kind": kind,
        "payload": payload,
    }
    p.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

app = FastAPI(title="Calyx Agent Watcher Dashboard")

# serve static html
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _read_lock_file(path: Path) -> Dict[str, Any]:
    try:
        txt = path.read_text(encoding="utf-8")
        return json.loads(txt)
    except Exception:
        return {"__raw": path.name}


def list_agents() -> List[Dict[str, Any]]:
    """Discover outgoing/*.lock files and return simple agent records.

    Each lock file is expected to be JSON with at least `pid`, `ts`, and
    `status_message` fields. We tolerate missing fields.
    """
    agents: List[Dict[str, Any]] = []
    for p in sorted(OUT.glob("*.lock")):
        rec = _read_lock_file(p)
        agents.append({
            "file": p.name,
            "data": rec,
        })
    return agents


def system_diagnostics() -> Dict[str, Any]:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
    return {
        "ts": time.time(),
        "cpu_percent": cpu,
        "memory": {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "percent": vm.percent,
        },
        "load_avg": load,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = STATIC_DIR / "agent_watcher.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    # fallback minimal page
    return HTMLResponse(content="<html><body><h1>Agent Watcher Dashboard</h1><p>Static UI missing.</p></body></html>", status_code=200)


@app.get("/api/status")
def api_status():
    try:
        return JSONResponse({
            "system": system_diagnostics(),
            "agents": list_agents(),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


ALLOWED_COMMANDS = {"cbo_chat", "append_log", "set_banner", "open_path"}


@app.post("/api/command")
async def api_command(req: Request):
    payload = await req.json()
    cmd = payload.get("cmd")
    args = payload.get("args") or {}
    sender = payload.get("sender") or "watcher_ui"
    if cmd not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Command not allowed: {cmd}")
    try:
        p = post_command(cmd, args=args, sender=sender)
        # If this is a CBO chat request, also forward to bridge so CBO can pick it up
        if cmd == "cbo_chat":
            msg = {"from": sender, "message": args.get("message"), "source": "watcher_ui"}
            bridge_path = _write_bridge_request("cbo_chat", msg)
            return JSONResponse({"ok": True, "path": str(p), "bridge": str(bridge_path)})
        return JSONResponse({"ok": True, "path": str(p)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commands")
def api_commands(limit: int = 20):
    """Return recent watcher command files for debugging (most recent first)."""
    cmds_dir = OUT / "watcher_cmds"
    if not cmds_dir.exists():
        return JSONResponse([])
    files = sorted(cmds_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out = []
    for p in files:
        try:
            txt = p.read_text(encoding="utf-8")
            j = json.loads(txt)
        except Exception:
            j = {"__raw": p.name}
        out.append({
            "file": p.name,
            "ts": p.stat().st_mtime,
            "cmd": j.get("cmd") if isinstance(j, dict) else None,
            "from": j.get("from") if isinstance(j, dict) else None,
            "args": j.get("args") if isinstance(j, dict) else j,
        })
    return JSONResponse(out)


@app.get("/api/command/{name}")
def api_command_file(name: str):
    p = OUT / "watcher_cmds" / name
    if not p.exists():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        txt = p.read_text(encoding="utf-8")
        j = json.loads(txt)
    except Exception:
        j = {"__raw": txt}
    return JSONResponse({"file": name, "content": j})


@app.post("/api/debug/reply_demo")
def api_debug_reply_demo():
    """Create a demo reply file in outgoing/watcher_replies to simulate CBO response."""
    REPLIES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time(), "from": "cbo", "text": "Demo reply from CBO", "demo": True}
    name = f"demo_reply_{int(time.time()*1000)}.json"
    p = REPLIES_DIR / name
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse({"ok": True, "path": str(p), "payload": payload})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket that:
    - accepts client command messages (JSON) and posts them using post_command
    - streams periodic status updates (type='status')
    - streams watcher replies written to `outgoing/watcher_replies/` (type='reply')
    """
    await websocket.accept()
    seen = set()
    try:
        async def send_status_loop():
            while True:
                data = {"system": system_diagnostics(), "agents": list_agents()}
                try:
                    await websocket.send_text(json.dumps({"type": "status", "payload": data}))
                except Exception:
                    break
                await asyncio.sleep(2.0)

        async def watch_replies_loop():
            while True:
                for p in sorted(REPLIES_DIR.glob("*.json")):
                    if p.name in seen:
                        continue
                    try:
                        txt = p.read_text(encoding="utf-8")
                        payload = json.loads(txt)
                    except Exception:
                        payload = {"__raw": p.name}
                    seen.add(p.name)
                    try:
                        await websocket.send_text(json.dumps({"type": "reply", "file": p.name, "payload": payload}))
                    except Exception:
                        return
                await asyncio.sleep(1.0)

        async def recv_loop():
            while True:
                msg = await websocket.receive_text()
                try:
                    j = json.loads(msg)
                except Exception:
                    # ignore non-json
                    continue
                if j.get("type") == "command":
                    cmd = j.get("cmd")
                    args = j.get("args") or {}
                    sender = j.get("sender") or "watcher_ws"
                    if cmd not in ALLOWED_COMMANDS:
                        await websocket.send_text(json.dumps({"type": "ack", "ok": False, "error": f"not allowed: {cmd}"}))
                        continue
                    try:
                        p = post_command(cmd, args=args, sender=sender)
                        # forward chat to bridge so CBO/bridge can see it even if watcher doesn't
                        if cmd == "cbo_chat":
                            msg = {"from": sender, "message": args.get("message"), "source": "watcher_ws"}
                            bridge_path = _write_bridge_request("cbo_chat", msg)
                            await websocket.send_text(json.dumps({"type": "ack", "ok": True, "path": str(p), "bridge": str(bridge_path)}))
                        else:
                            await websocket.send_text(json.dumps({"type": "ack", "ok": True, "path": str(p)}))
                    except Exception as e:
                        await websocket.send_text(json.dumps({"type": "ack", "ok": False, "error": str(e)}))

        # run tasks concurrently until disconnect
        await asyncio.gather(send_status_loop(), watch_replies_loop(), recv_loop())

    except WebSocketDisconnect:
        return
    except Exception:
        return


if __name__ == "__main__":
    # default dev server
    uvicorn.run("tools.agent_watcher_dashboard:app", host="127.0.0.1", port=8000, reload=False)
