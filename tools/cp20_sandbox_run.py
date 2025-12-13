#!/usr/bin/env python3
"""
CP20 Sandbox Runner - Phase 2
Execute commands in isolated sandbox environment
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASES_DIR = ROOT / "outgoing" / "leases"
STAGING_RUNS_DIR = ROOT / "outgoing" / "staging_runs"


def validate_command(lease: dict, command: str) -> bool:
    """Validate command against lease allowlist"""
    allowed_commands = lease["scope"]["commands_allowlist"]
    return command in allowed_commands


def setup_sandbox_environment(lease: dict):
    """Setup sandbox environment variables"""
    # Minimal environment from lease
    env = {}
    for key in lease["scope"]["env_allowlist"]:
        env[key] = os.environ.get(key, "")
    
    # Minimal PATH
    env["PATH"] = "/usr/bin:/bin"
    
    return env


def enforce_timeout(proc: subprocess.Popen, timeout_s: int):
    """Enforce wallclock timeout"""
    try:
        outs, errs = proc.communicate(timeout=timeout_s)
        exit_code = proc.returncode
        duration = time.time() - proc.__dict__.get('start_time', time.time())
        return outs, errs, exit_code, duration
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        exit_code = -9  # SIGKILL
        duration = timeout_s
        return outs, errs, exit_code, duration


def run_in_sandbox(lease_json: str, command: str):
    """
    Run command in sandbox with lease constraints
    
    Args:
        lease_json: Path to lease JSON file
        command: Command to execute
        
    Returns:
        Exit code
    """
    lease_file = Path(lease_json)
    if not lease_file.exists():
        raise FileNotFoundError(f"Lease file not found: {lease_json}")
    
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    
    # Validate command
    if not validate_command(lease, command):
        raise ValueError(f"Command not in allowlist: {command}")
    
    # Setup environment
    env = setup_sandbox_environment(lease)
    
    # Prepare workdir
    workdir = lease["runner"]["workdir"]
    # In production, create actual sandbox with mounts
    # For now, use local workdir for testing
    workdir_path = Path(workdir.replace("/srv/calyx", str(ROOT)))
    workdir_path.mkdir(parents=True, exist_ok=True)
    
    # Log start
    try:
        from tools.svf_audit import log_intent_activity
        log_intent_activity(lease["lease_id"], "cp20", "exec_event_STARTED", {
            "command": command,
            "lease_id": lease["lease_id"]
        })
    except ImportError:
        pass
    
    # Execute with timeout
    start_time = time.time()
    try:
        proc = subprocess.Popen(
            command.split(),
            cwd=str(workdir_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.start_time = start_time
        
        timeout_s = lease["limits"]["wallclock_timeout_s"]
        outs, errs, exit_code, duration = enforce_timeout(proc, timeout_s)
    except FileNotFoundError:
        # Command not found - still record attempt
        outs = b""
        errs = b"Command not found\n"
        exit_code = 127
        duration = time.time() - start_time
    
    # Persist artifacts
    outdir = STAGING_RUNS_DIR / lease["lease_id"]
    outdir.mkdir(parents=True, exist_ok=True)
    
    (outdir / "stdout.log").write_bytes(outs or b"")
    (outdir / "stderr.log").write_bytes(errs or b"")
    (outdir / "exit_code.txt").write_text(str(exit_code))
    (outdir / "meta.json").write_text(json.dumps({
        "duration_s": duration,
        "command": command,
        "lease_id": lease["lease_id"],
        "intent_id": lease["intent_id"]
    }, indent=2))
    
    # Log finish
    try:
        from tools.svf_audit import log_intent_activity
        event_type = "exec_event_TIMEOUT" if exit_code == -9 else "exec_event_FINISHED"
        log_intent_activity(lease["lease_id"], "cp20", event_type, {
            "command": command,
            "exit_code": exit_code,
            "duration_s": duration
        })
    except ImportError:
        pass
    
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="CP20 Sandbox Runner")
    parser.add_argument("--lease", required=True, help="Path to lease JSON file")
    parser.add_argument("--command", required=True, help="Command to execute")
    
    args = parser.parse_args()
    
    try:
        exit_code = run_in_sandbox(args.lease, args.command)
        print(f"Command executed with exit code: {exit_code}")
        return exit_code
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

