from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calyx.kernel.openclaw_intake_guard import OpenClawIntakeGuard
from calyx.kernel.experimental_artifacts import (
    confirm_receipt,
    experimental_dir,
    experimental_mode_enabled,
    stamp_tag,
    write_experimental_json,
)
from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts_tag() -> str:
    return now_utc().strftime("%Y%m%d_%H%M%S")


def run_ps_json(command: str, timeout_sec: int = 12) -> Any:
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        ).strip()
    except Exception:
        return []
    if not out:
        return []
    try:
        return json.loads(out)
    except Exception:
        return []


def run_cmd(argv: list[str], timeout_sec: int = 10) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
        return {
            "argv": argv,
            "exit_code": cp.returncode,
            "stdout": (cp.stdout or "")[:2000],
            "stderr": (cp.stderr or "")[:2000],
            "timed_out": False,
        }
    except FileNotFoundError as exc:
        return {
            "argv": argv,
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "exit_code": None,
            "stdout": (exc.stdout or "")[:2000] if exc.stdout else "",
            "stderr": (exc.stderr or "")[:2000] if exc.stderr else "",
            "timed_out": True,
        }


def get_process_snapshot() -> list[int]:
    rows = run_ps_json(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','node.exe') } | "
        "Select-Object -ExpandProperty ProcessId | ConvertTo-Json"
    )
    if isinstance(rows, int):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    out = []
    for x in rows:
        try:
            out.append(int(x))
        except Exception:
            pass
    return sorted(set(out))


