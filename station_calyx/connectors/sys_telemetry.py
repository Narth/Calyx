"""
Station Calyx System Telemetry Connector
========================================

Read-only system snapshot collection.

INVARIANT: NO MODIFICATIONS
- This connector only READS system state
- No commands executed
- No files modified

Role: connectors/sys_telemetry
Scope: Read-only system metrics collection
"""

from __future__ import annotations

import platform
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Role declaration
COMPONENT_ROLE = "sys_telemetry"
COMPONENT_SCOPE = "read-only system metrics collection"

# Try to import psutil (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


def get_hostname() -> str:
    """Get system hostname."""
    return socket.gethostname()


def get_platform_info() -> dict[str, str]:
    """Get platform information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def get_uptime() -> Optional[float]:
    """Get system uptime in seconds (requires psutil)."""
    if PSUTIL_AVAILABLE and psutil:
        try:
            boot_time = psutil.boot_time()
            return datetime.now().timestamp() - boot_time
        except Exception:
            pass
    return None


def get_cpu_percent() -> Optional[float]:
    """Get CPU usage percentage (requires psutil)."""
    if PSUTIL_AVAILABLE and psutil:
        try:
            return psutil.cpu_percent(interval=0.5)
        except Exception:
            pass
    return None


def get_memory_info() -> dict[str, Any]:
    """Get memory information."""
    if PSUTIL_AVAILABLE and psutil:
        try:
            mem = psutil.virtual_memory()
            return {
                "total_bytes": mem.total,
                "available_bytes": mem.available,
                "used_bytes": mem.used,
                "percent": mem.percent,
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
            }
        except Exception:
            pass
    return {"available": False}


def get_disk_usage(path: str = "/") -> dict[str, Any]:
    """Get disk usage information."""
    try:
        # Use shutil (stdlib) as fallback
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round((usage.used / usage.total) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def get_top_processes(n: int = 5) -> list[dict[str, Any]]:
    """Get top N processes by memory usage (requires psutil)."""
    if not PSUTIL_AVAILABLE or not psutil:
        return []
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info['memory_percent'] is not None:
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": round(info['cpu_percent'] or 0, 1),
                        "memory_percent": round(info['memory_percent'] or 0, 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        return processes[:n]
    except Exception:
        return []


def get_network_interfaces() -> list[dict[str, Any]]:
    """Get network interface summary (requires psutil)."""
    if not PSUTIL_AVAILABLE or not psutil:
        return []
    
    try:
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        for iface_name, iface_addrs in addrs.items():
            iface_info = {
                "name": iface_name,
                "addresses": [],
                "is_up": stats.get(iface_name, {}).isup if iface_name in stats else None,
            }
            for addr in iface_addrs:
                if addr.family.name in ('AF_INET', 'AF_INET6'):
                    iface_info["addresses"].append({
                        "family": addr.family.name,
                        "address": addr.address,
                    })
            if iface_info["addresses"]:
                interfaces.append(iface_info)
        
        return interfaces[:10]  # Limit to 10 interfaces
    except Exception:
        return []


def collect_snapshot() -> dict[str, Any]:
    """
    Collect a complete system snapshot (READ-ONLY).
    
    Returns a dictionary with:
    - hostname
    - platform info
    - uptime (if available)
    - cpu_percent (if available)
    - memory info (if available)
    - disk_usage
    - top_processes (if available)
    - network_interfaces (if available)
    """
    now = datetime.now(timezone.utc)
    
    # Determine primary disk path
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    
    snapshot = {
        "timestamp": now.isoformat(),
        "hostname": get_hostname(),
        "platform": get_platform_info(),
        "uptime_seconds": get_uptime(),
        "cpu_percent": get_cpu_percent(),
        "memory": get_memory_info(),
        "disk": get_disk_usage(disk_path),
        "top_processes": get_top_processes(5),
        "network_interfaces": get_network_interfaces(),
        "psutil_available": PSUTIL_AVAILABLE,
        "collector_role": COMPONENT_ROLE,
    }
    
    return snapshot


def format_snapshot_summary(snapshot: dict[str, Any]) -> str:
    """Format snapshot as human-readable summary."""
    lines = [
        f"=== System Snapshot @ {snapshot['timestamp']} ===",
        f"Hostname: {snapshot['hostname']}",
        f"Platform: {snapshot['platform']['system']} {snapshot['platform']['release']}",
    ]
    
    if snapshot.get('uptime_seconds'):
        hours = int(snapshot['uptime_seconds'] // 3600)
        lines.append(f"Uptime: {hours}h")
    
    if snapshot.get('cpu_percent') is not None:
        lines.append(f"CPU: {snapshot['cpu_percent']}%")
    
    mem = snapshot.get('memory', {})
    if mem.get('percent'):
        lines.append(f"Memory: {mem['percent']}% ({mem.get('used_gb', '?')}GB / {mem.get('total_gb', '?')}GB)")
    
    disk = snapshot.get('disk', {})
    if disk.get('percent_used'):
        lines.append(f"Disk: {disk['percent_used']}% ({disk.get('used_gb', '?')}GB / {disk.get('total_gb', '?')}GB)")
    
    procs = snapshot.get('top_processes', [])
    if procs:
        lines.append(f"Top Processes: {', '.join(p['name'] for p in procs[:3])}")
    
    return "\n".join(lines)


# Self-test
if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print(f"psutil available: {PSUTIL_AVAILABLE}")
    print()
    
    snapshot = collect_snapshot()
    print(format_snapshot_summary(snapshot))
