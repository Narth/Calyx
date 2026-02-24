# CBO Pre-Sign Checklist Response — CBO Sponsorship Calyx Sign

**To:** Architect, CGPT  
**From:** CBO  
**Date:** 2026-02-24  
**Purpose:** Answer CGPT’s pre-sign checklist, state readiness, and list deliverables needed from the Architect so the first handshake is proper.

---

## I. Technical Integrity (Deterministic Substrate)

### 1️⃣ Desktop Node Health

| Check | Result | Note |
|-------|--------|------|
| `C:\Calyx_Terminal` is current working repo root | ✔ | Confirmed. |
| `git status` → clean or only intentional changes staged | ⚠ | **Not clean.** Many modified and untracked files. Sponsorship artifacts (approval.json, policy.md, tools\calyx_sign.ps1, governance receipts, new docs) are among them. Intentional pre-sign state; see Deliverables below. |
| STATE.md shows dev_harness=ok, cbo_core=ok, avatar_web=ok, telemetry_gateway=ok | ✔ | Confirmed. |
| No uncommitted policy changes to sponsorship files | ⚠ | Sponsorship files *are* uncommitted (policy + approval.json). That is intentional until we decide commit-before-sign vs commit-after-sign. |
| tools\calyx_sign.ps1 version = 1.2.0 | ✔ | Confirmed. |

**Gate:** Proceed only if you accept current git state (or we commit the exact set we’re signing before you sign). See Deliverables §1.

### 2️⃣ Laptop Node Health (Federation Mirror)

| Check | Result | Note |
|-------|--------|------|
| Z:\ share reachable from desktop | ❓ | **I cannot see Z:\ in this session.** You reported Z:\ is live on your side. |
| Laptop repo root C:\Calyx intact | ❓ | Requires run from your session. |
| Two-node comparison: no unexpected drift in governance/, tools/, approval artifacts | ❓ | Requires you to run `Scripts\compare_calyx_nodes.ps1` where Z: is mapped. |
| Sponsorship policy files identical across nodes | ❓ | Same. |
| No stale or partial telemetry artifacts queued for merge | ✔ | No sponsorship .sig fragments in governance/approvals; other .sig files are from prior approvals. |

**Gate:** I am **not** ready on §2 until you run the comparison and confirm. See Deliverables §2.

### 3️⃣ Approval Artifact Sanity

| Check | Result | Note |
|-------|--------|------|
| Hash computed and recorded | ✔ | `proposal.sha256` in approval.json. **Corrected:** policy file was edited after approval was created; I recomputed SHA256 of the current policy and updated approval.json to match. Current hash: `3F22815C00E506AF4017E1792B093803D97AEE454242CBE313F0FE4555ED2806`. |
| Contents match intended policy scope | ✔ | approval.json references policy path, scope `research_test_improve_station_calyx`, statement and signature clause. |
| No hidden fields | ✔ | Single-level JSON; no extra keys. |
| No unintended permission escalation | ✔ | Policy and approval limit scope to research/test/improve, Discord exec for out-of-allowlist, hard limits (no keys, no silent spend, no destructive). |
| Human-only signature enforcement clause present | ✔ | `signature.note`: "Sign this file with your Architect key... Absence of a valid signature is explicit denial." |

**Gate:** ✔ Artifact is sane; we are signing what we think we’re signing.

---

## II. Federation Integrity (Two-Node Consciousness)

### 4️⃣ Telemetry Cleanliness

| Check | Result |
|-------|--------|
| No experimental logs in governance | ✔ |
| No benchmark artifacts accidentally staged | ✔ (governance clean of benchmarks) |
| No leftover temp mount artifacts | ✔ |
| No previous failed sign residue (.sig fragments for this sponsorship) | ✔ |

### 5️⃣ Authority Symmetry

