"""
Self-test for local LLM harness.
Loads benchmarks/outcome/local_models.json and tries the first model.
If runner missing, writes a report noting MISSING_RUNNER (does not stub success).
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import tempfile

REPORT_DIR = Path("reports/local_llm")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main():
    config_path = Path("benchmarks/outcome/local_models.json")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "local_llm_harness_report.md"

    if not config_path.exists():
        report_path.write_text("Config missing: benchmarks/outcome/local_models.json\n", encoding="utf-8")
        sys.exit(1)

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    models = cfg.get("models", [])
    if not models:
        report_path.write_text("No models configured.\n", encoding="utf-8")
        sys.exit(1)

    m = models[0]
    runner = Path(m["runner_path"])
    model_path = Path(m["model_path"])
    prompt = "Self-test prompt: say 'hello' briefly."
    tmp_dir = Path(tempfile.mkdtemp())
    prompt_file = tmp_dir / "prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    out_json = tmp_dir / "out.json"

    cmd = [
        sys.executable,
        "benchmarks/tools/local_llm_runner.py",
        "--runner",
        str(runner),
        "--model-path",
        str(model_path),
        "--model-id",
        m["model_id"],
        "--prompt-file",
        str(prompt_file),
        "--n-predict",
        str(m.get("n_predict", 256)),
        "--temperature",
        str(m.get("temperature", 0.7)),
        "--top-p",
        str(m.get("top_p", 0.9)),
        "--seed",
        str(m.get("seed", 42)),
        "--timeout-sec",
        str(m.get("timeout_sec", 120)),
        "--out-json",
        str(out_json),
    ]

    result = {
        "timestamp": now_iso(),
        "runner": str(runner),
        "model_path": str(model_path),
        "status": None,
        "details": "",
    }

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if out_json.exists():
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            result["status"] = payload.get("status")
            result["details"] = payload
        else:
            result["status"] = "NO_JSON"
            result["details"] = proc.stderr
    except Exception as e:
        result["status"] = "ERROR"
        result["details"] = f"{type(e).__name__}: {e}"

    lines = []
    lines.append("# Local LLM Harness Report")
    lines.append("")
    lines.append(f"Timestamp: {result['timestamp']}")
    lines.append(f"Runner: {result['runner']}")
    lines.append(f"Model path: {result['model_path']}")
    lines.append(f"Status: {result['status']}")
    lines.append("")
    lines.append("Details:")
    lines.append("```\n" + json.dumps(result["details"], ensure_ascii=False, indent=2) + "\n```")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("Report written:", report_path)
    if result["status"] != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
