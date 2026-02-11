# Apply / Dry-Run Checklist — Firewall Profiles Enable (Design-only)

This checklist must be completed and recorded before any apply operation is performed. All items require explicit affirmation by the approver.

- [ ] Proposal reviewed: proposal_id `proposal_fw_profiles_enable_001` and policy `network_steward_firewall_v1`.
- [ ] Evidence hashes verified: confirm evidence raw_hash `284ffff18bb35c6b3099d47f8cfaf84d84f121df8ca1d4571ae306817bf0da53` exists and matches `logs/calyx_guardian/evidence.jsonl`.
- [ ] Impact estimate reviewed: confirm list of potentially affected services (HTTP, SMB, custom ports) and known owners contacted.
- [ ] Maintenance window confirmed or explicitly waived: specify start/end UTC or waived reason.
- [ ] Rollback plan identified: a rollback proposal template exists, and responsible owner is assigned.
- [ ] Verification plan understood: test commands and success criteria documented in proposal verification_plan.
- [ ] Dry-run completed successfully: `proposals/sample_fw_profiles_enabled.diff` reviewed and no unexpected changes observed.
- [ ] Approver explicitly acknowledges: all three acknowledgement statements present in `approvals/proposal_fw_profiles_enable_001.signed.json`.

Record of checklist completion:
- completed_by: <approver name>
- completed_utc: <timestamp>
- notes: <Any additional notes>

NO ACTIONS PERFORMED: This checklist gates a manual apply. Do not run `Set-NetFirewallProfile` or similar without a signed approval artifact and recorded checklist completion.
