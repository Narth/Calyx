"""
LLM Ladder: Run autonomous_exec_v0_1_llm across 4 models × 3 seeds.
Sequential, no parallel. Updates llm_config.json per model.
"""
import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path("runtime")
SUITE = Path("benchmarks/suites/autonomous_exec_v0_1")
MODELS = ["tinyllama:latest", "qwen2.5:3b", "qwen2.5:7b", "qwen2.5-coder:7b"]
SEEDS = [1337, 314159, 271828]


def update_llm_config(model_id: str) -> None:
    cfg_path = RUNTIME / "llm_config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["model_id"] = model_id
    cfg["command"] = [str(cfg["command"][0]), "run", model_id]
    cfg_path.write_text(json.dumps(cfg, indent=None) + "\n")


def run_one(model_id: str, seed: int) -> bool:
    update_llm_config(model_id)
    cmd = [
        sys.executable, "-m", "benchmarks.harness.autonomous_suite_runner_llm",
        "--runtime-dir", str(RUNTIME),
        "--suite-path", str(SUITE),
        "--run-id", "autonomous_exec_v0_1_llm",
        "--seed", str(seed),
    ]
    r = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1])
    return r.returncode == 0


def main():
    for model in MODELS:
        for seed in SEEDS:
            print(f"Running model={model} seed={seed}...", flush=True)
            ok = run_one(model, seed)
            if not ok:
                print(f"FAILED: model={model} seed={seed}")
                sys.exit(1)
            # Check no .tmp
            tmps = list(RUNTIME.rglob("*.tmp"))
            if tmps:
                print(f"STOP: .tmp files remain: {tmps}")
                sys.exit(1)
    print("All 12 runs complete.")


if __name__ == "__main__":
    main()
