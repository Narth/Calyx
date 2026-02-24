# Sharing C:\Calyx (laptop) to this PC for read/write access

You can share the laptop’s **C:\Calyx** repo to this computer so both codebases are usable from here (and, if you want, from the laptop).

## On the laptop

1. **Share the Calyx folder**
   - Right‑click **C:\Calyx** → **Properties** → **Sharing** tab → **Advanced Sharing**.
   - Check **Share this folder**.
   - **Share name:** e.g. `Calyx`.
   - **Permissions:** add your user (or Everyone if both machines use the same account name/password) with **Change** (read/write).
   - OK out.

2. **Note the laptop’s name or IP**
   - In a cmd window: `hostname` (e.g. `LAPTOP-ABC`) or `ipconfig` for IPv4 (e.g. `192.168.1.10`).

## On this PC (Calyx_Terminal)

1. **Map a drive to the share**
   - In Explorer: **This PC** → **Map network drive**.
   - **Drive:** e.g. `Z:`.
   - **Folder:** `\\LAPTOP-ABC\Calyx` (use the laptop’s hostname) or `\\192.168.1.10\Calyx` (use its IP if name resolution fails).
   - Check **Reconnect at sign-in** if you want it permanent.
   - Finish (enter laptop credentials if prompted).

2. **Use the shared repo**
   - From here you can open **Z:\** (or whatever letter you chose) and work in **Z:\** as the Calyx repo: edit, run scripts, git, etc.
   - You can run the laptop’s signing script from the share, e.g.:
     ```powershell
     powershell -NoProfile -ExecutionPolicy Bypass -File Z:\tools\calyx_sign.ps1 -Receipt Z:\governance\approvals\some_receipt.json
     ```
   - **Important:** `calyx_sign` and diskpart/ssh-keygen run **on this PC**. The USB key (VHDX) must be on this PC. The receipt and script can live on the share; the key stays local.

## Operating from both codebases

- **This PC:** repo at `C:\Calyx_Terminal` (this repo). Use `.\tools\calyx_sign.ps1` and `.\governance\approvals\...` here.
- **Laptop share on this PC:** repo at `Z:\Calyx` (or your drive letter). Use `Z:\tools\calyx_sign.ps1` and paths under `Z:\` for receipts/approvals when you want to work against the laptop’s Calyx tree.
- **Sync:** Keep repos in sync via git (push from one, pull on the other) or by working mainly on the share so there’s one copy. If both are git clones, you can add the other as a remote and push/pull as needed.

## Caveats

- **diskpart / VHD:** The script that runs on this PC looks for the VHDX on **this** machine’s drives (e.g. E:). It does not use paths on the network share for the VHD; only the receipt (and script) can be on the share.
- **Latency:** Editing and building on a network path can be slower than local; for heavy use, clone the repo locally and sync via git.
- **Laptop must be on:** The share is only available when the laptop is on and on the same network.
