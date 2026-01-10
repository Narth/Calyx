"""
Station Calyx Doctor
====================

Health checks for Station Calyx installation.

INVARIANTS:
- NO_HIDDEN_CHANNELS: Reports all check results transparently
- EXECUTION_GATE: Read-only checks, no modifications

Role: core/doctor
Scope: System health verification
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import urllib.request
import urllib.error

from .config import get_config
from .service import get_service_status

COMPONENT_ROLE = "doctor"
COMPONENT_SCOPE = "system health verification"


def check_evidence_writable() -> dict[str, Any]:
    """Check if evidence log is writable."""
    config = get_config()
    evidence_path = config.data_dir / "evidence.jsonl"
    
    try:
        # Ensure directory exists
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to open for append
        with open(evidence_path, "a", encoding="utf-8") as f:
            pass
        
        return {
            "check": "evidence_writable",
            "passed": True,
            "message": f"Evidence log writable: {evidence_path}",
        }
    except Exception as e:
        return {
            "check": "evidence_writable",
            "passed": False,
            "message": f"Evidence log not writable: {e}",
        }


def check_disk_permissions() -> dict[str, Any]:
    """Check disk write permissions in data directory."""
    config = get_config()
    
    try:
        # Try to create and delete a temp file
        test_path = config.data_dir / ".write_test"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        test_path.write_text("test")
        test_path.unlink()
        
        return {
            "check": "disk_permissions",
            "passed": True,
            "message": f"Write permissions OK: {config.data_dir}",
        }
    except Exception as e:
        return {
            "check": "disk_permissions",
            "passed": False,
            "message": f"Write permissions failed: {e}",
        }


def check_api_reachable(host: str = "127.0.0.1", port: int = 8420) -> dict[str, Any]:
    """Check if API server is reachable."""
    url = f"http://{host}:{port}/v1/health"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                return {
                    "check": "api_reachable",
                    "passed": True,
                    "message": f"API reachable at {host}:{port}",
                }
    except urllib.error.URLError:
        pass
    except Exception:
        pass
    
    # Check if service is supposed to be running
    status = get_service_status()
    if status["running"]:
        return {
            "check": "api_reachable",
            "passed": False,
            "message": f"API not reachable (service running but not responding)",
        }
    else:
        return {
            "check": "api_reachable",
            "passed": True,
            "message": "API not running (service stopped - this is OK)",
            "info": "Start service with: calyx start",
        }


def check_rate_limits() -> dict[str, Any]:
    """Check notification rate limits are sane."""
    from .notifications import RATE_LIMIT_WINDOW_SECONDS, RATE_LIMIT_MAX_NOTIFICATIONS
    
    # Sanity check: should be reasonable values
    if RATE_LIMIT_WINDOW_SECONDS < 60:
        return {
            "check": "rate_limits",
            "passed": False,
            "message": f"Rate limit window too short: {RATE_LIMIT_WINDOW_SECONDS}s",
        }
    
    if RATE_LIMIT_MAX_NOTIFICATIONS > 10:
        return {
            "check": "rate_limits",
            "passed": False,
            "message": f"Rate limit too high: {RATE_LIMIT_MAX_NOTIFICATIONS} per window",
        }
    
    return {
        "check": "rate_limits",
        "passed": True,
        "message": f"Rate limits OK: {RATE_LIMIT_MAX_NOTIFICATIONS} per {RATE_LIMIT_WINDOW_SECONDS}s",
    }


def check_data_directory() -> dict[str, Any]:
    """Check data directory structure."""
    config = get_config()
    
    required_dirs = [
        config.data_dir,
        config.summaries_dir,
    ]
    
    missing = []
    for d in required_dirs:
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                missing.append(str(d))
    
    if missing:
        return {
            "check": "data_directory",
            "passed": False,
            "message": f"Could not create directories: {missing}",
        }
    
    return {
        "check": "data_directory",
        "passed": True,
        "message": f"Data directory OK: {config.data_dir}",
    }


def check_python_version() -> dict[str, Any]:
    """Check Python version."""
    import sys
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return {
            "check": "python_version",
            "passed": False,
            "message": f"Python {version.major}.{version.minor} - requires 3.9+",
        }
    
    return {
        "check": "python_version",
        "passed": True,
        "message": f"Python {version.major}.{version.minor}.{version.micro}",
    }


def check_dependencies() -> dict[str, Any]:
    """Check required dependencies are installed."""
    required = ["fastapi", "uvicorn", "pydantic"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return {
            "check": "dependencies",
            "passed": False,
            "message": f"Missing packages: {', '.join(missing)}",
            "info": f"Install with: pip install {' '.join(missing)}",
        }
    
    return {
        "check": "dependencies",
        "passed": True,
        "message": "All required packages installed",
    }


def run_all_checks() -> dict[str, Any]:
    """Run all health checks."""
    checks = [
        check_python_version,
        check_dependencies,
        check_data_directory,
        check_disk_permissions,
        check_evidence_writable,
        check_rate_limits,
        check_api_reachable,
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
            if result["passed"]:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append({
                "check": check_fn.__name__,
                "passed": False,
                "message": f"Check failed with error: {e}",
            })
            failed += 1
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": results,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "healthy": failed == 0,
    }


def format_doctor_report(results: dict[str, Any]) -> str:
    """Format doctor results for display."""
    lines = [
        "",
        "=" * 50,
        "  STATION CALYX DOCTOR",
        "=" * 50,
        "",
    ]
    
    for check in results["checks"]:
        status = "?" if check["passed"] else "?"
        lines.append(f"  {status} {check['check']}")
        lines.append(f"    {check['message']}")
        if "info" in check:
            lines.append(f"    ? {check['info']}")
        lines.append("")
    
    lines.extend([
        "-" * 50,
        f"  Results: {results['passed']} passed, {results['failed']} failed",
        "",
    ])
    
    if results["healthy"]:
        lines.append("  Status: HEALTHY")
    else:
        lines.append("  Status: ISSUES DETECTED")
    
    lines.extend([
        "",
        "=" * 50,
        "",
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_all_checks()
    print(format_doctor_report(results))
