# Calyx Sign — Laptop copy-back verified

**Date:** 2026-02-24  
**From:** CBO  

---

## Signed approval: copied and verified

| Artifact | Location | Status |
|----------|----------|--------|
| **Signature (.sig)** | `governance/approvals/cbo_sponsorship_research_test_improve.approval.json.sig` | **Present.** Verified with `allowed_signers`: `Good "calyx" signature for architect` (ED25519). |
| **Signing receipt** | `governance/receipts/signing/cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json` | Not present in repo. Optional; add from laptop if you have it for audit. |

Sponsorship is in effect. The `.sig` validates; you may commit it (and the signing receipt if you copy it later).

---

## Laptop tooling (script was in backup, removed from main repo)

The `calyx_sign.ps1` script had been moved to a local backup on the laptop and was missing from the laptop main repo (`C:\Calyx`). **Canonical tooling for Calyx Sign lives in this repo (Calyx_Terminal):**

- **Script:** `tools/calyx_sign.ps1` (v1.2.0)
- **Docs:** `docs/operations/calyx_sign.md`, `CALYX_SIGN_REQUEST_METHOD.md`, `CALYX_SIGN_LAPTOP_RUNBOOK.md`
- **Helpers:** `Scripts/request_calyx_sign.ps1`, `Scripts/prompt_calyx_sign.ps1`

To restore the script on the laptop so future signs can run there:

- Copy **from this repo** to the laptop:
  - `C:\Calyx_Terminal\tools\calyx_sign.ps1` → `C:\Calyx\tools\calyx_sign.ps1`

Behavior is compatible (same ceremony, same receipt schema). Functionality confirmed: request flow and signature verification both succeed from this repo.
