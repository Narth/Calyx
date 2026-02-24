# Telemetry recap and systems confirmation — for CGPT awareness and commit

**Purpose:** Give CGPT (and any other participant) a single telemetry recap and systems confirmation before we attempt the CBO sponsorship Calyx Sign. This receipt is for awareness and commit; it does not replace the Architect-signed approval artifact.

**Date (UTC):** 2026-02-24  
**Scope:** Station Calyx (desktop node), laptop node (Calyx share), Calyx Sign ceremony, CBO sponsorship policy.

---

## Systems confirmed

| System | Status | Notes |
|--------|--------|------|
| **Desktop node (Calyx_Terminal)** | OK | Repo root: `C:\Calyx_Terminal`. STATE.md: maintenance; checks dev_harness=ok, cbo_core=ok, avatar_web=ok, telemetry_gateway=ok. |
| **Laptop node (Calyx share)** | OK | Share live as **Z:\** on desktop; laptop repo at `C:\Calyx` (original). Two-node comparison script and implementation path doc in place. |
| **Calyx Sign (desktop)** | Ready | `tools\calyx_sign.ps1` v1.2.0 on desktop: ceremony works; fixes for SIGN captcha, diskpart path, already-attached, V: visibility; pre-check and hints for Admin vs non-Admin. |
| **Calyx Sign (laptop)** | Available | Script at `C:\Calyx\tools\calyx_sign.ps1` (and at `Z:\tools\calyx_sign.ps1` when Z: mapped). Laptop-side capture via automated prompt is feasible (see docs/operations/CALYX_SIGN_LAPTOP_CAPTURE_FEASIBILITY.md). |
| **Sponsorship policy** | Draft | `governance/approvals/cbo_sponsorship_research_test_improve.policy.md`; approval artifact `cbo_sponsorship_research_test_improve.approval.json` (unsigned). Awaiting Architect signature → `.approval.json.sig`. |
| **Governance** | Aligned | Architect Approval Contract: human-only signatures; Calyx Sign CBO Sponsorship doc; STATE.md “Forbidden (until Calyx Sign)” references sponsorship. |

---

## Telemetry recap (recent)

- **Calyx Sign on desktop:** Reproduced `tools\calyx_sign.ps1`; fixed diskpart “fully qualified” path (WriteAllLines, no quotes); added “already attached” handling and skip detach when user pre-mounted; fixed ssh-keygen seeing V: (Start-Process cmd with WorkingDirectory = key dir); clarified SIGN captcha; pre-check and non-Admin hint; error message improvements (empty exit code, laptop capture).
- **Two-node:** `Scripts\compare_calyx_nodes.ps1` added; `docs/operations/CALYX_TWO_NODE_IMPLEMENTATION_PATHS.md` and `SHARE_CALYX_REPO_LAPTOP_TO_PC.md` in place.
- **Intent:** About to attempt CBO sponsorship sign (desktop and/or laptop). Considering laptop-side capture via automated prompt (feasible within governance).

---

## For CGPT — awareness and commit

- **Acknowledge:** This recap and systems confirmation reflect current state as of the date above.
- **Commit:** You can treat this document as the telemetry recap and systems confirmation for the upcoming sign attempt; no need to re-derive state from prior logs if you have this.
- **Next step:** Architect signs `cbo_sponsorship_research_test_improve.approval.json` (on desktop or laptop); optionally we implement laptop-side prompt + capture/delivery for future runs.

---

*Receipt: telemetry recap and systems confirmation for sign attempt. No secrets. CBO → CGPT.*
