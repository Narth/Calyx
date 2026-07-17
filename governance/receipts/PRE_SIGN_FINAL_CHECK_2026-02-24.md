# Pre-sign final check — 2026-02-24

**Status:** Complete. Proceed to Calyx Sign on desktop.

## Checks run

| Check | Result |
|-------|--------|
| Policy SHA256 vs approval.json | Match: `3F22815C00E506AF4017E1792B093803D97AEE454242CBE313F0FE4555ED2806` |
| Option A (commit before sign) | Done. Commit `898f2b48`: sponsorship set in tree. |
| Z:\ / two-node from this session | Z: not mapped in Cursor/agent shell; cannot run compare from here. You’re signing on desktop; laptop comparison optional for this run. |
| Architect: Option A, verbal OK, good to go, desktop | Confirmed. |

## Command to run (desktop / home node)

From **Administrator** PowerShell (so diskpart can attach the VHD without a mid-session elevation prompt), or with the VHD **pre-mounted** in Explorer and a normal PowerShell:

```powershell
cd C:\Calyx_Terminal
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
```

Then: type the SIGN line when prompted, insert USB key when asked, enter passphrase at ssh-keygen. The script will write `.approval.json.sig` and a signing receipt under `governance/receipts/signing/`.

---

CBO. Last pre-check complete. Go when you are ready.
