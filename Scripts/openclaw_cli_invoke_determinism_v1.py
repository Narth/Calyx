from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(REPO_ROOT))

from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir
from calyx.kernel.experimental_artifacts import (
    confirm_receipt,
    experimental_dir,
    experimental_mode_enabled,
    stamp_tag,
    write_experimental_json,
)


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


def get_process_ids() -> list[int]:
    rows = run_ps_json(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','node.exe') } | "
        "Select-Object -ExpandProperty ProcessId | ConvertTo-Json"
    )
    if isinstance(rows, int):
        rows = [rows]
    if not isinstance(rows, list):
        rows = []
    out: list[int] = []
    for x in rows:
        try:
            out.append(int(x))
        except Exception:
            pass
    return sorted(set(out))


def get_net_snapshot() -> dict[str, list[tuple[int, str]]]:
    pids = get_process_ids()
    pid_filter = "$true" if not pids else f"$_.OwningProcess -in @({','.join(str(p) for p in pids)})"
    rows = run_ps_json(
        f"Get-NetTCPConnection -State Listen,Established | Where-Object {{ {pid_filter} }} | "
        "Select-Object OwningProcess,LocalAddress,LocalPort,RemoteAddress,RemotePort,State | ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        rows = []
    listen: set[tuple[int, str]] = set()
    tls: set[tuple[int, str]] = set()
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
    return {"listen": sorted(listen), "tls": sorted(tls)}


def run_cli_cmd(cli_abs: str, arg: str) -> dict[str, Any]:
    argv = ["cmd.exe", "/d", "/c", cli_abs, arg]
    try:
        cp = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
        return {
            "argv": argv,
            "exit_code": cp.returncode,
            "stdout": (cp.stdout or "")[:4000],
            "stderr": (cp.stderr or "")[:2000],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "exit_code": None,
            "stdout": (exc.stdout or "")[:4000] if exc.stdout else "",
            "stderr": (exc.stderr or "")[:2000] if exc.stderr else "",
            "timed_out": True,
        }


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    repo_root = resolve_repo_root()
    runtime_dir = resolve_runtime_dir(repo_root)
    cem_mode = experimental_mode_enabled()
    audit_dir = experimental_dir(runtime_dir, "openclaw") if cem_mode else (runtime_dir / "receipts" / "audit")
    stamp = stamp_tag() if cem_mode else ts_tag()

    cli_path = shutil.which("openclaw.cmd") or shutil.which("openclaw.CMD") or shutil.which("openclaw")
    cli_abs = str(Path(cli_path).resolve()) if cli_path else ""

    env_receipt = {
        "schema": "audit.openclaw_cli_env_snapshot.v1",
        "ts_utc": now_utc().isoformat(),
        "observe_mode": True,
        "cwd": str(Path.cwd()),
        "repo_root": str(repo_root),
        "harness_interpreter": os.path.abspath(os.sys.executable),
        "openclaw_cli_abs_path": cli_abs,
        "PATH": os.environ.get("PATH", ""),
        "PATHEXT": os.environ.get("PATHEXT", ""),
        "COMSPEC": os.environ.get("COMSPEC", ""),
    }
    env_path = audit_dir / f"openclaw_cli_env_snapshot__{stamp}.json"
    if cem_mode:
        write_experimental_json(env_path, env_receipt)
    else:
        dump_json(env_path, env_receipt)

    pids_before = get_process_ids()
    net_before = get_net_snapshot()
    thread_before = len(threading.enumerate())

    help_result = {"error": "cli_not_found"}
    version_result = {"error": "cli_not_found"}
    if cli_abs:
        help_result = run_cli_cmd(cli_abs, "--help")
        version_result = run_cli_cmd(cli_abs, "--version")

    pids_after = get_process_ids()
    net_after = get_net_snapshot()
    thread_after = len(threading.enumerate())

    probe_receipt = {
        "schema": "audit.openclaw_cli_readonly_probe.v1",
        "ts_utc": now_utc().isoformat(),
        "observe_mode": True,
        "openclaw_cli_abs_path": cli_abs,
        "probes": {
            "help": help_result,
            "version": version_result,
        },
        "pid_diff": sorted(set(pids_after) - set(pids_before)),
        "port_diff": {
            "listening_added": sorted(set(tuple(x) for x in net_after["listen"]) - set(tuple(x) for x in net_before["listen"])),
            "listening_removed": sorted(set(tuple(x) for x in net_before["listen"]) - set(tuple(x) for x in net_after["listen"])),
        },
        "tls_diff": {
            "tls_added": sorted(set(tuple(x) for x in net_after["tls"]) - set(tuple(x) for x in net_before["tls"])),
            "tls_removed": sorted(set(tuple(x) for x in net_before["tls"]) - set(tuple(x) for x in net_after["tls"])),
        },
        "thread_diff": thread_after - thread_before,
        "no_side_effects": (
            len(set(pids_after) - set(pids_before)) == 0
            and len(set(tuple(x) for x in net_after["listen"]) - set(tuple(x) for x in net_before["listen"])) == 0
            and len(set(tuple(x) for x in net_after["tls"]) - set(tuple(x) for x in net_before["tls"])) == 0
            and (thread_after - thread_before) == 0
        ),
        "no_execution_enablement": True,
        "no_promotion": True,
    }
    probe_path = audit_dir / f"openclaw_cli_readonly_probe__{stamp}.json"
    if cem_mode:
        write_experimental_json(probe_path, probe_receipt)
    else:
        dump_json(probe_path, probe_receipt)

    confirmations = {}
    if cem_mode:
        for key, path in {
            "openclaw_cli_env_snapshot": env_path,
            "openclaw_cli_readonly_probe": probe_path,
        }.items():
            confirmation_path, created = confirm_receipt(path)
            confirmations[key] = {"path": str(confirmation_path), "created": created}

    print(
        json.dumps(
            {
                "ts": stamp,
                "receipts": {
                    "openclaw_cli_readonly_probe": str(probe_path),
                    "openclaw_cli_env_snapshot": str(env_path),
                },
                "confirmations": confirmations,
                "summary": {
                    "cli_abs": cli_abs,
                    "help_exit": help_result.get("exit_code"),
                    "version_exit": version_result.get("exit_code"),
                    "no_side_effects": probe_receipt["no_side_effects"],
                    "experimental_mode": cem_mode,
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
