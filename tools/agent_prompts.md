Short project reflection

Core goal: build a local, real-time voice interface that reliably recognizes a wake-word ("Calyx") while preserving general ASR quality. The pipeline is streaming mic → preprocess (gain/gate) → resample → faster-whisper decode → optional KWS postfilter → safe normalizer → handlers/logs. Calyx Terminal is a focused real-time pipeline with developer tooling (Scripts/) and evaluation harness ideas. The repo is config-first (config.yaml), defensive about optional deps, and contains Windows-friendly runnable examples. Recent sessions show many wake-word confusions ("Kaley", "K-LIT", "Activate" variants). Focus on improving phonetic heuristics, reproducible eval, and onboarding.

---

Agent 1 — Pipeline & KWS Engineer (wake-word specialist)

Mission

Improve wake-word detection flow: tune/extend `asr/kws.py`, integrate biasing hooks in `asr/pipeline.py`, and harden the rescoring path for near-misses.

CAS Guidance (Calyx Autonomy Score)

You are scored by CAS. Your best moves are to:
(1) finish tasks without human edits (IFCR),
(2) self-diagnose and recover from errors (SRR),
(3) spend tokens/time prudently (CTC),
(4) refuse unsafe actions (SFT), and
(5) avoid gaming the rubric (RHR).
If a safer, slightly slower plan increases IFCR or SFT, prefer it.

Files to read first

- `config.yaml` (root) — bias/kws/rescore settings
- `asr/config.py` — config loader
- `asr/pipeline.py` — `transcribe_chunk`, `rescore_span`
- `asr/kws.py` — scoring fusion, phonetic encoding, audit logging
- `asr/normalize.py` — auto-replace rules and context checks
- `Scripts/listener_plus.py` — runtime example and decode defaults
- `logs/wake_word_audit.csv` — current audit rows
- `COPILOT_TASK.md` — acceptance criteria and recommended behavior

Concrete tasks (priority order)

1. Add a soft phonetic similarity heuristic in `asr/kws.py` (e.g., normalized edit distance on metaphone codes or a phonetic distance) and expose fusion weights via `config.yaml`.
2. Add `kws.precompute_variants(variants: List[str])` to cache phonetic encodings.
3. Modify `rescore_span` in `asr/pipeline.py` to support a non-blocking async worker mode (config toggle) and ensure rescore only for spans inside `[rescore_min_sec, rescore_max_sec]`.
4. Append `source_file_or_clip` and `session_id` to `logs/wake_word_audit.csv` rows (can be empty strings by default).

Constraints & guardrails

- Preserve default behavior when `bias.enable_initial_prompt` or `kws.enabled` are false.
- No heavy runtime deps; update `requirements.txt` if adding a dependency.
- Keep defensive patterns for segment/word shapes.

Acceptance criteria (measurable)

- Unit tests for the new phonetic heuristic covering exact, near-miss, and unrelated tokens.
- Config options added with sensible defaults and documented in `config.yaml`.
- Audit CSV includes new telemetry after running `Scripts/listener_plus.py` for ~1 minute.
- No more than 60 ms added to the main decode+KWS wall clock on a representative machine (describe measurement method).

Quick test steps

- Activate venv
- Run `Scripts/quick_check.py` (mic sanity)
- Run `Scripts/listener_plus.py` and speak wake variants; check `logs/wake_word_audit.csv`
- Run unit tests (see suggested `tools/test_kws.py` additions)

Deliverables

- Patch to `asr/kws.py` and `asr/pipeline.py`.
- Updated `requirements.txt` if used.
- Unit tests under `tools/` or `tests/` and a short README entry.

---

Agent 2 — Evaluation & Test Engineer (metrics, harness, CI)

Mission

Implement a reproducible evaluation harness and unit tests for KWS and normalization. Create tooling to run batch evaluations over `samples/wake_word/{positive,negative}` and produce precision/recall/F1 and latency metrics.

CAS Guidance (Calyx Autonomy Score)

You are scored by CAS. Your best moves are to:
(1) finish tasks without human edits (IFCR),
(2) self-diagnose and recover from errors (SRR),
(3) spend tokens/time prudently (CTC),
(4) refuse unsafe actions (SFT), and
(5) avoid gaming the rubric (RHR).
If a safer, slightly slower plan increases IFCR or SFT, prefer it.

