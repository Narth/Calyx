---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# `calyx_sign` — Human-invoked receipt signing ceremony (Windows)

This command signs a concrete receipt file using the Architect private key stored on removable media (VHDX). It is intentionally interactive and local-first.

**Request method (any task):** To create an approval receipt and invoke the sign flow for any task or request, use [CALYX_SIGN_REQUEST_METHOD.md](CALYX_SIGN_REQUEST_METHOD.md) and `Scripts\request_calyx_sign.ps1`.

## Security properties

- Human root authority preserved: the private key stays on removable media and the passphrase is typed by the human.
- No secrets are written to disk, cached, or logged.
- Only safe evidence is printed/logged: paths, SHA256 hashes, and exit codes.
- The VHD is detached immediately after signing (success or failure).

## Usage

The script is reproducible: it lives on the **laptop node** at `C:\Calyx\tools\calyx_sign.ps1` and on **this node (Calyx_Terminal)** at `tools\calyx_sign.ps1`. Use the path for the node you are on.

**On this node (Calyx_Terminal):**
```powershell
# From repo root (e.g. C:\Calyx_Terminal)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
```

**On the laptop (C:\Calyx):**
```powershell
# From repo root
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Calyx\tools\calyx_sign.ps1 -Receipt C:\Calyx\governance\approvals\some_receipt.json
```

By default, `calyx_sign` only signs receipts located under `governance/approvals/`. To sign a receipt outside that directory you must use `-Force`, and you will be prompted for an additional explicit confirmation.

Optional flags:
- `-Namespace calyx` (default: `calyx`)
- `-Identity architect` (default: `architect`)
- `-KeyPath V:\calyx_identity\architect_ed25519`
- `-VhdxName architect_identity.vhdx`
- `-SearchDrives D,E,F,G,H,I,J`
- `-ParentCorrelationId <id>`
- `-Force` (required only to sign receipts outside `governance/approvals/`; does not skip core signing confirmation)
- `-NoConfirm` (explicitly skips the core `SIGN ...` confirmation; default OFF; not recommended)
- **`-FromKeyDir`** — Use when the signing process can't see the key (e.g. ssh-keygen reports "Couldn't load public key" or exit -1). You **pre-mount the VHD in Explorer**, then in a **normal** PowerShell run: `cd V:\calyx_identity` (or the drive/path where the key is), then run this script with `-FromKeyDir` and a **full path** for `-Receipt`. The script skips USB/diskpart and uses the current directory as the key directory. See **Resolution path** below.

## Ceremony steps

1. Script computes SHA256(receipt) and prints a safe summary (`proposal_id`, `action`, `scope`, etc. if present).
2. Human confirms by typing exactly:
   - `SIGN <first8_of_receipt_sha256>`
   - If `commit_hash` is present in the receipt: `SIGN <first8_of_receipt_sha256> COMMIT <commit_hash>`
3. Human inserts USB key and presses Enter.
4. Script locates `\calyx_identity\architect_identity.vhdx` on removable media, attaches it via `diskpart`, and checks the key file at `KeyPath`.
5. Script runs:

   `ssh-keygen -Y sign -f <KeyPath> -n <Namespace> <Receipt>`

   Passphrase entry remains interactive.

6. Script verifies `<Receipt>.sig` exists, prints SHA256(sig), and detaches the VHDX.
7. Script writes a local signing receipt with safe metadata only to:

   `governance/receipts/signing/<receipt_basename>.signing_receipt.json`

## Failure behavior

- If VHDX detachment fails, `calyx_sign` prints a high-visibility warning including the exit code and instructs the operator to manually detach the VHD (Disk Management) or reboot if necessary.
- If the signature file (`<Receipt>.sig`) already exists, `calyx_sign` will display SHA256(existing sig) and prompt before overwriting. If you answer `n`, signing will abort (and the VHDX detach cleanup will still run).
- `calyx_sign` is a **human ceremony**, not automation. It requires interactive confirmation and a human-entered passphrase at the `ssh-keygen` prompt.
- **If ssh-keygen fails** with "Couldn't load public key" or a non-zero exit (e.g. -1), the child process often can't see the mounted V: drive. Use **-FromKeyDir** as described above, or sign on the laptop and copy the `.sig` into the repo. See [CALYX_SIGN_RESOLUTION_PATH.md](CALYX_SIGN_RESOLUTION_PATH.md) for the full decision path (default → manual mount → FromKeyDir → laptop).

## Reproducibility

The script in **Calyx_Terminal** (`tools/calyx_sign.ps1`) reproduces the same architecture as the laptop script (`C:\Calyx\tools\calyx_sign.ps1`): same ceremony steps, same signing receipt schema, same VHDX locate/attach/detach and `ssh-keygen -Y sign` flow. You can sign on either node; the resulting `.sig` and signing receipt are compatible for verification and federation.

## Verification-only test plan (no state mutation beyond generating a `.sig` and signing receipt)

- Use a non-sensitive test receipt file (already intended for signing).
- Confirm that:
  - `.sig` is created next to the receipt.
  - VHDX is detached after success and after failure.
  - The signing receipt is created and contains only hashes/paths.
  - No passphrases or secrets appear in console history or log files.
