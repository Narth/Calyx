# Governance Ticket: Enable Windows Firewall Profiles (Design-only)

- Proposal ID: `proposal_fw_profiles_enable_001`
- Policy ID: `network_steward_firewall_v1`
- Correlation ID: `d2f87a5b9e1a` (parent: `972bbb9fd057`)

Status
- No action has been taken. This ticket is for human review only.
- Approval is required to proceed.

---

## 1) What was observed

During Night Watch and an elevated Phase 0 run (correlation `d2f87a5b9e1a`), the collector observed that all Windows Firewall profiles on the target host are disabled. Evidence excerpt and full raw record are available under `logs/calyx_guardian/evidence.jsonl` (example raw_hash: `284ffff18bb35c6b3099d47f8cfaf84d84f121df8ca1d4571ae306817bf0da53`).

## 2) Why this matters

Firewall profiles (Domain, Private, Public) control host-level inbound/outbound filtering. If profiles are disabled, the host may accept inbound connections without host-based filtering, increasing exposure to network threats and lateral movement.

## 3) What would change (summary)

If this proposal is applied, the host will have its Windows Firewall profiles set to Enabled for Domain, Private, and Public. No firewall rules will be added, removed, or modified — only the profile "Enabled" flags will be turned on. Example command (not executed here):

`Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True`

This is a dry-run proposal: `proposals/sample_fw_profiles_enabled.diff` contains a human-readable preview of the change.

## 4) What could break

Potential service disruptions if services were intentionally exposed without corresponding allow rules. Examples include:
- Local HTTP servers (ports 80/443) that expect inbound access
- Custom application listeners bound to 0.0.0.0
- File shares (SMB) or other infrastructure services
- Remote admin tools relying on permissive settings

Impact estimate and affected-services checklist included in `proposals/sample_fw_profiles_enabled.json`.

## 5) What will not change

- No firewall rule modifications are proposed.
- No network routes, NAT, or upstream appliance policies are changed.
- No automatic remediation or rollback will occur without a separate, signed proposal and approval.

## 6) What evidence supports this

- Evidence record (Get-NetFirewallProfile) in `logs/calyx_guardian/evidence.jsonl` raw_hash: `284ffff18bb35c6b3099d47f8cfaf84d84f121df8ca1d4571ae306817bf0da53` (timestamp present in the proposal). See `logs/calyx_guardian/firewall_evidence_excerpt.md` for the quoted record.
- Elevated run receipt and proof: `logs/calyx_guardian/elevation_receipt.json` (correlation: `d2f87a5b9e1a`) and `logs/calyx_guardian/elevation_status.json` (shows `is_admin:true`).
- Normalized findings: `logs/calyx_guardian/findings.json` includes `firewall.disabled` with `confidence_score: 0.85`.

## 7) What decision is required

Please review the attached proposal, diff, evidence, and checklist. Approve or reject the proposal. If you approve, please sign the approval artifact at `approvals/proposal_fw_profiles_enable_001.signed.json` and confirm the apply checklist at `checklists/apply_dry_run_checklist.md` before running the apply step (manual, out-of-band).

- Decision options:
  - Approve: Sign approval artifact and schedule apply during a maintenance window.
  - Reject: Close the proposal and document rationale.
  - Defer: Request additional evidence or a more targeted change (e.g., enable only specific profiles).

## 8) Links and artifacts (design-only)

- Proposal JSON: `proposals/sample_fw_profiles_enabled.json`
- Proposal diff (what-would-change): `proposals/sample_fw_profiles_enabled.diff`
- Approval template: `approvals/proposal_fw_profiles_enable_001.signed.json`
- Apply/Dry-Run Checklist: `checklists/apply_dry_run_checklist.md`
- Evidence excerpt: `logs/calyx_guardian/firewall_evidence_excerpt.md`
- SVF brief: `logs/calyx_guardian/svf_firewall_disabled.md`
- Findings: `logs/calyx_guardian/findings.json`
- Elevated run receipt: `logs/calyx_guardian/elevation_receipt.json`
- Elevated run elevation status: `logs/calyx_guardian/elevation_status.json`

---

Audit & Traceability
- All artifacts include correlation IDs and are recorded in the orchestrator log stream (`logs/orchestrator/orchestrator_log.jsonl`).
- No action will be performed until a signed approval artifact and completed checklist are present.

Prepared by: Guardian System (design-only)

