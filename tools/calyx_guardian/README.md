# Calyx Guardian — Phase 0 (Windows)

Phase 0 is a **no-install, read-only assessment** for Windows. It collects local system signals via PowerShell, normalizes findings with Python, and renders a deterministic Markdown report. No network calls, no background services.

## Usage (from repo root)

```powershell
powershell -ExecutionPolicy Bypass -File tools\calyx_guardian\guardian_assess_windows.ps1 -OutDir logs\calyx_guardian
python tools\calyx_guardian\guardian_assess_windows.py --outdir logs\calyx_guardian
python tools\calyx_guardian\render\render_report.py --outdir logs\calyx_guardian
```

## One-command verify (Phase 0)

```powershell
powershell -ExecutionPolicy Bypass -File tools\calyx_guardian\bootstrap_dev.ps1
powershell -ExecutionPolicy Bypass -File tools\calyx_guardian\run_phase0_windows.ps1 -OutDir logs\calyx_guardian
py -3.11 -m pytest tools\calyx_guardian\tests -q
```

Optional Guardian-only test runner with logging and retries:

```powershell
powershell -ExecutionPolicy Bypass -File tools\calyx_guardian\run_guardian_tests.ps1
```

## Outputs

- `logs/calyx_guardian/evidence.jsonl` (append-only evidence)
- `logs/calyx_guardian/findings.json` (normalized findings)
- `logs/calyx_guardian/report.md` (decision-maker readable)
- `logs/calyx_guardian/run_log.jsonl` (run ledger)

## Notes

- Phase 0 is local-first and read-only.
- If a command requires elevation and fails, the report will document the blind spot.
- Findings and reports are deterministic given the same system state and evidence.
- Findings include explicit lifecycle annotations (confidence score + added_due_to).
- Findings are withdrawn when visibility or confidence is insufficient; removals must be annotated in Night Watch deltas.
