---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Calyx two-node implementation paths — Laptop vs Desktop

**Purpose:** Canonical implementation paths for the **laptop node** (Calyx repo at `C:\Calyx`, exposed on this PC as `Z:\` when shared) and the **desktop node** (Calyx_Terminal at `C:\Calyx_Terminal`), and how to assess both from this PC.

## Node roles

| Node        | Repo root (local)   | On this PC (desktop)     | Role |
|------------|---------------------|---------------------------|------|
| **Laptop** | `C:\Calyx`          | `Z:\` (mapped share)      | Original Calyx repo; `calyx_sign.ps1` source; governance/approvals. |
| **Desktop**| `C:\Calyx_Terminal` | `C:\Calyx_Terminal`       | Station Calyx hub; CBO, Avatar Web, gateway; reproduced `tools\calyx_sign.ps1`. |

## Implementation paths (canonical)

### Laptop node (C:\Calyx → Z:\ when shared)

| Purpose              | Path (on laptop)              | Path (from this PC when Z: mapped) |
|----------------------|-------------------------------|-------------------------------------|
| Repo root            | `C:\Calyx`                    | `Z:\`                               |
| Calyx Sign script    | `C:\Calyx\tools\calyx_sign.ps1` | `Z:\tools\calyx_sign.ps1`         |
| Governance approvals | `C:\Calyx\governance\approvals\` | `Z:\governance\approvals\`       |
| Signing receipts     | `C:\Calyx\governance\receipts\signing\` | `Z:\governance\receipts\signing\` |
| Architect contract   | `C:\Calyx\governance\contracts\architect_approval.md` | `Z:\governance\contracts\architect_approval.md` |
| Operations doc       | `C:\Calyx\docs\operations\calyx_sign.md` | `Z:\docs\operations\calyx_sign.md` |

### Desktop node (Calyx_Terminal)

| Purpose              | Path |
|----------------------|------|
| Repo root            | `C:\Calyx_Terminal` |
| Calyx Sign script    | `C:\Calyx_Terminal\tools\calyx_sign.ps1` |
| Governance approvals | `C:\Calyx_Terminal\governance\approvals\` |
| Signing receipts     | `C:\Calyx_Terminal\governance\receipts\signing\` |
| Architect contract   | `C:\Calyx_Terminal\governance\contracts\architect_approval.md` |
| Operations doc       | `C:\Calyx_Terminal\docs\operations\calyx_sign.md` |
| CBO / Station Calyx  | `C:\Calyx_Terminal\cbo_hub\`, `Scripts\start_calyx_core_services.ps1`, `STATE.md` |

## Differences (implementation path vs behavior)

- **Laptop:** Single canonical Calyx repo; `calyx_sign.ps1` is the original build. No CBO hub/Station Calyx stack on the laptop repo itself (unless added).
- **Desktop:** Calyx_Terminal adds CBO hub, Avatar Web, telemetry gateway, Station Calyx scripts; it also has a **reproduced** `tools\calyx_sign.ps1` (same ceremony, same receipt schema) so signing can be done on the desktop without the laptop. Governance layout (`governance/approvals/`, `governance/receipts/signing/`, `governance/contracts/`) is aligned so receipts and policies are compatible.
- **Signing:** You can sign on either node. Receipts and `.sig` files are interchangeable for verification. When running from this PC, the USB key (VHDX) must be on this PC; the receipt and script can live on `Z:\` or on `C:\Calyx_Terminal`.

## Full system comparison (run when Z: is live)

From a PowerShell session where **Z:** is mapped to the laptop’s Calyx share:

```powershell
cd C:\Calyx_Terminal
.\Scripts\compare_calyx_nodes.ps1
```

Options:

- **Default:** Human-readable table of key paths (exists/missing on laptop vs desktop) and `calyx_sign.ps1` versions.
- **`-Json`:** Machine-readable report for automation:
  ```powershell
  .\Scripts\compare_calyx_nodes.ps1 -Json
  ```

The script checks:

- Both roots (Z:\ and C:\Calyx_Terminal) accessible.
- Existence of `tools\calyx_sign.ps1`, `governance\approvals`, `governance\contracts\architect_approval.md`, `governance\receipts\signing`, `governance\identities\allowed_signers`, `docs\operations\calyx_sign.md`, `STATE.md`, `README.md`, `cbo_hub`, `Scripts\start_calyx_core_services.ps1`, `Scripts\check_calyx_core_services.ps1`.
- Script version in `tools\calyx_sign.ps1` on each node (if present).

If Z: is not mapped, the script reports that the laptop root is not accessible and reminds you to map Z: to `\\<laptop>\Calyx`.

## Confirming implementation path from here

1. **Ensure Z: is live** (mapped to laptop’s Calyx share).
2. Run: `.\Scripts\compare_calyx_nodes.ps1`
3. Confirm both nodes show **OK** for the paths you care about (e.g. `tools\calyx_sign.ps1`, `governance\approvals`).
4. Use **docs/operations/SHARE_CALYX_REPO_LAPTOP_TO_PC.md** for share setup and caveats (VHD local, latency, laptop must be on).
