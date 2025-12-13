# Demo Safe Boot Contract v1

Scope: Single-command, Safe Mode, deny-all demo for BloomOS kernel + naming rites + assistance intake. No schedulers. No external access. Append-only logging.

Invariants
- safe_mode=true, deny_all=true
- No network or external calls
- No policy mutation
- No schedulers/background loops
- Append-only logs

Allowed operations
- Read local config files
- Write append-only logs
- Prompt human via CLI (interactive)
- Write envelopes/configs to specified paths

Outputs (expected artifacts)
- logs/bloomos/kernel_boot.jsonl (boot events)
- config/naming_rites_v1.json (human-provided naming config)
- logs/governance/naming_rites.jsonl (naming rites audit)
- outgoing/Architect/assist_request_<timestamp>.json (assistance request envelope)
- logs/governance/assist_requests.jsonl (assist request audit)
- reports/demo_safe_boot_run_<boot_id>.md (human-readable summary)

Failure conditions (hard stop)
- safe_mode or deny_all validation fails
- Missing log directories cannot be created
- Naming rites prompt declined or invalid
- Assistance intake not provided (user abort)
