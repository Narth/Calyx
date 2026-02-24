# Calyx Sign — Laptop-side capture: feasibility (before attempt)

**Question:** Can we capture the sign from the laptop via an automated prompt on the laptop?

**Short answer:** **Yes, within governance.** We can automate the **prompt** to the human and the **capture/delivery** of the result after the human signs. We cannot automate the signing itself (passphrase, SIGN confirmation) — that stays human per the Architect Approval Contract.

## What we can do

1. **Automated prompt on the laptop**
   - A script or scheduled task on the laptop that, when run (or when triggered by a shared trigger file / message), displays or sends a clear instruction: e.g. “Sign receipt at `C:\Calyx\governance\approvals\cbo_sponsorship_research_test_improve.approval.json`; when done, the .sig will be at …” or “Run: `powershell -NoProfile -File C:\Calyx\tools\calyx_sign.ps1 -Receipt …`”.
   - So the **prompt** (what to do, which receipt, where the output goes) can be automated; the human still performs the ceremony on the laptop.

2. **Capture/delivery after sign**
   - On the laptop, a **wrapper** around `calyx_sign.ps1` can:
     - Run the ceremony (human inserts key, types SIGN, enters passphrase).
     - On success, copy the `.sig` (and optionally the signing receipt) to a known network location (e.g. `\\DESKTOP\Calyx_Terminal\governance\approvals\` or a shared folder) or commit them to a repo.
   - That way the desktop (or CBO) “captures” the sign by reading the delivered `.sig` without the human manually copying files.

3. **Telemetry / confirmation**
   - The wrapper can write a small “sign complete” receipt (receipt path, .sig path, timestamp, no secrets) to a shared location or channel so CBO/CGPT knows the sign was completed and where to find the `.sig`.

## What we must not do

- **No agent-generated signatures** — CBO or any agent cannot run the private key or produce the `.sig`; only the human on the laptop can.
- **No passphrase derivation or storage** — the human types the passphrase at the laptop; it is never sent or stored.
- **No substituting automation for human approval** — the “SIGN &lt;hash&gt;” confirmation and passphrase entry remain human actions on the laptop.

## Conclusion

**Yes, we can capture the sign from the laptop via an automated prompt there**, in this sense:

- Automate **what** to sign and **where** to put the result (prompt + wrapper).
- Human on the laptop **does** the sign (key, SIGN, passphrase).
- Automate **delivery** of the `.sig` (and optional receipt) to the desktop or shared location so the “capture” is automatic once the human has signed.

Before implementing, we’d define: trigger (e.g. file drop, chat command, run-once script), exact receipt path(s), and the delivery target (UNC path or repo path) so the desktop/CBO can verify and commit the `.sig`.