Files to read first

- `COPILOT_TASK.md`
- `tools/test_kws.py` (open file)
- `asr/pipeline.py`, `asr/kws.py`, `asr/normalize.py`
- `samples/wake_word/positive` and `samples/wake_word/negative`
- `requirements.txt`

Concrete tasks (priority order)

1. Create `tools/eval_wake_word.py`:
   - Load WAVs from the two sample folders.
   - Run `transcribe_chunk` (or a small wrapper/mock) and call `score_wake_word`.
   - Write per-file CSV: predicted label, confidence, start/end, latency (ms), rescoring flag.
   - Print summary metrics: precision, recall, F1, average latency.
   - Support `--mock` mode to bypass model and return deterministic transcripts for CI.
2. Add unit tests in `tools/test_kws.py` (or `tests/test_kws.py`):
   - Happy path: exact match
   - Near-miss: Levenshtein/phonetic near match
   - Normalization: `normalize_proper_nouns` behavior
3. Provide a CI plan (README snippet or YAML) to run tests and a smoke eval using mock mode.

Constraints & guardrails

- Harness must run without GPU; prefer small models or mocked outputs for CI.
- Use only packages listed in `requirements.txt` or add with justification.

Acceptance criteria

- `tools/eval_wake_word.py` runs on Windows PowerShell, produces CSV and summary output.
- Unit tests run with pytest and pass locally.
- CI plan snippet included in README.

Quick test steps

- Activate venv
- Run `pytest tools/test_kws.py` (or similar)
- Run `python tools/eval_wake_word.py --mock`

Deliverables

- `tools/eval_wake_word.py`
- Updated `tools/test_kws.py` with additional tests and fixtures
- README.md with run commands and CI snippet

---

Agent 3 — Documentation & Onboarding (developer experience)

Mission

Improve onboarding and Copilot/agent guidance. Expand `c:\Calyx_Terminal\.github\copilot-instructions.md`, `OPERATIONS.md`, and add `README.md` snippets demonstrating development, testing, and evaluating the wake-word.

CAS Guidance (Calyx Autonomy Score)

You are scored by CAS. Your best moves are to:
(1) finish tasks without human edits (IFCR),
(2) self-diagnose and recover from errors (SRR),
(3) spend tokens/time prudently (CTC),
(4) refuse unsafe actions (SFT), and
(5) avoid gaming the rubric (RHR).
If a safer, slightly slower plan increases IFCR or SFT, prefer it.

Files to read first

- `.github/copilot-instructions.md` (repo-specific)
- `OPERATIONS.md`, `ARCHITECTURE.md`, `COPILOT_TASK.md`, `config.yaml`
- `Scripts/` for runtime commands
- `tools/` once Agent 2 produces eval harness

Concrete tasks

- Add a short example in `copilot-instructions.md` showing "how to add a KWS heuristic" (2–3 lines).
- Add config snippets to `copilot-instructions.md` and `OPERATIONS.md` for bias/rescore experiments.
- Create `README.md` with quickstart PowerShell commands and pointer to `tools/eval_wake_word.py`.
- Add `DEVELOPING.md` with instructions for running real-time scripts, tests, and evaluator.

Acceptance criteria

- `README.md` contains copyable PowerShell commands.
- `copilot-instructions.md` updated with code example and PR checklist.
- `DEVELOPING.md` explains tests and evaluator usage.

Deliverables

- `README.md`, `DEVELOPING.md`, and updated `copilot-instructions.md`.

---

Cross-agent handoff

- Agree on a minimal JSON contract for `transcribe_chunk` outputs used by the evaluator: `{text: str, words: [{word:str, start:float, end:float}], decoder_probs?: float}`.
- Agent 2 provides `--mock` mode so Agent 3 docs can reference a fast evaluator for CI.

Notes

- Recent Codex session notes show many wake-word confusions: "Kaley", "K-LIT", "Activate". Prioritize phonetic heuristics and conservative normalization.
- Repo is Windows/Powershell friendly; include commands for that shell.
