# Chronicle Vault Quarantine (WO_CHRONICLE_VAULT_QUARANTINE_V1)

WARNING: Vault content is NOT Station context.

## Contract Summary
The Chronicle Vault preserves ChatGPT export backups without allowing execution,
policy mutation, or task intake. Vault contents are non-executable and must not
be ingested by any pipeline, loader, or context system.

## Deny Rules
- No task intake or routing from vault content
- No tool activation from vault content
- No policy or governance mutation based on vault content
- Promotion requires an ARCHIVE_CONSENT receipt

## Vault Root (this machine)
D:\\Calyx_Data\\Calyx_Archive

## Directory Contract
<VAULT_ROOT>/chatgpt_exports/<YYYY-MM>/
- raw/
- derived/
- ledger/

## Promotion Gate
Allowed promotions only:
- raw -> derived (redacted)
- derived -> chronicles (curated excerpts)

### ARCHIVE_CONSENT Receipt Schema
{
  "receipt_type": "ARCHIVE_CONSENT",
  "ts": "YYYY-MM-DDThh:mm:ssZ",
  "actor": "<human operator>",
  "source": {
    "vault_path": "<VAULT_ROOT>/chatgpt_exports/<YYYY-MM>/raw/<file>",
    "sha256": "<hex>"
  },
  "allowed_actions": ["raw_to_derived", "derived_to_chronicles"],
  "constraints": [
    "no tool activation",
    "no policy mutation",
    "no task intake",
    "redaction required"
  ],
  "note": "<free text>"
}

## Scanner Deny Hints
- Exclude VAULT_ROOT from any scanners, loaders, and CI hygiene checks
- Never add VAULT_ROOT to git
