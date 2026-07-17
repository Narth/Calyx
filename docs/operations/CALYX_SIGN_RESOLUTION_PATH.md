---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Calyx Sign — Efficient path to a physical sign

When the default run fails (attach issues, or ssh-keygen "Couldn't load public key" / exit -1), follow this path. It avoids long debugging and gets to a valid `.sig` with minimal steps.

## Decision path

| Step | Try this | If it fails → |
|------|----------|----------------|
| **1. Default** | From repo: run `calyx_sign.ps1 -Receipt <path>`. Use **normal** PowerShell if you pre-mount the VHD in Explorer; use **Administrator** if you want the script to attach via diskpart. | Attach fails or "Insert USB" / manual mount → step 2. ssh-keygen "Couldn't load public key" or exit -1 → step 3. |
| **2. Manual mount** | In Explorer, open the USB path (e.g. `E:\calyx_identity\`), double-click `architect_identity.vhdx` to mount (e.g. V:). In **normal** PowerShell (same session as Explorer), run the script again; at "Insert USB key" press Enter. | Key still not found or ssh-keygen can't see V: → step 3. |
| **3. FromKeyDir** | Leave VHD mounted. Open **normal** PowerShell (Start menu). Run **two commands in order:** `cd V:\calyx_identity` then run the script with **-FromKeyDir** and full **-Receipt** path. Type SIGN line and passphrase. | If ssh-keygen still fails (e.g. different session/process isolation), → step 4. |
| **4. Laptop sign** | Sign on the laptop (C:\Calyx\tools\calyx_sign.ps1). Copy the `.sig` and signing receipt into this repo. See [CALYX_SIGN_LAPTOP_RUNBOOK.md](CALYX_SIGN_LAPTOP_RUNBOOK.md) for step-by-step and copy-back. | — |

## Why this order

- **Default** is one command and works when diskpart or the current session sees the key.
- **Manual mount** fixes "attach failed" and session mismatches (e.g. Explorer mount not visible in Admin PowerShell).
- **FromKeyDir** fixes child-process visibility: the script runs with CWD = key dir, so ssh-keygen is started from that directory and can open the key without relying on V: in a child.
- **Laptop** is the fallback when the desktop environment (Cursor, terminal, session isolation) consistently prevents the child from seeing V:.

## One-liner reminder (FromKeyDir)

After mounting the VHD in Explorer (e.g. CalyxArchitect (V:)):

```powershell
cd V:\calyx_identity; powershell -NoProfile -ExecutionPolicy Bypass -File C:\Calyx_Terminal\tools\calyx_sign.ps1 -Receipt C:\Calyx_Terminal\governance\approvals\cbo_sponsorship_research_test_improve.approval.json -FromKeyDir
```

(Replace the `-Receipt` path for other receipts.)

## After the first sign

Once you know which path works on your machine (e.g. FromKeyDir on desktop), use that path first next time; only fall back to the previous steps if something changes (e.g. new terminal, different drive letter).
