# Federated Ops Roadmap v0

## Overview

Federated Ops enables multiple nodes (Desktop, Laptop) to coordinate via envelope-based directives. Desktop remains the sole executor for resource-intensive tasks.

## Phase A: Discord → Desktop Hub (CURRENT)

### Status: Implementation Complete, Validation Required

### Architecture
- **Discord** → Intake Adapter → `telemetry/outbox/intents/` → Desktop Hub Runner → Execution
- Only desktop executes envelopes
- Laptop does not execute hub tasks

### Components
1. **Discord Intake Adapter** (`calyx/cbo/discord_intake.py`)
   - Reads messages from approved channels
   - Converts to intent envelopes
   - Validates against schema
   - Writes to `telemetry/outbox/intents/`

2. **Desktop Hub Runner** (`benchmarks/harness/hub_runner.py`)
   - Watches `telemetry/outbox/intents/`
   - Validates against `CALYX_CONTRACT.yaml`
   - Executes tasks via approved harness mechanisms
   - Emits receipts and manifests

### Validation Metrics (1-2 weeks or N runs)

Must track and validate:

1. **parse_success_rate** (envelopes)
   - Percentage of Discord messages successfully converted to valid envelopes
   - Target: >95%

2. **deny_rate reasons distribution**
   - Breakdown of denial reasons:
     - Invalid task_type
     - Missing scope
     - High risk without approval
     - Schema validation failure
     - Policy/governance touch without approval
   - Track distribution to identify common issues

3. **unknown_task_type_rate**
   - Percentage of envelopes with task_type not in allowed_tasks
   - Target: 0% (all should be validated at intake)

4. **containment anomalies**
   - Any execution outside allowed tool surface
   - Any execution without proper validation
   - Target: 0 (hard requirement)

5. **determinism hashes stable for repeated intents**
   - Same intent + same seed → same determinism hash
   - Target: 100% consistency

### Validation Period
- **Duration:** 1-2 weeks OR N runs (whichever comes first, minimum 10 runs)
- **Success Criteria:**
  - All metrics meet targets
  - Zero containment anomalies
  - Stable determinism hashes
  - No stop conditions triggered

### Metrics Collection

Metrics should be collected in:
- `runtime/metrics/phase_a_validation.json`
- Updated after each envelope processing
- Includes all 5 metrics above

## Phase B: Laptop → Desktop Directives (FUTURE)

### Prerequisites
- Phase A validation complete and stable
- All Phase A metrics meet targets
- Zero containment anomalies for validation period

### Architecture
- **Laptop** → Local Envelope Creation → Signed Envelope → `telemetry/outbox/intents/` → Desktop Hub Runner → Execution
- Desktop accepts only if:
  - Signature valid
  - Node ID matches allowlist
  - Envelope passes all Phase A validations

### Implementation Requirements

1. **Laptop Node Identity**
   - Laptop must have node identity (if identity system exists)
   - Node ID must be in desktop's allowlist
   - Identity stored in `runtime/node_id.txt` (already exists for laptop)

2. **Envelope Signing**
   - Laptop produces envelopes locally
   - Envelopes signed with laptop node identity
   - Signature validation on desktop

3. **Desktop Acceptance Rules**
   - Signature validation required
   - Node ID must match allowlist in `CALYX_CONTRACT.yaml`
   - All Phase A validations still apply
   - Desktop remains sole executor for "resource intensive" tasks

4. **Hard Rule: No Direct Shell Commands**
   - **NO** "laptop triggers desktop shell commands" directly
   - **MUST** be: envelope → outbox → hub runner → bounded task
   - All execution goes through hub runner with contract validation

### Node Allowlist

Add to `CALYX_CONTRACT.yaml`:
```yaml
allowed_nodes:
  phase_b:
    - calyx_laptop_01  # Node ID from runtime/node_id.txt
    # Add more nodes as needed
```

### Security Considerations

1. **Signature Validation**
   - Envelopes must be signed with valid node identity
   - Desktop must verify signature before processing
   - Invalid signatures → deny and alert

2. **Node ID Verification**
   - Node ID must match allowlist
   - Unknown node IDs → deny and alert
   - Alert sent to `#cbo-alerts`

3. **Rate Limiting**
   - Consider rate limits per node
   - Prevent envelope flooding

4. **Audit Trail**
   - All laptop-originated envelopes logged
   - Receipts include node_id
   - Manifests track node origin

## Migration Path: Phase A → Phase B

1. **Complete Phase A Validation**
   - Run for 1-2 weeks
   - Collect all metrics
   - Verify zero containment anomalies

2. **Review Metrics**
   - Human review of Phase A metrics
   - Confirm all targets met
   - Document any issues

3. **Enable Phase B (Gradual)**
   - Add laptop node to allowlist
   - Enable signature validation
   - Start with low-risk tasks only
   - Monitor closely

4. **Full Phase B**
   - After successful low-risk validation
   - Enable all task types
   - Continue monitoring

## Stop Conditions (Apply to Both Phases)

If any of these occur, halt processing and post to `#cbo-alerts`:

1. Tool surface expansion beyond contract
2. Policy/governance edit without explicit approval token
3. Secrets detected in repo diff
4. Non-deterministic results for determinism-required task
5. Unknown tool invocation attempt
6. Unknown envelope source (Phase A) or invalid signature (Phase B)
7. Containment anomaly (execution outside allowed surface)

## Metrics Dashboard (Future)

Consider creating a dashboard to visualize:
- Parse success rate over time
- Deny rate reasons distribution
- Containment anomalies (should always be 0)
- Determinism hash stability
- Node activity (Phase B)
- Task type distribution

## Notes

- Phase B is **NOT** implemented yet
- Do not implement Phase B until Phase A metrics are stable
- All execution must go through hub runner - no direct commands
- Desktop remains sole executor for resource-intensive tasks
- Laptop can create directives, but desktop executes them
