"""Run repo stability checks: compile-all and pytest.

Outputs a concise JSON summary to stdout so callers can parse results.
Designed to be executed inside WSL venv (see OPERATIONS.md).
"""
from __future__ import annotations

import json
import sys
import io
import contextlib
import subprocess
from pathlib import Path


def run_compile_all(root: Path) -> dict:
    import compileall
    # Quiet=2: suppress most filenames, return bool
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        ok = compileall.compile_dir(str(root), maxlevels=20, force=False, quiet=2)
    out = buf.getvalue()
    return {"ok": bool(ok), "stdout_tail": out[-2000:]}


def run_pytest(root: Path, args: list[str] | None = None) -> dict:
    # Default to running tests under tools/ only to avoid hardware-dependent tests under Scripts/
    args = args or ["-q", "tools"]
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", *args], cwd=str(root), capture_output=True, text=True)
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "error": str(exc)}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "outgoing"
    out.mkdir(exist_ok=True)
    compile_res = run_compile_all(root)
    pytest_res = run_pytest(root)
    summary = {
        "compile": compile_res,
        "pytest": pytest_res,
        "overall_ok": bool(compile_res.get("ok") and pytest_res.get("ok")),
    }
    # Write to outgoing for GUI/tools to consume
    (out / "stability_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
