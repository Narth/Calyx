---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Calyx Sign — Laptop node runbook

Use this when the **desktop** cannot complete the sign (e.g. ssh-keygen cannot see V:). Perform the ceremony on the **laptop**, then bring the signed artifacts back into the desktop repo for validation.

## Adopting the laptop script on the desktop

The laptop implementation has worked reliably; the desktop has had V: visibility issues. When the laptop share is mapped as **Z:**, run from the desktop repo:

```powershell
.\Scripts\sync_calyx_sign_from_laptop.ps1
```

This copies `Z:\tools\calyx_sign.ps1` into `tools\calyx_sign.ps1` on the desktop.

---

## Roles

| Node     | Repo root        | Role |
|----------|------------------|------|
| **Laptop**  | `C:\Calyx`       | Run Calyx Sign; USB key is here. Script writes `.sig` and signing receipt into the laptop repo. |
| **Desktop** | `C:\Calyx_Terminal` | Authoritative Station Calyx repo. After signing on laptop, copy the two artifacts here and validate. |

---

## Step 1: Ensure the receipt is on the laptop

The receipt to sign must exist under the laptop repo:

- **Path on laptop:** `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json`

If your laptop repo (`C:\Calyx`) is a separate clone or not in sync with the desktop:

- Copy from desktop to laptop:
  - **Receipt:** `C:\Calyx_Terminal\governance\approvals\cbo_sponsorship_research_test_improve.approval.json`
    → `C:\Calyx\governance\approvals\`
  - **Policy (optional):** `cbo_sponsorship_research_test_improve.policy.md` → same `governance\approvals\` folder

---

## Step 2: Run the sign on the laptop

1. Insert the **USB key** (VHDX with Architect identity) into the laptop.
2. Open **PowerShell** on the laptop (normal, not Administrator).
3. From the laptop repo root:

```powershell
cd C:\Calyx
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
```

4. When the script shows the receipt summary, type the **SIGN** line exactly (e.g. `SIGN 04490B73` — use the value printed).
5. When prompted, press Enter (USB key already inserted) or insert the key and press Enter.
6. Enter your **Architect passphrase** at the `ssh-keygen` prompt.

On success, the script writes:

- **Signature:** `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig`
- **Signing receipt:** `C:\Calyx\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json`

---

## Step 3: Copy artifacts into the desktop repo (for validation)

Copy the two files from the laptop into the **desktop** repo so the desktop has the signed sponsorship in its tree.

**From the laptop** (e.g. over network share, USB stick, or cloud):

| Copy from (laptop) | Copy to (desktop) |
|--------------------|--------------------|
| `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig` | `C:\Calyx_Terminal\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig` |
| `C:\Calyx\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json` | `C:\Calyx_Terminal\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json` |

If the desktop has the laptop share mapped as **Z:**, from the **desktop** you can copy:

```powershell
# Run on desktop (PowerShell)
Copy-Item Z:\governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig C:\Calyx_Terminal\governance\approvals\
Copy-Item Z:\governance\receipts\signing\cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json C:\Calyx_Terminal\governance\receipts\signing\
```

---

## Step 4: Validate on the desktop

From the desktop repo root:

```powershell
cd C:\Calyx_Terminal
type governance\approvals\cbo_sponsorship_research_test_improve.approval.json | ssh-keygen -Y verify -f governance\identities\allowed_signers -I architect -n calyx -s governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig
```

Expected: `Signature verified`. Then the sponsorship is in effect; you can commit the `.sig` and signing receipt.

---

## Request receipt (logged in repo)

A dated request receipt is written under `governance/receipts/` when CBO prepares a laptop sign request (e.g. `CALYX_SIGN_LAPTOP_REQUEST_2026-02-24.md`). It records what was requested, which receipt, and where to copy the artifacts. Use it as the checklist for copy-back and validation.
