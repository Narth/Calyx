"""Triage Orchestrator: serial 3-phase checks for safe changes.

Phases (A -> B -> C):
- A (Proposer/Validator): invoke agent_runner with a goal-file, apply+dry-run, to produce a deterministic plan + diffs.
- B (Reviewer): inspect the emitted diffs/audit and verify scope and content constraints. Emits a signed review.json.
- C (Stability): run compile and optional pytest sanity checks.

Default wiring assumes WSL venv at ~/.calyx-venv and this repo at /mnt/c/Calyx_Terminal.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
ORCH_VERSION = "1.1.1"
TRIAGE_HEARTBEAT = OUT / "triage.lock"


def _run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    """Write a small JSON heartbeat for a simple status GUI to consume."""
    try:
        payload: Dict[str, Any] = {
            "name": "triage",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": __import__("time").time(),
            "orchestrator_version": ORCH_VERSION,
        }
        if extra:
            payload.update(extra)
        TRIAGE_HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        TRIAGE_HEARTBEAT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _is_wsl_env() -> bool:
    try:
        return "WSL_DISTRO_NAME" in os.environ or "microsoft" in (Path("/proc/version").read_text().lower())
    except Exception:
        return False


def _wsl_agent(goal_file: Path, max_steps: int = 1, apply: bool = False, dry_run: bool = True) -> Dict[str, Any]:
    """Run tools/agent_runner.py using WSL venv when on Windows, or directly if already inside WSL.

    Returns a dict with keys: ok (bool), stdout, stderr
    """
    goal_file_wsl = f"outgoing/{goal_file.name}"
    apply_flag = "--apply" if apply else ""
    dry_flag = "--dry-run" if dry_run else ""
    if _is_wsl_env():
        # Already inside WSL: use bash -lc to enable `source`
        inner = (
            "source ~/.calyx-venv/bin/activate && "
            "cd /mnt/c/Calyx_Terminal && "
            f"python -u tools/agent_runner.py --goal-file {goal_file_wsl} --max-steps {max_steps} {apply_flag} {dry_flag} --run-tests --skip-patches --test-cmd \"python -m compileall -q asr Scripts tools\""
        )
        proc = subprocess.run(["bash", "-lc", inner], capture_output=True, text=True)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}
    else:
        cmd = (
            "wsl bash -lc '"
            "source ~/.calyx-venv/bin/activate && "
            "cd /mnt/c/Calyx_Terminal && "
            f"python -u tools/agent_runner.py --goal-file {goal_file_wsl} --max-steps {max_steps} {apply_flag} {dry_flag} --run-tests --skip-patches --test-cmd \"python -m compileall -q asr Scripts tools\"'"
        )
        proc = _run(cmd)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}


def _latest_run_dir() -> Optional[Path]:
    runs = [p for p in OUT.glob("agent_run_*") if p.is_dir()]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name)[-1]


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_diff_for_try_it(diff_text: str) -> bool:
    """Lightweight check: the diff must include the powershell fenced block and not mass-edit other files.
    """
    if "README.md" not in diff_text:
        return False
    # Must contain the fenced block with the exact command
    if "```powershell" not in diff_text:
        return False
    if "python -u .\\\\Scripts\\\\listener_plus.py" not in diff_text.replace("\\", "\\\\"):
        return False
    return True


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _review(run_dir: Path, strict: bool = False) -> Dict[str, Any]:
    plan = _read_json(run_dir / "plan.json")
    audit = _read_json(run_dir / "audit.json")
    diffs_dir = run_dir / "diffs"
    diff_file = diffs_dir / "README.md.patch"
    review = {
        "plan_present": plan is not None,
        "audit_present": audit is not None,
        "diff_present": diff_file.exists(),
        "only_readme_changed": None,
        "try_it_snippet_ok": None,
        "files_ok": None,
        "signature": None,
        "orchestrator_version": ORCH_VERSION,
    }
    if audit:
        changed = audit.get("changed_files", [])
        review["only_readme_changed"] = (changed == [] or changed == ["README.md"])  # apply may be no-op
        # In strict mode require exactly README or no changes
        if strict:
            review["files_ok"] = review["only_readme_changed"] is True
        else:
            review["files_ok"] = review["only_readme_changed"] in (True, None)
    if diff_file.exists():
        diff_text = diff_file.read_text(encoding="utf-8", errors="ignore")
        review["try_it_snippet_ok"] = _check_diff_for_try_it(diff_text)
        # Produce a simple signature over the relevant materials
        plan_t = (run_dir / "plan.json").read_text(encoding="utf-8", errors="ignore") if (run_dir / "plan.json").exists() else ""
        audit_t = (run_dir / "audit.json").read_text(encoding="utf-8", errors="ignore") if (run_dir / "audit.json").exists() else ""
        payload = f"{ORCH_VERSION}\n{plan_t}\n{audit_t}\n{diff_text}"
        review["signature"] = _sha256_text(payload)
        # Write a signed review.json next to audit
        (run_dir / "review.json").write_text(json.dumps(review, indent=2), encoding="utf-8")
    return review


def _stability(run_pytest: bool = False, pytest_args: str = "-q") -> Dict[str, Any]:
    # Compile check using WSL venv, or direct if inside WSL
    if _is_wsl_env():
        cmd_compile = (
            "source ~/.calyx-venv/bin/activate && "
            "cd /mnt/c/Calyx_Terminal && "
            "python -m compileall -q asr Scripts tools"
        )
        proc_c = subprocess.run(["bash", "-lc", cmd_compile], capture_output=True, text=True)
    else:
        cmd_compile = (
            "wsl bash -lc '"
            "source ~/.calyx-venv/bin/activate && "
            "cd /mnt/c/Calyx_Terminal && "
            "python -m compileall -q asr Scripts tools'"
        )
        proc_c = _run(cmd_compile)
    result = {
        "compile_ok": proc_c.returncode == 0,
        "compile_stdout_tail": proc_c.stdout[-2000:],
        "compile_stderr_tail": proc_c.stderr[-2000:],
        "pytest_ok": None,
        "pytest_stdout_tail": None,
        "pytest_stderr_tail": None,
    }
    if run_pytest and result["compile_ok"]:
        if _is_wsl_env():
            cmd_pytest = (
                "source ~/.calyx-venv/bin/activate && "
                "cd /mnt/c/Calyx_Terminal && "
                f"pytest {pytest_args}"
            )
            proc_t = subprocess.run(["bash", "-lc", cmd_pytest], capture_output=True, text=True)
        else:
            cmd_pytest = (
                "wsl bash -lc '"
                "source ~/.calyx-venv/bin/activate && "
                "cd /mnt/c/Calyx_Terminal && "
                f"pytest {pytest_args}'"
            )
            proc_t = _run(cmd_pytest)
        result.update({
            "pytest_ok": proc_t.returncode == 0,
            "pytest_stdout_tail": proc_t.stdout[-4000:],
            "pytest_stderr_tail": proc_t.stderr[-4000:],
        })
    return result


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="3-phase triage orchestrator")
    ap.add_argument("--goal-file", required=True, help="Path to goal file under outgoing/")
    ap.add_argument("--max-steps", type=int, default=1)
    ap.add_argument("--strict", action="store_true", help="Require only README changes and exact snippet in review phase")
    ap.add_argument("--pytest", dest="run_pytest", action="store_true", help="Run pytest in stability phase")
    ap.add_argument("--pytest-args", default="-q", help="Arguments to pass to pytest (default: -q)")
    args = ap.parse_args(argv)

    goal_file = Path(args.goal_file)
    if not goal_file.exists():
        print(f"Goal file not found: {goal_file}", file=sys.stderr)
        return 2

    # Phase A: proposer/validator (apply+dry-run)
    try:
        goal_rel = str(goal_file if goal_file.is_absolute() else (ROOT / goal_file))
        # Normalize to path relative to ROOT for UI when possible
        goal_rel_display = str(Path(goal_rel).resolve())
        if goal_rel_display.startswith(str(ROOT)):
            goal_rel_display = str(Path(goal_rel_display).relative_to(ROOT))
    except Exception:
        goal_rel_display = str(goal_file)
    _write_hb("phase_a", status="running", extra={"goal_file": goal_rel_display})
    a_res = _wsl_agent(goal_file, max_steps=args.max_steps, apply=True, dry_run=True)

    # Phase B: reviewer (inspect latest run artifacts)
    run_dir = _latest_run_dir()
    if not run_dir:
        print("No agent_run directory found after Phase A", file=sys.stderr)
        _write_hb("phase_a", status="error")
        return 3
    _write_hb("phase_b", status="running", extra={"run_dir": str(run_dir.relative_to(ROOT))})
    review = _review(run_dir, strict=args.strict)

    # Phase C: stability (compile)
    _write_hb("phase_c", status="running")
    stab = _stability(run_pytest=args.run_pytest, pytest_args=args.pytest_args)

    report = {
        "phase_a": {"ok": a_res["ok"], "stdout_tail": a_res["stdout"][-1000:], "stderr_tail": a_res["stderr"][-1000:]},
        "phase_b": review,
        "phase_c": stab,
        "run_dir": str(run_dir.relative_to(ROOT)),
    }

    out_path = OUT / f"triage_{run_dir.name}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print a concise summary
    # Gate summary on compile pass, review rules, and optionally pytest pass
    review_ok = (
        review.get("diff_present") is True and
        review.get("files_ok") in (True, None) and
        review.get("try_it_snippet_ok") in (True, None)
    )
    stability_ok = bool(stab.get("compile_ok")) and (True if not args.run_pytest else bool(stab.get("pytest_ok")))
    summary_ok = bool(a_res["ok"]) and review_ok and stability_ok

    print("Triage summary:")
    print("  Phase A (apply+dry-run):", "PASS" if a_res["ok"] else "FAIL")
    print("  Phase B (review diffs):", "PASS" if review_ok else "FAIL")
    label_c = "compile+pytest" if args.run_pytest else "compile"
    print(f"  Phase C ({label_c}):", "PASS" if stability_ok else "FAIL")
    print("  Artifacts:", out_path)

    _write_hb("done", status="done", extra={
        "summary": {
            "phase_a": bool(a_res["ok"]),
            "phase_b": bool(review_ok),
            "phase_c": bool(stability_ok),
        },
        "report": str(out_path.relative_to(ROOT)),
    })

    return 0 if summary_ok else 1


if __name__ == "__main__":
    sys.exit(main())
