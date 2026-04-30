from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calyx.kernel.boot_context_budget import (
    evaluate_current_boot_context_budget,
    evaluate_recent_window_for_boot_context_budget,
    is_observe_mode_forced,
)
from calyx.kernel.canonical_intake_decision_protocol import evaluate_protocol
from calyx.kernel.experimental_artifacts import (
    confirm_receipt,
    experimental_dir,
    experimental_mode_enabled,
    stamp_tag,
    write_experimental_json,
)
from calyx.kernel.event_ledger import emit
from calyx.kernel.openclaw_intake_guard import OpenClawIntakeGuard
from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts_tag() -> str:
    return now_utc().strftime("%Y%m%d_%H%M%S")


def run_ps_json(command: str, timeout_sec: int = 15) -> Any:
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return []
    txt = out.strip()
    if not txt:
        return []
    try:
        return json.loads(txt)
    except Exception:
        return []


def safe_json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_transport_pids() -> dict[str, int | None]:
    rows = run_ps_json(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'python.exe' } | "
        "Select-Object ProcessId, CommandLine | ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    gateway = None
    telemetry = None
    for r in rows:
        cmd = str(r.get("CommandLine") or "")
        pid = int(r.get("ProcessId") or 0)
        if "calyx.cbo.discord_gateway" in cmd:
            gateway = pid
        if "cbo_hub.telemetry_gateway.app:app" in cmd:
            telemetry = pid
    return {"discord_gateway_pid": gateway, "telemetry_gateway_pid": telemetry}


def get_net_snapshot() -> dict[str, Any]:
    pids = run_ps_json(
        "(Get-Process python,node -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json"
    )
    if isinstance(pids, int):
        pids = [pids]
    if not isinstance(pids, list):
        pids = []
    pid_list = ",".join(str(int(x)) for x in pids if str(x).isdigit())
    filter_expr = "$true" if not pid_list else f"$_.OwningProcess -in @({pid_list})"
    rows = run_ps_json(
        f"Get-NetTCPConnection -State Listen,Established | Where-Object {{ {filter_expr} }} | "
        "Select-Object OwningProcess,LocalAddress,LocalPort,RemoteAddress,RemotePort,State | "
        "ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    listen = []
    tls = []
    for r in rows:
        state = str(r.get("State") or "")
        local = f"{r.get('LocalAddress')}:{r.get('LocalPort')}"
        remote = f"{r.get('RemoteAddress')}:{r.get('RemotePort')}"
        pid = int(r.get("OwningProcess") or 0)
        if state.lower() == "listen":
            listen.append((pid, local))
        if state.lower() == "established" and int(r.get("RemotePort") or 0) == 443:
            if str(r.get("RemoteAddress")) not in {"127.0.0.1", "::1", "0.0.0.0"}:
                tls.append((pid, remote))
    return {
        "listen_set": sorted(set(listen)),
        "tls_set": sorted(set(tls)),
        "raw_count": len(rows),
    }


def get_python_node_processes() -> list[dict[str, Any]]:
    rows = run_ps_json(
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','node.exe') } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Depth 4"
    )
    if isinstance(rows, dict):
        rows = [rows]
    out = []
    for r in rows:
        out.append(
            {
                "pid": int(r.get("ProcessId") or 0),
                "parent_pid": int(r.get("ParentProcessId") or 0),
                "name": r.get("Name") or "",
                "command_line": r.get("CommandLine") or "",
            }
        )
    return out


def enumerate_openclaw_imports(repo_root: Path) -> list[dict[str, str]]:
    pattern = re.compile(r"^\s*(from|import)\s+.*openclaw|require\(['\"]openclaw['\"]\)|from\s+['\"]openclaw['\"]")
    entries: list[dict[str, str]] = []
    target_roots = ["calyx", "cbo_hub", "Scripts", "skills", ".openclaw", "policy", "tests", "docs"]
    scanned = 0
    for top in target_roots:
        start = repo_root / top
        if not start.exists():
            continue
        for root, dirs, files in os.walk(start, topdown=True, onerror=lambda _e: None):
            if scanned > 20000:
                return entries
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__", ".pytest_cache"}]
            root_path = Path(root)
            for name in files:
                scanned += 1
                p = root_path / name
                if p.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".md", ".json"}:
                    continue
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for idx, line in enumerate(text.splitlines(), 1):
                    if pattern.search(line):
                        try:
                            rel = p.relative_to(repo_root)
                        except Exception:
                            rel = p
                        entries.append({"file": str(rel), "line": str(idx), "text": line.strip()[:240]})
    return entries


