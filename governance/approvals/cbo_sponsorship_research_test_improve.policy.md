# CBO Sponsorship — Research, Test, Improve (Station Calyx)

**Proposal ID:** `cbo_sponsorship_research_test_improve`  
**Purpose:** Permissions request so CBO may safely begin researching, testing, and improving Station Calyx processes, workflows, and developments. Communication: explain in current chat; commands and permission authorizations via Discord exec request (OpenClaw).

**Status:** Draft for Architect review and Calyx Sign. Once signed, this policy defines the sponsored scope.

---

## 1. Permissions request (scope)

CBO is requesting sponsorship to:

### 1.1 Research

- **Read, search, list** within the Station Calyx repo: code, docs, scripts, STATE.md, memory (daily notes), runbooks, governance docs (except private keys / identity secrets).
- **Purpose:** Understand processes, workflows, and developments; identify friction and improvement opportunities; answer your questions accurately.
- **No execution:** Research is read-only. No file writes, no script runs, no network outbound beyond already-allowed model APIs and Dev Harness.

### 1.2 Test

- **Propose and run tests** that validate Station Calyx without mutating critical or irreversible state.
- **Allowlisted test actions (when implemented or via exec request):**
  - Run `Scripts\check_calyx_core_services.ps1` (read-only probe).
  - Run `Scripts\build_safety_check.ps1` (read-only hardware/safety check).
  - Run `Scripts\update_state_checks.ps1` (writes only STATE.md `checks` and `heartbeat_ts`).
- **Any other command or script run** that is not in the allowlist above **must** be requested via **Discord exec request (OpenClaw)** so you can approve or deny. CBO will not execute such commands without your authorization through that channel.

### 1.3 Improve

- **Propose and draft improvements:** Edits to docs, scripts, code (in repo), runbooks, and planning artifacts. CBO may draft patches, new files, or changes in the current session (e.g. Cursor) for your review.
- **Application of improvements:**
  - **Edits that CBO can apply under sponsorship (when gates are implemented):** File writes limited to allowlisted paths (e.g. `docs/`, `cbo_hub/` app code, `Scripts/`, `memory/`, `governance/approvals/` for this policy and receipts — **excluding** `governance/identities/` private material and any path containing secrets). No overwrite of existing approval signatures or identity files.
  - **Any command or permission authorization** (e.g. run a script, git commit, push, or write to a path not in the allowlist) **must** be requested via **Discord exec request (OpenClaw)**. CBO will not execute such commands without your authorization.

---

## 2. Communication

- **Explanations and questions:** Any request that needs to be explained, or any question CBO has for you, is done via **the currently available chat** (Discord, Avatar Web Chat, CLI Avatar, or Cursor).
- **Commands and permission authorizations:** Any **command execution** or **permission authorization** that falls outside the narrow allowlist in §1.2 and §1.3 is requested via **Discord exec request via OpenClaw**. CBO will not infer approval from silence; absence of your approval is denial.

---

## 3. Hard limits (no exceptions under this sponsorship)

- **No destructive operations** unless explicitly approved by you (e.g. `rm`, format, bulk delete). Trash/recoverable delete preferred when available.
- **No docker write/exec** unless you explicitly approve via Discord exec or a future signed amendment.
- **No access to or use of** governance private keys, identity secrets, or passphrases. CBO may not generate or substitute Architect signatures.
- **No silent spend:** Any use of paid APIs must remain receipt-backed and visible.
- **No exfiltration of private data** outside the station without your explicit approval.

---

## 4. Escalation

When a decision **truly requires your input or context**, CBO will **not** stamp or execute. CBO will ask you in the current channel (or via Discord if that is the exec channel), state what is needed, and wait for your explicit response. Per `docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md`.

---

## 5. Summary

Under this sponsorship, CBO may:

- **Research** freely (read/search/list) within the repo, excluding identity secrets.
- **Test** using the allowlisted scripts above; any other run is requested via Discord exec (OpenClaw).
- **Improve** by drafting and applying edits to allowlisted paths when implemented; any other command or write is requested via Discord exec (OpenClaw).

Explanations and questions use the current chat. Commands and permission authorizations use the Discord exec request via OpenClaw unless within the allowlist above.

---

---

## How to sign (Architect)

1. Open a terminal in the repo root (`C:\Calyx_Terminal`).
2. **On this node:** Run the Calyx Sign ceremony (USB key + password prompt):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\calyx_sign.ps1 -Receipt .\governance\approvals\cbo_sponsorship_research_test_improve.approval.json
   ```
   Insert the USB key when prompted; enter your passphrase at the `ssh-keygen` prompt. The script creates `.approval.json.sig` and a signing receipt under `governance/receipts/signing/`.
3. **Alternatively** (manual or on laptop): Sign with your Architect key (namespace `calyx`, identity `architect` per `governance/identities/allowed_signers`):
   ```bash
   type governance\approvals\cbo_sponsorship_research_test_improve.approval.json | ssh-keygen -Y sign -f <path-to-your-private-key> -n calyx -I architect -s governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig
   ```
   Or use the laptop script at `C:\Calyx\tools\calyx_sign.ps1` with the same receipt path. See **docs/operations/calyx_sign.md**.
4. Verify (optional): `type governance\approvals\cbo_sponsorship_research_test_improve.approval.json | ssh-keygen -Y verify -f governance\identities\allowed_signers -I architect -n calyx -s governance\approvals\cbo_sponsorship_research_test_improve.approval.json.sig`

Once the `.sig` file exists and verifies, the sponsorship is in effect. CBO will treat it as authority to operate within this policy and to use chat for explanations and Discord exec (OpenClaw) for command/permission authorizations outside the allowlist.
