Local Owner Confirmation Quickstart

Review the proposal actions and evidence, note the displayed proposal fingerprint (first 8 hex chars of the proposal SHA256). At the local console, type the exact confirmation string shown (e.g., `CONFIRM proposal_fw_context_preserve_enable_001_real ABCD1234`) to record your local owner confirmation. The local confirmation flow writes the approval artifact to `approvals/<proposal_id>.local_owner.json`. This path is for single-host, owner-initiated applies only; Public-profile or multi-host changes are not allowed via this path. After a successful apply (manual, out-of-band), Guardian will still produce full receipts and verification artifacts; rollback requires a separate approved proposal.

Example:

```
# review proposal & evidence
pwsh -File tools\calyx_guardian\local_owner_confirm.ps1 -ProposalPath proposals\fw_context_preserving_enable_real.json
# type: CONFIRM proposal_fw_context_preserve_enable_001_real ABCD1234
```
