---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Governance Integration — BloomOS & Station Calyx

**Date:** 2026-02-21
**Status:** Implemented

---

## Summary

Four governance wiring points integrated per BloomOS and Station Calyx developments:

1. **Integrity gate for CBO Core** — `/chat` runs spine integrity check before handling
2. **Stamping gates** — Sponsorship verification module; `/sponsorship` endpoint
3. **Spine integration** — `POST /execute` routes through Mail → Intent → Work Envelope → Contract Gate → Execution
4. **Calyx Guardian** — `tools/calyx_guardian/` stub wired for governance plans

---

## 1. Integrity Gate (CBO Core)

- **Where:** `cbo_hub/cbo_core/app.py` — `_check_integrity_gate()` at start of `/chat`
- **Behavior:** Calls `calyx.kernel.integrity_gate.gate_before_action` before any chat. On failure → HTTP 503.
- **Scope:** Mail inbox, intent artifacts, replay ledger, contract, receipts (execution path not required for chat).

---

## 2. Stamping Gates

- **Module:** `cbo_hub/cbo_core/stamping.py`
  - `check_sponsorship()` — verify `.sig` exists and optionally run `ssh-keygen -Y verify`
  - `require_sponsorship_for_stamped_op()` — raise `PermissionError` if not valid
- **Endpoint:** `GET /sponsorship` — returns `{valid, reason, proposal_id}` for BloomOS/tooling
- **Usage:** When CBO adds fs_write or script execution tools, call `require_sponsorship_for_stamped_op()` before those ops.

---

## 3. Spine Integration

- **Endpoint:** `POST /execute`
- **Body:** `{ task_type, scope?, constraints?, intent_summary? }`
- **Flow:** Mail Envelope → deliver_to_cbo_ingest → ingest → mark_ready → mint Work Envelope → process_work_outbox
- **Contract:** `cbo_core` added to `allowed_sources` in CALYX_CONTRACT.yaml (phase_a)
- **OpenClaw bridge:** Future: add `request_execution` tool that calls `POST /execute` instead of `/chat` for spine-routed execution.

---

## 4. Calyx Guardian

- **Path:** `tools/calyx_guardian/`
- **Scripts:** `local_owner_confirm.ps1`, `run_phase0_windows.ps1`, `guardian_watch_baseline.ps1`, `guardian_watch_observer.ps1`
- **Render:** `render/guardian_manifest.py`, `guardian_watch_analysis.py`, `guardian_night_watch_brief.py`
- **Tests:** `tests/test_smoke_phase0.py` — passes
- **Status:** Stubs; governance plans (`guardian_assessment_bundle.json`, `guardian_night_watch.json`) now have runnable targets.

---

## BloomOS Alignment

- **STATE.md:** Status, heartbeat_ts, checks, health — unchanged. Sponsorship block already documents signed artifact.
- **HEARTBEAT:** Can optionally call `GET /sponsorship` to verify sponsorship live; not required for current flow.
- **Airflow:** Throttle ingestion; direct energy to writing. Integrations are lightweight (gate check, sponsorship check).

---

## Verification

```powershell
# Integrity gate (CBO Core must be running)
Invoke-RestMethod -Uri "http://127.0.0.1:7778/chat" -Method POST -ContentType "application/json" -Body '{"user_text":"hi","model_role":"local"}' | Select-Object reply_text

# Sponsorship
Invoke-RestMethod -Uri "http://127.0.0.1:7778/sponsorship" -Method GET

# Spine execute (doc_update)
Invoke-RestMethod -Uri "http://127.0.0.1:7778/execute" -Method POST -ContentType "application/json" -Body '{"task_type":"doc_update","intent_summary":"test"}'

# Guardian smoke
python tools/calyx_guardian/tests/test_smoke_phase0.py
```
