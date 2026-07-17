---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Calyx Sign request method — Invoke a key signature for any task or request

A single entry point to **request** an Architect Calyx Sign: create (or use) an approval receipt and run the sign prompt and ceremony.

## When to use

- Any task or decision that requires an Architect signature (sponsorship, capability unlock, git push, ad‑hoc approval).
- You have a **task id** and a **statement** (what is being approved), or you already have an **approval receipt** file.

## Entry point

**Script:** `Scripts\request_calyx_sign.ps1`
**Repo root:** run from `C:\Calyx_Terminal` (or your repo root).

---

## Option 1: New task (create receipt and sign)

Creates `governance/approvals/<TaskId>.approval.json` and then prompts + runs the sign ceremony.

```powershell
.\Scripts\request_calyx_sign.ps1 -TaskId "my_approval_slug" -Statement "Architect approves X for purpose Y."
```

**Optional:**

- `-Action "calyx_sign_approve"` (default) or another action string.
- `-Scope "scope_slug"` — default is `TaskId`.
- `-CommitHash "abc123..."` — include in receipt; required for SIGN line when signing a commit-bound request.
- `-PolicyPath "governance/policies/foo.md"` — path to policy file; script computes SHA256 and adds `proposal.path` / `proposal.sha256` to the receipt.
- `-Force` — overwrite existing receipt for that `TaskId` without asking.
- `-FromKeyDir` — pass through to `calyx_sign.ps1` (use when key is pre-mounted; run from `V:\calyx_identity` or use the printed FromKeyDir command).
- `-PromptOnly` — only create receipt (if new) and show the sign prompt/commands; do **not** run the ceremony in this session.

**Examples:**

```powershell
# Minimal: task id + statement
.\Scripts\request_calyx_sign.ps1 -TaskId "allow_script_xyz" -Statement "Architect approves running Scripts\xyz.ps1 for one-time migration."

# With commit (e.g. for git-push approval)
.\Scripts\request_calyx_sign.ps1 -TaskId "push_helpingthehelp_20260221" -Statement "Approve push to Helping-the-Help main." -CommitHash "d797a1b2349c1eb905d0dac04d6bab10da6367c0"

# With policy file (SHA256 recorded in receipt)
.\Scripts\request_calyx_sign.ps1 -TaskId "capability_foo" -Statement "Approve capability per policy." -PolicyPath "governance/approvals/capability_foo.policy.md"

# Just create receipt and show commands (no ceremony in this window)
.\Scripts\request_calyx_sign.ps1 -TaskId "future_task" -Statement "Approved." -PromptOnly
```

---

## Option 2: Existing receipt (invoke sign for a known receipt)

Use when the approval receipt already exists (e.g. `cbo_sponsorship_research_test_improve.approval.json`).

```powershell
.\Scripts\request_calyx_sign.ps1 -Receipt ".\governance\approvals\cbo_sponsorship_research_test_improve.approval.json"
```

- Shows the same prompt and command(s) as `prompt_calyx_sign.ps1`.
- Then runs `calyx_sign.ps1` in this session unless you pass `-PromptOnly`.

```powershell
# Prompt only (show what to run, don't run sign here)
.\Scripts\request_calyx_sign.ps1 -Receipt ".\governance\approvals\cbo_sponsorship_research_test_improve.approval.json" -PromptOnly
```

---

## Flow

1. **Resolve receipt:**
   - If `-Receipt`: use that file (must exist).
   - Else: create or reuse `governance/approvals/<TaskId>.approval.json` from `-TaskId`, `-Statement`, and optional `-Action`, `-Scope`, `-CommitHash`, `-PolicyPath`.
2. **Prompt:** run `Scripts\prompt_calyx_sign.ps1` for that receipt (shows commands for default and FromKeyDir).
3. **Ceremony (unless `-PromptOnly`):** run `tools\calyx_sign.ps1` in this session; you type the SIGN line and passphrase.

Result: `<receipt>.sig` next to the receipt and a signing receipt under `governance/receipts/signing/`.

---

## Receipt schema (created by request method)

Generated receipts include at least:

- `proposal_id`, `action`, `scope`, `statement`, `created_utc`
- `signature`: `{ "required": true, "namespace": "calyx", "status": "unsigned", "note": "..." }`

Optional when provided: `commit_hash`, `proposal`: `{ "path", "sha256" }`.

---

## See also

- **Ceremony and flags:** [calyx_sign.md](calyx_sign.md)
- **If sign fails (key not visible, attach issues):** [CALYX_SIGN_RESOLUTION_PATH.md](CALYX_SIGN_RESOLUTION_PATH.md)
- **Prompt only (no request script):** `Scripts\prompt_calyx_sign.ps1 -Receipt <path>`
