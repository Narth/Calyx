---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1 — Validation Report

**Date:** 2026-02-27
**Branch:** wo-sunrise-canonical-bootpath-v1 (or successor)

---

## Deliverables

| Item | Status | Evidence |
|------|--------|----------|
| A) Contract hash enforcement | Done | `calyx/kernel/contract.py` enforces; tamper test passes |
| B) Intake/contract parity | Done | `discord_intake._get_contract_allowlists()`; `tests/test_contract_intake_parity.py` |
| C) API bind default loopback | Done | `calyx/cbo/api.py` default 127.0.0.1; `CALYX_API_BIND_HOST` override |
| D) Ingest repo-root hardening | Done | `calyx/mail/router.py` uses `resolve_repo_root()`; fail on unresolved |
| E) No Discord token in openclaw.json | Done | `Scripts/setup_openclaw_calyx.ps1` no longer writes token |
| F) README/INDEX drift | Done | `docs/INDEX.md` station_calyx clarified |

---

## V1 — Contract Integrity

```
# Tamper test
python -c "
from pathlib import Path
from calyx.kernel.contract import load_contract
p = Path('CALYX_CONTRACT.yaml')
orig = p.read_text()
p.write_text(orig.replace('patch_small', 'patch_smallx'))
try:
    load_contract(p)
    raise SystemExit('FAIL')
except ValueError as e:
    print('OK:', str(e)[:80])
p.write_text(orig)
"
# Output: OK: Contract integrity failed: declared hash does not match...
```

---

## V2 — Intake Parity

```
pytest tests/test_contract_intake_parity.py -v
# test_intake_allowlists_match_contract PASSED
# test_intake_rejects_contract_disallowed_task PASSED
# test_intake_accepts_contract_allowed_task PASSED
```

---

## V3 — Network Posture

- Default: `calyx/cbo/api.py` `run()` uses `host="127.0.0.1"`
- Override: `CALYX_API_BIND_HOST=0.0.0.0` → emits `audit.runtime.network.bind_override`

---

## V4 — Ingest Robustness

- `deliver_to_cbo_ingest` uses `resolve_repo_root(runtime_dir)` instead of `runtime_dir.parent`
- If `CALYX_CONTRACT.yaml` not found at resolved root → `audit.ingest.repo_root.unresolved`, reject

---

## V5 — Secret Persistence

- `setup_openclaw_calyx.ps1` no longer writes `DISCORD_BOT_TOKEN` to `openclaw.json`
- Canonical Discord path: `Scripts/sunrise_calyx.ps1` (env only)

---

## Artifacts

- `Scripts/update_contract_hash.py` — recompute hash after contract edits
- `CALYX_CONTRACT.yaml` — `contract_sha256` populated and enforced