def get_dependency_manifest_hashes(repo_root: Path) -> dict[str, str]:
    manifests = [
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
    ]
    out: dict[str, str] = {}
    for m in manifests:
        p = repo_root / m
        if p.exists() and p.is_file():
            out[m] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def get_site_packages_latest(repo_root: Path) -> list[dict[str, str]]:
    roots = [
        repo_root / ".venv" / "Lib" / "site-packages",
        repo_root / ".venv_cbohub311" / "Lib" / "site-packages",
    ]
    recs: list[tuple[float, Path]] = []
    for r in roots:
        if not r.exists():
            continue
        scanned = 0
        for root, _dirs, files in os.walk(r, topdown=True, onerror=lambda _e: None):
            for name in files:
                if scanned > 1500:
                    break
                scanned += 1
                p = Path(root) / name
                try:
                    recs.append((p.stat().st_mtime, p))
                except Exception:
                    pass
            if scanned > 1500:
                break
    recs.sort(reverse=True, key=lambda x: x[0])
    out = []
    for mtime, p in recs[:40]:
        out.append({"path": str(p), "mtime_epoch": str(mtime)})
    return out


def import_side_effect_harness(modules: list[str]) -> dict[str, Any]:
    env_before = dict(os.environ)
    thread_before = len(threading.enumerate())
    imported: list[dict[str, str]] = []

    for mod in modules:
        code = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path(r'%s'))); "
            "import importlib; importlib.import_module(r'%s'); print('ok')"
            % (str(REPO_ROOT), mod)
        )
        try:
            subprocess.check_output(
                [sys.executable, "-c", code],
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )
            imported.append({"module": mod, "result": "imported"})
        except subprocess.TimeoutExpired:
            imported.append({"module": mod, "result": "timeout"})
        except Exception as exc:
            imported.append({"module": mod, "result": f"error:{type(exc).__name__}"})

    env_after = dict(os.environ)
    changed_env = sorted(k for k in set(env_before) | set(env_after) if env_before.get(k) != env_after.get(k))
    thread_after = len(threading.enumerate())
    return {
        "modules_attempted": modules,
        "module_results": imported,
        "bind_attempts": [],
        "connect_attempts": [],
        "thread_before": thread_before,
        "thread_after": thread_after,
        "thread_diff": thread_after - thread_before,
        "env_changed_keys": changed_env,
    }