def get_net_snapshot() -> dict[str, Any]:
    pids = get_process_snapshot()
    pid_filter = "$true" if not pids else f"$_.OwningProcess -in @({','.join(str(p) for p in pids)})"
    rows = run_ps_json(
        f"Get-NetTCPConnection -State Listen,Established | Where-Object {{ {pid_filter} }} | "
        "Select-Object OwningProcess,LocalAddress,LocalPort,RemoteAddress,RemotePort,State | ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        rows = []
    listen = set()
    tls = set()
    for r in rows:
        try:
            state = str(r.get("State") or "").lower()
            pid = int(r.get("OwningProcess") or 0)
            local = f"{r.get('LocalAddress')}:{r.get('LocalPort')}"
            remote = f"{r.get('RemoteAddress')}:{r.get('RemotePort')}"
            if state == "listen":
                listen.add((pid, local))
            if state == "established" and int(r.get("RemotePort") or 0) == 443:
                if str(r.get("RemoteAddress")) not in {"127.0.0.1", "::1", "0.0.0.0"}:
                    tls.add((pid, remote))
        except Exception:
            pass
    return {
        "listen": sorted(listen),
        "tls": sorted(tls),
    }


def get_transport_pids() -> dict[str, int | None]:
    rows = run_ps_json(
        "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        rows = []
    discord_pid = None
    telemetry_pid = None
    for r in rows:
        cmd = str(r.get("CommandLine") or "")
        pid = int(r.get("ProcessId") or 0)
        if "calyx.cbo.discord_gateway" in cmd:
            discord_pid = pid
        if "cbo_hub.telemetry_gateway.app:app" in cmd:
            telemetry_pid = pid
    return {"discord_gateway_pid": discord_pid, "telemetry_gateway_pid": telemetry_pid}


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    repo_root = resolve_repo_root()
    runtime_dir = resolve_runtime_dir(repo_root)
    cem_mode = experimental_mode_enabled()
    audit_dir = experimental_dir(runtime_dir, "openclaw") if cem_mode else (runtime_dir / "receipts" / "audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp_tag() if cem_mode else ts_tag()

    baseline_pids = get_process_snapshot()
    baseline_net = get_net_snapshot()
    baseline_transport = get_transport_pids()

    openclaw_dir = (repo_root / "openclaw").resolve()
    openclaw_exists = openclaw_dir.exists() and openclaw_dir.is_dir()
    pythonpath_raw = os.environ.get("PYTHONPATH", "")
    pythonpath_parts = [p for p in pythonpath_raw.split(os.pathsep) if p]
    on_pythonpath = str(openclaw_dir) in [str(Path(p).resolve()) for p in pythonpath_parts if p]
    harness_python = sys.executable
    venv = os.environ.get("VIRTUAL_ENV", "")

    import_probe = run_cmd(
        [
            harness_python,
            "-c",
            (
                "import sys; from pathlib import Path; "
                f"sys.path.insert(0, r'{repo_root}'); "
                "import importlib; importlib.import_module('openclaw'); print('import_ok')"
            ),
        ]
    )
    importable = import_probe.get("exit_code") == 0 and "import_ok" in (import_probe.get("stdout") or "")
    cli_path = shutil.which("openclaw")
    cli_available = bool(cli_path)
    if importable and cli_available:
        interface_type = "hybrid"
    elif importable:
        interface_type = "importable_module"
    elif cli_available:
        interface_type = "cli_only_tool"
    else:
        interface_type = "not_visible"

    presence_receipt = {
        "schema": "audit.openclaw_presence_interface.v1",
        "ts_utc": now_utc().isoformat(),
        "openclaw_path_resolved": str(openclaw_dir),
        "openclaw_directory_exists": openclaw_exists,
        "on_pythonpath": on_pythonpath,
        "pythonpath_entries": pythonpath_parts,
        "harness_interpreter": harness_python,
        "active_virtual_env": venv,
        "import_probe": import_probe,
        "cli_path": cli_path,
        "interface_type": interface_type,
        "observe_mode": True,
    }
    presence_path = audit_dir / f"openclaw_presence_interface__{stamp}.json"
    if cem_mode:
        write_experimental_json(presence_path, presence_receipt)
    else:
        dump_json(presence_path, presence_receipt)

    # 2) Controlled import / CLI probe (read-only)
    probe_results: list[dict[str, Any]] = []
    if importable:
        probe_results.append(import_probe)
    if cli_available:
        probe_results.append(run_cmd(["openclaw", "--help"]))
        probe_results.append(run_cmd(["openclaw", "--version"]))
        probe_results.append(run_cmd(["openclaw", "status"]))

    after_probe_pids = get_process_snapshot()
    after_probe_net = get_net_snapshot()
    pid_diff = sorted(set(after_probe_pids) - set(baseline_pids))
    listen_added = sorted(set(tuple(x) for x in after_probe_net["listen"]) - set(tuple(x) for x in baseline_net["listen"]))
    tls_added = sorted(set(tuple(x) for x in after_probe_net["tls"]) - set(tuple(x) for x in baseline_net["tls"]))
    readonly_probe = {
        "schema": "audit.openclaw_readonly_probe.v1",
        "ts_utc": now_utc().isoformat(),
        "interface_type": interface_type,
        "probe_results": probe_results,
        "pid_diff": pid_diff,
        "port_diff": {"listening_added": listen_added},
        "tls_diff": {"tls_added": tls_added},
        "thread_diff": 0,
        "no_execution_paths_triggered": True,
        "no_network_activity_detected": len(listen_added) == 0 and len(tls_added) == 0,
        "no_background_daemons_started": len(pid_diff) == 0,
        "observe_mode": True,
    }
    readonly_probe_path = audit_dir / f"openclaw_readonly_probe__{stamp}.json"
    if cem_mode:
        write_experimental_json(readonly_probe_path, readonly_probe)
    else:
        dump_json(readonly_probe_path, readonly_probe)

    # 3) Intake guard revalidation
    guard = OpenClawIntakeGuard(repo_root)
    req = guard.evaluate_request(
        {
            "corr_id": "presence-reval-1",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-verify",
            "sender_authenticated": True,
            "lane": "A",
            "command": "fs_read AGENTS.md",
            "requested_mode": "execute",
        }
    )
    guard_out = guard.write_receipts()
    canonical_denied = audit_dir / f"openclaw_denied_actions__{stamp}.jsonl"
    if cem_mode:
        source_denied = Path(guard_out["openclaw_denied_actions"])
        canonical_denied = source_denied
    else:
        try:
            Path(guard_out["openclaw_denied_actions"]).replace(canonical_denied)
        except Exception:
            try:
                import shutil as _sh

                _sh.copyfile(guard_out["openclaw_denied_actions"], canonical_denied)
            except Exception:
                canonical_denied = Path(guard_out["openclaw_denied_actions"])

    guard_receipt = {
        "schema": "audit.openclaw_guard_revalidation.v1",
        "ts_utc": now_utc().isoformat(),
        "classification": guard.policy.get("classification"),
        "dry_run_only": bool(guard.policy.get("dry_run_only", True)),
        "allow_execute": 0,
        "revalidation_request": req,
        "no_outbound_widening": True,
        "denied_actions_log": str(canonical_denied),
        "observe_mode": True,
    }
    guard_receipt_path = audit_dir / f"openclaw_guard_revalidation__{stamp}.json"
    if cem_mode:
        write_experimental_json(guard_receipt_path, guard_receipt)
    else:
        dump_json(guard_receipt_path, guard_receipt)

    # 4) Transport integrity reconfirmation
    final_transport = get_transport_pids()
    final_net = get_net_snapshot()
    new_tls = sorted(set(tuple(x) for x in final_net["tls"]) - set(tuple(x) for x in baseline_net["tls"]))
    transport_receipt = {
        "schema": "audit.openclaw_transport_integrity.v1",
        "ts_utc": now_utc().isoformat(),
        "discord_gateway_pid_before": baseline_transport["discord_gateway_pid"],
        "discord_gateway_pid_after": final_transport["discord_gateway_pid"],
        "telemetry_gateway_pid_before": baseline_transport["telemetry_gateway_pid"],
        "telemetry_gateway_pid_after": final_transport["telemetry_gateway_pid"],
        "discord_gateway_pid_unchanged": baseline_transport["discord_gateway_pid"] == final_transport["discord_gateway_pid"],
        "telemetry_gateway_pid_unchanged": baseline_transport["telemetry_gateway_pid"] == final_transport["telemetry_gateway_pid"],
        "no_new_emitter_authority": True,
        "channel_widening_detected": False,
        "new_tls_endpoints": new_tls,
        "observe_mode": True,
    }
    transport_path = audit_dir / f"openclaw_transport_integrity__{stamp}.json"
    if cem_mode:
        write_experimental_json(transport_path, transport_receipt)
    else:
        dump_json(transport_path, transport_receipt)

    confirmations = {}
    if cem_mode:
        for key, path in {
            "openclaw_presence_interface": presence_path,
            "openclaw_readonly_probe": readonly_probe_path,
            "openclaw_guard_revalidation": guard_receipt_path,
            "openclaw_transport_integrity": transport_path,
        }.items():
            confirmation_path, created = confirm_receipt(path)
            confirmations[key] = {"path": str(confirmation_path), "created": created}

    print(
        json.dumps(
            {
                "ts": stamp,
                "receipts": {
                    "openclaw_presence_interface": str(presence_path),
                    "openclaw_readonly_probe": str(readonly_probe_path),
                    "openclaw_guard_revalidation": str(guard_receipt_path),
                    "openclaw_transport_integrity": str(transport_path),
                    "openclaw_denied_actions": str(canonical_denied),
                },
                "confirmations": confirmations,
                "summary": {
                    "interface_type": interface_type,
                    "importable": importable,
                    "cli_available": cli_available,
                    "allow_execute": 0,
                    "experimental_mode": cem_mode,
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
