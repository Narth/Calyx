DEVELOPING — developer guide

This file contains quick developer-oriented instructions for running the repo locally, running tests, and running the eval harness in mock mode.

1) Setup

PowerShell (recommended):

```powershell
.
Scripts\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Run unit tests

```powershell
pytest -q
```

3) Eval harness (mock mode)

If CI or dev machines should avoid pulling models, use the evaluator's mock mode (Agent 2 will add it) which reads a JSON of deterministic transcripts. Example (when implemented):

```powershell
python .\tools\eval_wake_word.py --cfg config.yaml --mock --mock-file tools/mock_transcripts.json
```

4) Adding new samples

Place WAVs under `samples/wake_word/positive` (contains wake-word) or `samples/wake_word/negative` (no wake-word). Run the evaluator to regenerate metrics and CSV outputs.

5) CI plan (copy-paste YAML snippet)

- name: Test and smoke eval
  run: |
    python -m pip install -r requirements.txt
    pytest -q
    python tools/eval_wake_word.py --cfg config.yaml --mock --mock-file tools/mock_transcripts.json

6) Notes

- Keep the mock mode deterministic so CI runs fast and doesn't need large model downloads.
- Tests should avoid live microphone operations. Use `--mock` or unit test fixtures that call `asr.kws` functions directly.
