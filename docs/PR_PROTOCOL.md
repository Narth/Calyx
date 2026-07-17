# PR Protocol - Code Factory Loop

## Overview

CBO (Code Factory Bot) must always follow this protocol when creating pull requests. All code changes are via PR - no direct merges to main.

## Branch Naming

**Format:** `cbo/<task>/<ts>_<shortid>`

- `cbo/` - Prefix indicating CBO-created branch
- `<task>` - Task type from allowed_tasks (e.g., `lint_fix`, `doc_update`, `refactor_scope`)
- `<ts>` - Timestamp in format `YYYYMMDD_HHMMSS`
- `<shortid>` - Short identifier (first 8 chars of envelope_id or random)

**Examples:**
- `cbo/doc_update/20260217_104522_a1b2c3d4`
- `cbo/lint_fix/20260217_110530_e5f6g7h8`
- `cbo/refactor_scope/20260217_120000_i9j0k1l2`

## Commit Rules

- **Only scoped changes** - commits must align with the task_type and scope defined in the intent envelope
- **Atomic commits** - one logical change per commit
- **Clear messages** - commit messages should reference the envelope_id

**Commit message format:**
```
<task_type>: <brief description> [envelope:<envelope_id>]

<optional detailed description>
```

## PR Template Requirements

Every PR must include:

### 1. Intent Envelope ID
- Reference to the envelope_id that triggered this PR
- Link to envelope file in `telemetry/outbox/intents/`

### 2. Contract Risk Tier
- Risk tier determined: `low`, `med`, or `high`
- Rationale for risk tier assignment

### 3. Required Checks List
- List of CI checks that must pass based on risk tier
- Reference to `CALYX_CONTRACT.yaml` required_ci_checks section

### 4. Receipts/Manifests
- Links to receipt files in `runtime/receipts/`
- Link to run manifest in `runtime/manifests/`
- SHA256 hashes of key artifacts

### 5. Rollback Plan (if applicable)
- For `high` risk or `refactor_scope` tasks
- Steps to revert changes if needed
- Affected files list

## PR Creation Process

1. **Create branch** using naming convention
2. **Make commits** following commit rules
3. **Open PR** using GitHub PR template (`.github/pull_request_template.md`)
4. **Fill all required fields** in template
5. **Wait for CI** to run required checks
6. **Address any failures** before requesting review

## Risk Tier Determination

Risk tier is determined by:
- Diff paths (governance/policy = high)
- Dependency file changes (med)
- Task type (some types default to med/high)
- Explicit approval requirements

See `CALYX_CONTRACT.yaml` risk_rules section for details.

## Required CI Checks by Risk Tier

### Low Risk
- Lint
- Unit tests
- Schema validation

### Med Risk
- All low risk checks +
- Harness lane(s) relevant to task
- Receipt presence check

### High Risk
- All med risk checks +
- Mandatory human approval marker
- Extra regression suite

## Approval Requirements

- **Low/Med risk:** Automated checks must pass
- **High risk:** Requires explicit human approval token in envelope + PR approval
- **Policy/governance changes:** Always require approval token

## Stop Conditions

If any stop condition is triggered, PR creation is halted and alert sent to `#cbo-alerts`:
- Tool surface expansion beyond contract
- Policy/governance edit without approval token
- Secrets detected in diff
- Non-deterministic results for determinism-required tasks
- Unknown tool invocation
- Unknown envelope source

## Receipt Requirements

Each PR must produce:
- Contract SHA256 (from `CALYX_CONTRACT.yaml`)
- Run manifests (from `runtime/manifests/`)
- Result JSONL paths (from `runtime/benchmarks/results/`)
- Hub runner receipts (from `runtime/receipts/hub_runner__*.jsonl`)

## Examples

### Example PR Title
```
[doc_update] Update PR_PROTOCOL.md [envelope:a1b2c3d4-e5f6-7890-abcd-ef1234567890]
```

### Example PR Description
```markdown
## Intent Envelope
- **Envelope ID:** `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- **Envelope Path:** `telemetry/outbox/intents/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`

## Contract Risk Tier
- **Risk Tier:** `low`
- **Rationale:** Only documentation files changed, no dependency changes, no governance touches

## Required Checks
- [x] Lint
- [x] Unit tests
- [x] Schema validation

## Receipts/Manifests
- **Contract SHA256:** `e86d8c6c30629645f1cd602fb78f1efdd906283268c43baf62e63271c6e158e2`
- **Run Manifest:** `runtime/manifests/doc_update_a1b2c3d4_20260217_104522_manifest.json`
- **Hub Runner Receipt:** `runtime/receipts/hub_runner__20260217_104522.jsonl`

## Rollback Plan
N/A - Low risk documentation change
```
