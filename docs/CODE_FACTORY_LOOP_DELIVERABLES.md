# Code Factory Loop + Discord Hub + Federated Ops v0 - Deliverables Receipt

## Summary

Implementation of minimal "one loop" system:
- Human intent arrives via Discord
- Intent becomes signed/validated envelope stored in repo/telemetry outbox
- Desktop hub picks up envelopes and executes only allowed tasks
- Code changes become branches + PRs
- Repo CI enforces risk-aware gates
- Review step produces evidence-based validation

## Deliverables Checklist

### 1. CALYX_CONTRACT.yaml
- **Path:** `CALYX_CONTRACT.yaml`
- **SHA256:** `e86d8c6c30629645f1cd602fb78f1efdd906283268c43baf62e63271c6e158e2`
- **What Changed:** Created contract with tool allowlist, risk tiers (low/med/high), required CI checks by risk tier, required receipts by task type, stop conditions, tool surface allowlist by task, envelope source allowlist, determinism requirements
- **How to Run:** N/A (configuration file)
- **Desktop:** Contract must exist and be valid for any execution
- **Laptop:** N/A (Phase A only)

### 2. INTENT_ENVELOPE_SCHEMA_v0.1.json
- **Path:** `telemetry/envelopes/INTENT_ENVELOPE_SCHEMA_v0.1.json`
- **SHA256:** `7b89dcc0a2ac16346306cc36e566a3058b218a1140bd58b1c5bea9d028a7f86c`
- **What Changed:** Created JSON Schema for incoming directives (intent envelopes) with required fields: envelope_id, ts_utc, source, author, channel_id, message_id, intent, task_type, risk_hint, scope, constraints, requires_human_approval, approval_token, evidence_requirements, signature
- **How to Run:** N/A (schema file)
- **Desktop:** Used by Discord intake and hub runner for validation
- **Laptop:** Will be used in Phase B for envelope creation

### 3. Discord Intake Adapter
- **Path:** `calyx/cbo/discord_intake.py`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **Config:** `runtime/discord_config.json`
- **What Changed:** Implemented Discord intake adapter that reads messages from approved channels, converts to intent envelopes, validates against schema, writes to `telemetry/outbox/intents/`. No direct execution - Discord is a mailbox only.
- **How to Run:**
  - **Desktop:** 
    ```bash
    # Set environment variable
    export DISCORD_BOT_TOKEN=your_token_here
    
    # Run intake adapter
    python -m calyx.cbo.discord_intake --config runtime/discord_config.json --repo-root .
    
    # Or start bot (requires discord.py):
    python -m calyx.cbo.discord_intake
    ```
  - **Laptop:** N/A (Phase A - Discord → Desktop only)
- **Receipts:** Writes to `runtime/receipts/discord_intake__*.jsonl`

### 4. Desktop Hub Runner
- **Path:** `benchmarks/harness/hub_runner.py`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **What Changed:** Created hub runner that watches `telemetry/outbox/intents/`, validates envelopes against contract, resolves task_type to deterministic task plan, executes via approved harness mechanisms. Default deny for unknown task_type, missing scope, high risk without approval, schema failures, policy/governance touches without approval.
- **How to Run:**
  - **Desktop:**
    ```bash
    # Run once (process all pending envelopes)
    python -m benchmarks.harness.hub_runner --repo-root . --contract CALYX_CONTRACT.yaml
    
    # Watch mode (future - not implemented yet)
    python -m benchmarks.harness.hub_runner --watch
    ```
  - **Laptop:** N/A (Desktop only executor)
- **Receipts:** Writes to `runtime/receipts/hub_runner__*.jsonl`
- **Manifests:** Writes to `runtime/manifests/<run_id>_manifest.json`
- **Results:** Writes to `runtime/benchmarks/results/<task_type>/<run_id>.jsonl`

### 5. PR Protocol Documentation
- **Path:** `docs/PR_PROTOCOL.md`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **What Changed:** Created PR protocol documentation describing branch naming (`cbo/<task>/<ts>_<shortid>`), commit rules, PR template requirements, risk tier determination, required CI checks by risk tier, approval requirements, stop conditions, receipt requirements
- **How to Run:** N/A (documentation)
- **Desktop:** CBO must follow this protocol when creating PRs
- **Laptop:** N/A (Phase A - no laptop PRs)

### 6. GitHub PR Template
- **Path:** `.github/pull_request_template.md`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **What Changed:** Created GitHub PR template enforcing structure: intent envelope ID, contract risk tier, required checks list, receipts/manifests, rollback plan
- **How to Run:** N/A (GitHub template)
- **Desktop:** Auto-populated when CBO creates PR
- **Laptop:** N/A

### 7. CI Workflows (Risk-Based Gates)
- **Path:** `.github/workflows/code_factory_gates.yml`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **Supporting Scripts:**
  - `.github/scripts/determine_risk_tier.py`
  - `.github/scripts/check_receipts.py`
  - `.github/scripts/check_approval_token.py`
  - `.github/scripts/validate_schemas.py`
  - `.github/scripts/validate_contract_hash.py`
  - `.github/scripts/generate_ci_receipt.py`