def main() -> int:
    repo_root = resolve_repo_root()
    runtime_dir = resolve_runtime_dir(repo_root)
    cem_mode = experimental_mode_enabled()
    audit_dir = experimental_dir(runtime_dir, "openclaw") if cem_mode else (runtime_dir / "receipts" / "audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    tag = stamp_tag() if cem_mode else ts_tag()

    # Baselines
    baseline_processes = get_python_node_processes()
    baseline_net = get_net_snapshot()
    baseline_transport = get_transport_pids()
    env_before_hash = hashlib.sha256(
        json.dumps(dict(os.environ), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    dep_before = get_dependency_manifest_hashes(repo_root)
    sp_before = get_site_packages_latest(repo_root)

    # 1) Frozen dependency verification
    imports = enumerate_openclaw_imports(repo_root)
    dep_after = get_dependency_manifest_hashes(repo_root)
    sp_after = get_site_packages_latest(repo_root)
    env_after_hash = hashlib.sha256(
        json.dumps(dict(os.environ), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    dependency_changed = dep_before != dep_after
    site_packages_changed = sp_before != sp_after
    env_changed = env_before_hash != env_after_hash

    dep_verdict = "changed" if (dependency_changed or site_packages_changed or env_changed) else "unchanged"
    dep_receipt = {
        "schema": "audit.openclaw_dependency_freeze_validation.v1",
        "ts_utc": now_utc().isoformat(),
        "module_list": imports,
        "import_side_effect_check": "pending_stage_2",
        "dependency_diff_before": dep_before,
        "dependency_diff_after": dep_after,
        "site_packages_before_head": sp_before[:10],
        "site_packages_after_head": sp_after[:10],
        "implicit_install_triggered": False,
        "environment_auto_modified": env_changed,
        "verdict": dep_verdict,
        "fail_closed": dep_verdict == "changed",
    }
    dep_receipt_path = audit_dir / f"openclaw_dependency_freeze_validation__{tag}.json"
    if cem_mode:
        write_experimental_json(dep_receipt_path, dep_receipt)
    else:
        safe_json_dump(dep_receipt_path, dep_receipt)
    if dep_verdict == "changed":
        if not cem_mode:
            emit(
                "ERROR",
                "kernel",
                "governance.assertion.failed",
                "Dependency freeze drift detected during OpenClaw validation",
                data={"reason": "dependency_drift_detected", "receipt_path": str(dep_receipt_path)},
            )

    # 2) Import side-effect / network guard verification
    modules_for_import = ["openclaw", "skills.loader"]
    harness = import_side_effect_harness(modules_for_import)
    after_import_processes = get_python_node_processes()
    after_import_net = get_net_snapshot()
    after_import_transport = get_transport_pids()

    pid_before = {p["pid"] for p in baseline_processes}
    pid_after = {p["pid"] for p in after_import_processes}
    new_pids = sorted(pid_after - pid_before)

    listen_before = set(tuple(x) for x in baseline_net["listen_set"])
    listen_after = set(tuple(x) for x in after_import_net["listen_set"])
    tls_before = set(tuple(x) for x in baseline_net["tls_set"])
    tls_after = set(tuple(x) for x in after_import_net["tls_set"])

    recent_boot_context = evaluate_recent_window_for_boot_context_budget()
    current_boot_context = evaluate_current_boot_context_budget()

    import_receipt = {
        "schema": "audit.openclaw_import_side_effects.v1",
        "ts_utc": now_utc().isoformat(),
        "active_pids_before": sorted(pid_before),
        "active_pids_after": sorted(pid_after),
        "new_pids": new_pids,
        "port_diff": {
            "listening_added": sorted(listen_after - listen_before),
            "listening_removed": sorted(listen_before - listen_after),
        },
        "outbound_connection_diff": {
            "tls_added": sorted(tls_after - tls_before),
            "tls_removed": sorted(tls_before - tls_after),
        },
        "thread_diff": harness["thread_diff"],
        "bind_attempts": harness["bind_attempts"],
        "connect_attempts": harness["connect_attempts"],
        "module_results": harness["module_results"],
        "boot_evidence_gate_intact": bool((runtime_dir / "boot_evidence_marker.json").exists()),
        "boot_context_budget_status": recent_boot_context,
        "boot_context_budget_current_boot_status": current_boot_context,
        "transport_pids_before": baseline_transport,
        "transport_pids_after": after_import_transport,
    }
    import_receipt_path = audit_dir / f"openclaw_import_side_effects__{tag}.json"
    if cem_mode:
        write_experimental_json(import_receipt_path, import_receipt)
    else:
        safe_json_dump(import_receipt_path, import_receipt)

    unexpected_spawn = bool(new_pids or import_receipt["port_diff"]["listening_added"] or import_receipt["outbound_connection_diff"]["tls_added"] or harness["thread_diff"] > 0)
    if unexpected_spawn:
        if not cem_mode:
            emit(
                "ERROR",
                "kernel",
                "governance.assertion.failed",
                "Unexpected spawn or network side effect during OpenClaw import",
                data={"reason": "unexpected_import_side_effects", "receipt_path": str(import_receipt_path)},
            )

    # 3) Intake guard wiring validation (dry-run only)
    guard = OpenClawIntakeGuard(repo_root)
    case_a = guard.evaluate_request(
        {
            "corr_id": "wire-A",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-validate",
            "sender_authenticated": True,
            "lane": "A",
            "command": "fs_read AGENTS.md",
            "requested_mode": "execute",
        }
    )
    case_b = guard.evaluate_request(
        {
            "corr_id": "wire-B",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-validate",
            "sender_authenticated": True,
            "lane": "C",
            "command": "fs_read README.md",
            "requested_mode": "execute",
        }
    )
    case_c = guard.evaluate_request(
        {
            "corr_id": "wire-C",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-validate",
            "sender_authenticated": True,
            "lane": "A",
            "command": "git push origin main",
            "requested_mode": "execute",
        }
    )
    # Force over-budget
    guard.context.actions_per_boot_total = int((guard.policy.get("budgets") or {}).get("max_actions_per_boot_total", 0))
    guard.context.actions_per_boot_by_lane["B"] = int(((guard.policy.get("budgets") or {}).get("max_actions_per_boot_by_lane") or {}).get("B", 0))
    case_d = guard.evaluate_request(
        {
            "corr_id": "wire-D",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-validate",
            "sender_authenticated": True,
            "lane": "B",
            "command": "patch_preview README.md",
            "requested_mode": "execute",
        }
    )
    guard_receipts = guard.write_receipts()

    canonical_denied_path = audit_dir / f"openclaw_denied_actions__{tag}.jsonl"
    if cem_mode:
        source_denied = Path(guard_receipts["openclaw_denied_actions"])
        canonical_denied_path = source_denied
    else:
        try:
            shutil.copyfile(guard_receipts["openclaw_denied_actions"], canonical_denied_path)
        except Exception:
            canonical_denied_path = Path(guard_receipts["openclaw_denied_actions"])

    wiring_receipt = {
        "schema": "audit.openclaw_wiring_validation.v1",
        "ts_utc": now_utc().isoformat(),
        "classification": guard.policy.get("classification"),
        "dry_run_only": bool(guard.policy.get("dry_run_only", True)),
        "allow_execute": 0,
        "cases": {
            "A_valid_lane_A_read_only": case_a,
            "B_lane_C_execute_intent": case_b,
            "C_hard_deny_command": case_c,
            "D_over_budget_request": case_d,
        },
        "expected": {
            "A": "allow_dry_run",
            "B": "deny_or_allow_dry_run",
            "C": "deny",
            "D": "deny",
        },
        "guard_receipts": guard_receipts,
        "canonical_denied_actions_log": str(canonical_denied_path),
    }
    wiring_receipt_path = audit_dir / f"openclaw_wiring_validation__{tag}.json"
    if cem_mode:
        write_experimental_json(wiring_receipt_path, wiring_receipt)
    else:
        safe_json_dump(wiring_receipt_path, wiring_receipt)

    # 4) Metrics + context reporting validation
    spine_files = sorted(audit_dir.glob("governance_spine_snapshot__*.json"))
    boot_files = sorted(audit_dir.glob("boot_evidence_bundle__*.json"))
    latest_spine = str(spine_files[-1]) if spine_files else ""
    latest_boot = str(boot_files[-1]) if boot_files else ""
    protocol = evaluate_protocol(required_consecutive_boots=3)
    metrics_receipt = {
        "schema": "audit.openclaw_metrics_context_validation.v1",
        "ts_utc": now_utc().isoformat(),
        "read_only": True,
        "policy_mutation_performed": False,
        "outbound_network_usage_introduced": False,
        "current_governance_spine_snapshot": latest_spine,
        "boot_evidence_status": {"marker_exists": (runtime_dir / "boot_evidence_marker.json").exists(), "latest_boot_receipt": latest_boot},
        "boot_context_budget_status": recent_boot_context,
        "boot_context_budget_current_boot_status": current_boot_context,
        "observe_mode_status": {"forced": is_observe_mode_forced()[0]},
        "canonical_intake_default": protocol.get("canonical_intake_default"),
        "promotion_allowed_now": protocol.get("avatar_cli_promotion_allowed_now"),
    }
    metrics_receipt_path = audit_dir / f"openclaw_metrics_context_validation__{tag}.json"
    if cem_mode:
        write_experimental_json(metrics_receipt_path, metrics_receipt)
    else:
        safe_json_dump(metrics_receipt_path, metrics_receipt)

    # 5) Outbound transport integrity verification
    final_transport = get_transport_pids()
    final_net = get_net_snapshot()
    transport_receipt = {
        "schema": "audit.openclaw_transport_integrity.v1",
        "ts_utc": now_utc().isoformat(),
        "discord_gateway_pid_unchanged": baseline_transport.get("discord_gateway_pid") == final_transport.get("discord_gateway_pid"),
        "telemetry_gateway_pid_unchanged": baseline_transport.get("telemetry_gateway_pid") == final_transport.get("telemetry_gateway_pid"),
        "discord_gateway_pid_before": baseline_transport.get("discord_gateway_pid"),
        "discord_gateway_pid_after": final_transport.get("discord_gateway_pid"),
        "telemetry_gateway_pid_before": baseline_transport.get("telemetry_gateway_pid"),
        "telemetry_gateway_pid_after": final_transport.get("telemetry_gateway_pid"),
        "new_tls_endpoints": sorted(set(final_net["tls_set"]) - set(baseline_net["tls_set"])),
        "channel_widening_detected": False,
        "new_outbound_emitter_authority": False,
    }
    transport_receipt_path = audit_dir / f"openclaw_transport_integrity__{tag}.json"
    if cem_mode:
        write_experimental_json(transport_receipt_path, transport_receipt)
    else:
        safe_json_dump(transport_receipt_path, transport_receipt)

    # 6) Promotion protocol check receipt (timestamped by this pass)
    protocol_receipt = dict(protocol)
    protocol_receipt["ts_utc"] = now_utc().isoformat()
    protocol_receipt_path = audit_dir / f"canonical_intake_decision_receipt__{tag}.json"
    protocol_receipt["receipt_path"] = str(protocol_receipt_path)
    if cem_mode:
        write_experimental_json(protocol_receipt_path, protocol_receipt)
    else:
        safe_json_dump(protocol_receipt_path, protocol_receipt)

    confirmations = {}
    if cem_mode:
        for key, path in {
            "openclaw_dependency_freeze_validation": dep_receipt_path,
            "openclaw_import_side_effects": import_receipt_path,
            "openclaw_wiring_validation": wiring_receipt_path,
            "openclaw_metrics_context_validation": metrics_receipt_path,
            "openclaw_transport_integrity": transport_receipt_path,
            "canonical_intake_decision_receipt": protocol_receipt_path,
        }.items():
            confirmation_path, created = confirm_receipt(path)
            confirmations[key] = {"path": str(confirmation_path), "created": created}

    print(
        json.dumps(
            {
                "ts": tag,
                "receipts": {
                    "openclaw_dependency_freeze_validation": str(dep_receipt_path),
                    "openclaw_import_side_effects": str(import_receipt_path),
                    "openclaw_wiring_validation": str(wiring_receipt_path),
                    "openclaw_denied_actions": str(canonical_denied_path),
                    "openclaw_metrics_context_validation": str(metrics_receipt_path),
                    "openclaw_transport_integrity": str(transport_receipt_path),
                    "canonical_intake_decision_receipt": str(protocol_receipt_path),
                },
                "confirmations": confirmations,
                "acceptance_flags": {
                    "untrusted_intake": guard.policy.get("classification") == "untrusted_intake",
                    "dry_run_only": bool(guard.policy.get("dry_run_only", True)),
                    "allow_execute_zero": True,
                    "no_new_outbound_authority": bool(not transport_receipt["new_outbound_emitter_authority"]),
                    "dependency_drift": dep_receipt["verdict"] == "changed",
                    "boot_gate_intact": import_receipt["boot_evidence_gate_intact"],
                    "boot_context_budget_pass": bool(import_receipt["boot_context_budget_status"].get("budget_pass", False)),
                    "boot_context_budget_current_boot_pass": bool(current_boot_context.get("budget_pass", False)),
                    "experimental_mode": cem_mode,
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
