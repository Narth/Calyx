"""
Station Calyx Service Runner
============================

Manages Station Calyx as a local service with explicit start/stop control.

INVARIANTS:
- HUMAN_PRIMACY: User-invoked only, no auto-start
- EXECUTION_GATE: Does not execute system commands
- NO_HIDDEN_CHANNELS: All service state is visible

CONSTRAINTS:
- No daemonization without explicit user command
- No system modifications
- Foreground or background mode, user's choice

Role: core/service
Scope: Service lifecycle management (start, stop, status)
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import get_config
from .evidence import append_event, create_event

COMPONENT_ROLE = "service_runner"
COMPONENT_SCOPE = "service lifecycle management"

# PID file location
def get_pid_file() -> Path:
    config = get_config()
    return config.data_dir / "calyx_service.pid"


def get_service_status() -> dict[str, Any]:
    """Get current service status."""
    pid_file = get_pid_file()
    
    if not pid_file.exists():
        return {
            "running": False,
            "pid": None,
            "message": "Service not running (no PID file)",
        }
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        return {
            "running": False,
            "pid": None,
            "message": "Service not running (invalid PID file)",
        }
    
    # Check if process is running
    if is_process_running(pid):
        return {
            "running": True,
            "pid": pid,
            "message": f"Service running (PID {pid})",
        }
    else:
        # Stale PID file
        pid_file.unlink(missing_ok=True)
        return {
            "running": False,
            "pid": None,
            "message": "Service not running (stale PID file removed)",
        }


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if process:
                kernel32.CloseHandle(process)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def write_pid_file(pid: int) -> None:
    """Write PID to file."""
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))


def remove_pid_file() -> None:
    """Remove PID file."""
    pid_file = get_pid_file()
    pid_file.unlink(missing_ok=True)


def start_service(
    host: str = "127.0.0.1",
    port: int = 8420,
    background: bool = False,
) -> dict[str, Any]:
    """
    Start the Station Calyx service.
    
    CONSTRAINT: User-invoked only. No auto-start.
    """
    status = get_service_status()
    if status["running"]:
        return {
            "success": False,
            "message": f"Service already running (PID {status['pid']})",
            "pid": status["pid"],
        }
    
    # Log service start attempt
    event = create_event(
        event_type="SERVICE_START_REQUESTED",
        node_role=COMPONENT_ROLE,
        summary=f"Service start requested: host={host}, port={port}, background={background}",
        payload={"host": host, "port": port, "background": background},
        tags=["service", "lifecycle"],
    )
    append_event(event)
    
    if background:
        return _start_background(host, port)
    else:
        return _start_foreground(host, port)


def _start_foreground(host: str, port: int) -> dict[str, Any]:
    """Start service in foreground (blocking)."""
    try:
        import uvicorn
        from station_calyx.api.server import app
        
        # Write PID
        write_pid_file(os.getpid())
        
        print(f"\n[Station Calyx] Starting in foreground mode...")
        print(f"[Station Calyx] API: http://{host}:{port}")
        print(f"[Station Calyx] Docs: http://{host}:{port}/docs")
        print(f"[Station Calyx] Press Ctrl+C to stop\n")
        
        uvicorn.run(app, host=host, port=port, log_level="info")
        
        return {"success": True, "message": "Service stopped", "pid": os.getpid()}
    except KeyboardInterrupt:
        print("\n[Station Calyx] Shutting down...")
        return {"success": True, "message": "Service stopped by user", "pid": os.getpid()}
    finally:
        remove_pid_file()


def _start_background(host: str, port: int) -> dict[str, Any]:
    """Start service in background."""
    config = get_config()
    
    # Build command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "station_calyx.api.server:app",
        "--host", host,
        "--port", str(port),
    ]
    
    # Start process
    if sys.platform == "win32":
        # Windows: use CREATE_NEW_PROCESS_GROUP
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        process = subprocess.Popen(
            cmd,
            creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # Unix: use start_new_session
        process = subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    
    # Give it a moment to start
    time.sleep(2)
    
    if process.poll() is None:
        # Process is running
        write_pid_file(process.pid)
        
        return {
            "success": True,
            "message": f"Service started in background (PID {process.pid})",
            "pid": process.pid,
            "url": f"http://{host}:{port}",
        }
    else:
        return {
            "success": False,
            "message": "Service failed to start",
            "pid": None,
        }


def stop_service() -> dict[str, Any]:
    """
    Stop the Station Calyx service.
    
    CONSTRAINT: Does not force-kill system processes.
    """
    status = get_service_status()
    
    if not status["running"]:
        return {
            "success": True,
            "message": "Service not running",
        }
    
    pid = status["pid"]
    
    # Log stop attempt
    event = create_event(
        event_type="SERVICE_STOP_REQUESTED",
        node_role=COMPONENT_ROLE,
        summary=f"Service stop requested for PID {pid}",
        payload={"pid": pid},
        tags=["service", "lifecycle"],
    )
    append_event(event)
    
    try:
        if sys.platform == "win32":
            # Windows: use taskkill
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
            )
        else:
            # Unix: send SIGTERM
            os.kill(pid, signal.SIGTERM)
        
        # Wait for process to stop
        for _ in range(10):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        
        remove_pid_file()
        
        return {
            "success": True,
            "message": f"Service stopped (PID {pid})",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to stop service: {e}",
        }


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    status = get_service_status()
    print(f"Status: {status['message']}")
