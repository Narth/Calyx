"""Health check Ollama models with prompt Return JSON {"ok": true}. Record latency."""
import subprocess
import time

prompt = 'Return JSON {"ok": true}'
models = ["tinyllama:latest", "qwen2.5:3b", "qwen2.5:7b", "qwen2.5-coder:7b"]
for m in models:
    t0 = time.perf_counter()
    r = subprocess.run(["ollama", "run", m, prompt], capture_output=True, text=True, timeout=120)
    dt = time.perf_counter() - t0
    ok = "ok" in r.stdout.lower() or "true" in r.stdout.lower() or r.returncode == 0
    print(f"{m}: ok={ok}, latency={dt:.2f}s")
