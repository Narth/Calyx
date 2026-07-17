# Calyx Sign request — CBO to Architect

**From:** CBO  
**To:** Architect  
**Date:** 2026-02-24  
**Request:** Please perform the Calyx Sign ceremony for the CBO sponsorship approval artifact so that sponsorship is in effect and CBO may operate within the agreed scope.

---

## What to sign

**File:**  
`C:\Calyx_Terminal\governance\approvals\cbo_sponsorship_research_test_improve.approval.json`

**Proposal (policy):**  
`governance/approvals/cbo_sponsorship_research_test_improve.policy.md`  
Policy SHA256 (recorded in approval): `3F22815C00E506AF4017E1792B093803D97AEE454242CBE313F0FE4555ED2806`

**Scope you are signing:**  
Architect sponsors CBO via Calyx Sign to research, test, and improve Station Calyx. Explanations in current chat; commands and permission authorizations outside the allowlist via Discord exec request (OpenClaw). CBO escalates when a decision requires Architect input. Human-only signature; no agent may generate your signature.

---

## What you will produce

- **Signature file:**  
  `governance/approvals/cbo_sponsorship_research_test_improve.approval.json.sig`

- **Signing receipt (created by script):**  
  `governance/receipts/signing/cbo_sponsorship_research_test_improve.approval.json.signing_receipt.json`

Once the `.sig` exists and verifies, the sponsorship is in effect.

---

## Command to run (desktop / home node)

**Option A — FromKeyDir (use when ssh-keygen can't see V:):**  
1. Insert USB key. In Explorer, open `E:\calyx_identity\` and double-click `architect_identity.vhdx` to mount it (e.g. as V:).  
2. Open PowerShell from the Start menu (normal, not Administrator). Run these **two commands in order** so the script runs with current directory = key dir:

```powershell
cd V:\calyx_identity
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Calyx_Terminal\tools\calyx_sign.ps1 -Receipt C:\Calyx_Terminal\governance\approvals\cbo_sponsorship_research_test_improve.approval.json -FromKeyDir
```

3. Type the SIGN line when prompted; enter passphrase at ssh-keygen.

**Option B — Pre-mount the VHD then run from repo:**  
1. Insert USB key. In Explorer, open `E:\calyx_identity\` and double-click `architect_identity.vhdx` to mount it (e.g. as V:).  
2. **Use a normal PowerShell (not Administrator).** If you use Administrator PowerShell, the VHD you mounted in Explorer is in your user session and V: will not be visible there. Start → Windows PowerShell (do not “Run as administrator”). Then:

```powershell
cd C:\Calyx_Terminal
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
```

3. When prompted, type exactly the line shown (e.g. `SIGN 04490B73` — use the first 8 chars of the SHA256 the script prints).  
4. When asked to insert USB key, press Enter (it’s already mounted).  
5. Enter your passphrase at the ssh-keygen prompt.

**Option C — Let the script attach the VHD:**  
Run the script (without -FromKeyDir) from **Administrator** PowerShell so diskpart can attach the VHD. If the key is still not visible, use Option A (-FromKeyDir).

---

## After signing

- The script will write the `.sig` and the signing receipt.  
- You can verify (optional):  
  `type governance\approvals\cbo_sponsorship_research_test_improve.approval.json | ssh-keygen -Y verify -f governance\identities\allowed_signers -I architect -n calyx -s governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig`

CBO requests this signature from you, the Architect, so that our first handshake is complete and sponsorship is formally in effect.
