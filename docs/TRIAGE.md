# Triage cycles — Calyx Terminal

This project uses a lightweight 3-phase triage loop to keep changes safe and observable. It’s designed for local-first development and simple tooling.

## Phases (A → B → C)
- A — Proposer/Validator
  - Run the agent in apply+dry-run to generate a deterministic plan and diffs.
  - Tooling: `tools/agent_runner.py` via `tools/triage_orchestrator.py`.
  - Output: `outgoing/agent_run_<ts>/` (plan.json, diffs/, audit.json).

- B — Reviewer
  - Inspect emitted diffs and audit; enforce scope constraints (e.g., only allowed files).
  - Tooling: `tools/triage_orchestrator.py` creates `review.json` next to `audit.json`.
  - Gate examples: require only README change for certain goals; check snippet exactness.

- C — Stability
  - Compile check (always) + optional tests.
  - Tooling: `python -m compileall -q .` and, if enabled, `pytest`.
  - Output: triage summary JSON under `outgoing/triage_*.json`.

## Domain coverage checklist (stability “what to cover”)
Use these domains to drive targeted tasks when stability dips or after significant changes:

- Audio IO & preproc
  - Device index discovery (`Scripts/list_mics.py`), sample rate, gain/gate behavior.
  - Resample path to 16k, glitch/drop detection.

- Decoder/ASR
  - faster-whisper model loading, device/compute-type config.
  - Word timestamps availability and drift handling.

- KWS & normalization
  - Phonetic & Levenshtein fusion; thresholds; audit logging (`logs/wake_word_audit.csv`).
  - Proper-noun normalization safety.

- Orchestration/Agents
  - Agent heartbeat & planner loops; watcher responsiveness.
  - Triage A/B/C pass rates and runtime errors.

- UX/Docs/Operations
  - README/OPERATIONS discoverability; Milestones and Heartbeats indices.
  - Pack/export scripts and basic runbooks.

Tip: Group TODOs under these headings in `TODO.MD` to improve the Tasks Dashboard signal.

## How to run
- One-shot triage (A→B→C, compile-only):
```powershell
python -u .\tools\triage_orchestrator.py --goal-file outgoing\goal_hello.txt
```
- Include pytest (if your environment has audio deps):
```powershell
python -u .\tools\triage_orchestrator.py --goal-file outgoing\goal_hello.txt --pytest
```

## Observability
- Heartbeats:
  - Agent1 → `outgoing/agent1.lock`
  - Triage → `outgoing/triage.lock`
- Dashboard:
  - Human: `logs/TASKS.md`
  - Machine: `outgoing/tasks_dashboard.json` (includes agents + latest triage summary)

## Keep triage "Active" with a lightweight probe
When the Watcher shows triage as idle but you want an always-on support presence, run the ultra-light probe:

```powershell
# Runs a tiny heartbeat loop; every ~30s it performs a 1–2 token LLM check if llama-cpp is available
python -u .\tools\triage_probe.py --interval 2 --probe-every 15

# Prefer the small probe model (if added to manifest)
python -u .\tools\triage_probe.py --interval 2 --adaptive --model-id tinyllama-1.1b-chat-q5_k_m --initial-probe-sec 30 --relaxed-probe-sec 300
```

Notes:
- Intended to run inside WSL with the `~/.calyx-venv` from OPERATIONS. If `llama_cpp` or the model manifest is missing,
  the probe still emits heartbeats (status=running) so the Watcher shows an animated spinner for triage.
- Heartbeat extras include `probe.last` with `ok/latency_ms/text/error` and the detected backend.
- Stop with Ctrl+C; the probe writes a final `status=done` heartbeat on exit.

### Probe model in the manifest
- A small GGUF (e.g., TinyLlama 1.1B) can be added to `tools/models/MODEL_MANIFEST.json` with `role: "probe"`.
- The probe automatically prefers a `role=probe` model when available; override explicitly via `--model-id`.