- **What Changed:** Created GitHub Actions workflow that enforces risk tier determination, required checks by risk tier (low/med/high), receipt validation, secret scanning, CI receipt generation
- **How to Run:** 
  - **Desktop:** Automatically runs on PR creation/update
  - **Laptop:** N/A (CI runs on GitHub)
- **Receipts:** CI receipts written to `runtime/receipts/ci_receipt__*.json`

### 8. Review Agent Stub
- **Path:** `benchmarks/harness/review_agent.py`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **What Changed:** Created review agent that does NOT approve, only summarizes: blast radius, suspicious tests, policy violations, missing evidence. Wired as report generator for CI, can post as PR comment or write to artifacts.
- **How to Run:**
  - **Desktop:**
    ```bash
    # Generate report
    python -m benchmarks.harness.review_agent \
      --repo-root . \
      --envelope telemetry/outbox/intents/<envelope_id>.json \
      --diff-paths path1 path2 \
      --output runtime/receipts/review_report.json
    
    # Output as PR comment
    python -m benchmarks.harness.review_agent \
      --envelope telemetry/outbox/intents/<envelope_id>.json \
      --diff-paths path1 path2 \
      --pr-comment
    ```
  - **Laptop:** N/A (Desktop only)
- **Receipts:** Review reports written to `runtime/receipts/review_report.json`

### 9. Federated Ops Roadmap
- **Path:** `docs/FEDERATED_OPS_ROADMAP_v0.md`
- **SHA256:** (see runtime/receipts/deliverables_receipt__*.json)
- **What Changed:** Documented Phase A (Discord → Desktop Hub, current) and Phase B (Laptop → Desktop Directives, future). Includes validation metrics, prerequisites, architecture, security considerations, migration path.
- **How to Run:** N/A (documentation)
- **Desktop:** Phase A active, Phase B roadmap for future
- **Laptop:** Phase B roadmap for future implementation

## Receipts Generated

All component initialization receipts:
- `runtime/receipts/contract_init__<ts>.json` - Contract initialization
- `runtime/receipts/envelope_schema_init__<ts>.json` - Schema initialization
- `runtime/receipts/deliverables_receipt__<ts>.json` - All deliverables with SHA256 hashes

## Directory Structure Created

```
runtime/
├── receipts/          # All receipts (contract, schema, intake, runner, CI)
├── manifests/         # Run manifests with artifact hashes
└── benchmarks/
    └── results/       # Task execution results by task_type

telemetry/
├── envelopes/         # Schema definitions
└── outbox/
    └── intents/       # Incoming intent envelopes

.github/
├── workflows/         # CI workflows
│   └── code_factory_gates.yml
└── scripts/           # CI helper scripts
    ├── determine_risk_tier.py
    ├── check_receipts.py
    ├── check_approval_token.py
    ├── validate_schemas.py
    ├── validate_contract_hash.py
    └── generate_ci_receipt.py

calyx/cbo/
└── discord_intake.py  # Discord intake adapter

benchmarks/harness/
├── hub_runner.py      # Desktop hub runner
└── review_agent.py   # Review agent stub

docs/
├── PR_PROTOCOL.md                    # PR protocol documentation
└── FEDERATED_OPS_ROADMAP_v0.md      # Federated ops roadmap
```

## Stop Conditions Implemented

All stop conditions from contract are enforced:
1. Tool surface expansion beyond contract → halt + alert #cbo-alerts
2. Policy/governance edit without approval token → halt + alert
3. Secrets detected in diff → halt + alert (via gitleaks in CI)
4. Non-deterministic results → halt + alert
5. Unknown tool invocation → halt + alert
6. Unknown envelope source → halt + alert

## Next Steps

1. **Configure Discord Bot:**
   - Set `DISCORD_BOT_TOKEN` environment variable
   - Update `runtime/discord_config.json` with channel allowlist
   - Enable intake: `"intake_enabled": true`

2. **Test Discord Intake:**
   - Send test message to approved channel
   - Verify envelope created in `telemetry/outbox/intents/`
   - Check receipt in `runtime/receipts/discord_intake__*.jsonl`

3. **Test Hub Runner:**
   - Run hub runner: `python -m benchmarks.harness.hub_runner`
   - Verify envelope processed
   - Check receipts and manifests

4. **Phase A Validation:**
   - Run for 1-2 weeks
   - Collect metrics: parse_success_rate, deny_rate, unknown_task_type_rate, containment_anomalies (must be 0), determinism_hash_stability
   - Document in `runtime/metrics/phase_a_validation.json`

5. **Phase B (Future):**
   - Only after Phase A validation complete
   - Implement laptop envelope signing
   - Add node allowlist to contract
   - Enable signature validation

## Hard Rules Enforced

- ✅ Contract must exist and be valid for execution
- ✅ Default deny for unknown task_type, missing scope, high risk without approval
- ✅ No direct execution from Discord (mailbox only)
- ✅ All execution via hub runner with contract validation
- ✅ No direct merges to main (PR only)
- ✅ All actions produce receipts
- ✅ Stop conditions halt and alert
