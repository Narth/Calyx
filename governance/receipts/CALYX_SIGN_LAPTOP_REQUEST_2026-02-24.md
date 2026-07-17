# Calyx Sign — Laptop request (desktop V: visibility issue)

**Date:** 2026-02-24  
**From:** CBO  
**Reason:** Desktop sign failed with "Couldn't load public key architect_ed25519: No such file or directory" (ssh-keygen child cannot see V:). Sign to be performed on the laptop; artifacts then copied back to this repo for validation.

---

## Request

- **Receipt to sign:** `governance/approvals/cbo_sponsorship_research_test_improve.approval.json`  
- **Proposal:** CBO sponsorship (research, test, improve Station Calyx).  
- **Runbook:** [CALYX_SIGN_LAPTOP_RUNBOOK.md](../../docs/operations/CALYX_SIGN_LAPTOP_RUNBOOK.md)

---

## Laptop steps (summary)

1. Ensure receipt is on laptop at `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json` (copy from desktop if needed).
2. On the laptop: insert USB key, open PowerShell, run:
   ```powershell
   cd C:\Calyx
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
   ```
3. Type the SIGN line when prompted; enter passphrase at ssh-keygen.

---

## Copy-back to desktop (after signing on laptop)

Copy these two files from the **laptop** into this repo (**desktop**):

| From (laptop) | To (desktop — this repo) |
|---------------|---------------------------|
| `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig` | `governance/approvals/cbo_sponsorship_research_test_improve.approval.json.sig` |
| `C:\Calyx\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json` | `governance/receipts/signing/cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json` |

If desktop has laptop share as **Z:**:

```powershell
Copy-Item Z:\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig C:\Calyx_Terminal\governance\approvals\
Copy-Item Z:\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json C:\Calyx_Terminal\governance\receipts\signing\
```

---

## Validation on desktop (after copy-back)

From repo root:

```powershell
type governance\approvals\cbo_sponsorship_research_test_improve.approval.json | ssh-keygen -Y verify -f governance\identities\allowed_signers -I architect -n calyx -s governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig
```

Expected: **Signature verified.** Then commit the `.sig` and signing receipt.

---

**Status:** Sign completed on laptop; `.sig` copied to desktop and verified. See [CALYX_SIGN_LAPTOP_COPYBACK_VERIFIED_2026-02-24.md](CALYX_SIGN_LAPTOP_COPYBACK_VERIFIED_2026-02-24.md).
