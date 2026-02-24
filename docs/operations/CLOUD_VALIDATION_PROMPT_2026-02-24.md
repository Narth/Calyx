# Cloud CBO validation prompt — Deployment & Integration Harness v0.1

**Purpose:** Run this in the Linux cloud environment to validate the pull and confirm new changes are live.

---

## Instructions (copy and run in cloud)

```
You are CBO in the Linux cloud environment. Validate that the Station Calyx repo pull succeeded and the Deployment & Integration Harness v0.1 changes are live.

1. **Pull:** Run `git pull` (or `git fetch` + `git merge` as appropriate). Confirm no conflicts.

2. **Verify new files:**
   - `.env.example` exists at repo root
   - `tools/smoke_test.py` exists

3. **Verify code changes:**
   - `cbo_hub/dev_harness/app.py` — REPO_ROOT uses `_resolve_repo_root()` (no hardcoded C:\Calyx_Terminal)
   - `cbo_hub/cbo_core/app.py` — same pattern
   - `requirements.txt` — contains httpx, python-dotenv, rich

4. **Smoke test:** In a clean venv, run:
   ```bash
   pip install -r requirements.txt -q
   python tools/smoke_test.py --cbo-api-url http://127.0.0.1:8080 --dev-harness-url http://127.0.0.1:7777 --cbo-core-url http://127.0.0.1:7778
   ```
   (If CBO API / Dev Harness / CBO Core are not running in the cloud, report which checks would require services. The script should run without import errors.)

5. **Pytest:** Run `pytest tests/ -q` — expect 66 passed.

6. **Report:** Summarize: pull status, files present, smoke test result (or "services not running"), pytest result. Confirm: "Deployment & Integration Harness v0.1 changes are live" or list any gaps.
```

---

*Generated 2026-02-24. Station health at capture: fail (entropy high). Commits: c6c24b95, 4dd11854, 224e1f4f, 1bf41f5b.*
