"""Small local LLM test runner.

Checks model manifest policy, then attempts to run a short inference using available backends.
Writes an audit JSON to outgoing/ with results.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outgoing"
OUT_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT))
from tools.agent_policy import assert_allowed, get_model_entry


def try_vllm(model_path, prompt):
    try:
        from vllm import LLM
        # vllm expects a model name or path recognized by vllm server; skipping heavy server usage here
        return False, "vLLM backend present but not used in quick runner"
    except Exception:
        return False, "vllm not available"


def try_llama_cpp(model_path, prompt):
    try:
        from llama_cpp import Llama
    except Exception as e:
        return False, f"llama_cpp not installed: {e}"
    try:
        m = Llama(model_path=str(model_path))
        r = m(prompt, max_tokens=64)
        text = r.get("choices", [{}])[0].get("text", "")
        return True, text
    except Exception as e:
        return False, f"llama_cpp invocation failed: {e}"


def main():
    entry = get_model_entry()
    model_path = Path(entry["filename"])
    assert_allowed("inference", entry.get("id"))

    prompt = "Summarize: The quick brown fox jumps over the lazy dog."
    start = time.time()

    ok, result = try_vllm(model_path, prompt)
    backend = "vllm"
    if not ok:
        ok, result = try_llama_cpp(model_path, prompt)
        backend = "llama_cpp"

    end = time.time()
    audit = {
        "timestamp": int(start),
        "duration_s": end - start,
        "model_id": entry.get("id"),
        "model_path": str(model_path),
        "backend": backend,
        "success": ok,
        "result": result,
    }

    out_file = OUT_DIR / f"llm_test_{int(start)}.json"
    with out_file.open("w", encoding="utf-8") as fh:
        json.dump(audit, fh, indent=2)

    print("Audit written to:", out_file)
    print("Success:", ok)
    if ok:
        print("Result preview:")
        print(str(result)[:400])


if __name__ == "__main__":
    main()