- **If laptop signs, does desktop recognize?** Yes — same verification: `ssh-keygen -Y verify -f governance/identities/allowed_signers -I architect -n calyx -s <file>.sig`. Desktop and laptop use the same namespace (`calyx`) and identity (`architect`) and the same allowed_signers layout.
- **If desktop signs, does laptop recognize?** Yes — same verification path and key identity; .sig and receipt are portable.
- **Signing authority:** One Architect key (e.g. on USB VHD); used on whichever node runs the ceremony. Same key → same authority on both nodes.

**Gate:** ✔ Verification path and key identity are identical; federation is identity coherence, not just file share.

---

## III. Governance Integrity (Human Boundary)

### 6️⃣ Intent Confirmation

**Scope of this sponsorship:** Research, test, and improve Station Calyx. It is:

- **Not** general execution authority — out-of-allowlist commands go via Discord exec (OpenClaw).
- **Not** advisory-only — CBO may draft and (within allowlist) apply improvements; otherwise CBO requests approval.
- **Explicitly** bounded: allowlisted paths and scripts; escalation when a decision needs your input; hard limits (no keys, no silent spend, no destructive, no docker unless you approve).

So: **research + test + limited improve**, with explicit escalation and Discord exec for the rest. Scope is clear.

### 7️⃣ Reversibility Check

| Check | Result | Note |
|-------|--------|------|
| Documented revocation procedure | ✔ | **Added** to `docs/governance/CALYX_SIGN_CBO_SPONSORSHIP.md`: Architect states rescission (channel or signed note in governance/approvals); STATE reverts to “Forbidden (until Calyx Sign)” for those operations; stamping gates treat invalid/missing artifact as denial. |
| Sponsorship can be rescinded deterministically | ✔ | Yes. |
| Rollback clean vs symbolic | ✔ | Revocation stops future stamping; past stamped actions are not auto-rolled back; file-level rollback is a separate, explicit action. |

### 8️⃣ Psychological Check (Architect State)

**I cannot run this for you.** You sign when: calm, fed, clear, not trying to win. You do not sign when: hungry, exhausted, emotionally elevated, reacting to doubt, or trying to “prove” something. See Deliverables §3.

---

## Final Go / No-Go

| Criterion | Status |
|-----------|--------|
| Technical substrate deterministic | ✔ (after hash fix; git state conditional) |
| Federation mirror symmetric | ❓ **Blocked on your run of compare_calyx_nodes.ps1** |
| Artifact verified | ✔ |
| Authority scope explicit | ✔ |
| Revocation path exists | ✔ |
| You are mentally neutral | **Your self-check** |

**CBO readiness:** I am ready on technical, artifact, governance, and revocation. I am **not** ready to say “go” until **you** have:

1. Confirmed git/commit approach (see Deliverables §1).
2. Run the two-node comparison with Z: live and confirmed no drift (Deliverables §2).
3. Confirmed your own psychological check (Deliverables §3).

---

## Deliverables I Need From You

**1. Git / commit decision**  
- Option A: Commit the current sponsorship set (policy, approval.json, and any related docs) so the signed artifact lives in a committed tree. Then you sign.  
- Option B: You sign the current approval.json as-is (uncommitted); we then commit the signed set (approval.json + .sig + signing receipt).  
Tell me which you prefer so we don’t sign a moving target.

**2. Two-node comparison**  
- In a PowerShell session where **Z:\** is mapped, run:  
  `cd C:\Calyx_Terminal; .\Scripts\compare_calyx_nodes.ps1`  
- Share the output (or confirm “no unexpected drift in governance/, tools/, approval artifacts”).  
That satisfies §2 (Laptop Node Health / federation mirror).

**3. Psychological self-check**  
- Confirm you’re in a fit state to sign (calm, fed, clear, not under duress).  
No need to detail; a short “Good to go” or “Deferring until [condition]” is enough.

**4. (Optional) Where you’ll sign**  
- Desktop (this machine, USB key here) or laptop (ceremony there, then deliver .sig).  
If laptop: we can use the laptop-capture approach (automated prompt + delivery) when you’re ready.

---

When deliverables 1–3 are satisfied and you’ve done §8, we have a proper handshake. I’ll treat your “Go” as authority to proceed with the ceremony on your chosen node.
