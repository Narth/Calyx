---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_OPENCLAW_DECOMMISSION_GATING_V2 — Verification Ladder

---

## E1 — Baseline Clean Run (OpenClaw OFF)

1. Stop OpenClaw (services, tasks, processes). See OPENCLAW_DECOMMISSION_PLAYBOOK.md.
2. Start Calyx + gateway: `.\Scripts\start_calyx_core_services.ps1`
3. Run: `python Scripts/audit_health.py --since-minutes 60`

**Expected:**
- No `audit.external.emitter.detected`
- No `audit.runtime.singularity.breach`
- Exactly one sender identity
- audit_health exit 0

---

## E2 — Adversarial Probe (OpenClaw ON)

1. Start OpenClaw (service/task/manual)
2. Attempt to start Calyx: `.\Scripts\start_calyx_core_services.ps1`

**Expected:**
- CBO preflight fails (exit 1)
- Emits `audit.external.emitter.detected`
- Emits `audit.runtime.singularity.breach`
- Emits `governance.assertion.failed`
- Stderr: "OpenClaw detected", "See OPENCLAW_DECOMMISSION_PLAYBOOK.md"

---

## E3 — Gate CLI

```powershell
python -m calyx.kernel.external_emitter_gate
```

**With OpenClaw OFF:** Exit 0, "No OpenClaw detected."
**With OpenClaw ON:** Exit 1, emits audit events to ledger.

---

## E4 — Restart Invariance

1. With OpenClaw OFF, perform 3 restarts of Calyx + gateway
2. After each: run audit_health

**Expected:** No OpenClaw detection, sender singularity stable.

---

## Config Override (Migration Only)

```powershell
$env:ALLOW_OPENCLAW_FOR_MIGRATION = "true"
# Bypasses gate. Remove after decommission.
```
