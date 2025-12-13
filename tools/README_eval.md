Eval wake-word harness

Quick local usage (PowerShell):

```powershell
# activate venv (example)
.\n+Scripts\.venv\Scripts\Activate.ps1

# run unit tests (pytest must be installed)
pytest .\tools\test_kws.py

# run evaluator in mock mode (fast, no model download)
python .\tools\eval_wake_word.py --mock
```

CI snippet (GitHub Actions job - run tests and a smoke eval in mock mode):

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest .\tools\test_kws.py
      - name: Smoke eval (mock)
        run: python .\tools\eval_wake_word.py --mock --out logs/eval_mock.csv
```

Notes:
- `--mock` mode makes the evaluator deterministic for CI: it converts filenames to transcripts.
- Add WAV samples under `samples/wake_word/{positive,negative}` to run a full evaluation.
