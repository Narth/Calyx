## Intent Envelope
- **Envelope ID:** <!-- envelope_id from telemetry/outbox/intents/ -->
- **Envelope Path:** <!-- path to envelope JSON file -->

## Contract Risk Tier
- **Risk Tier:** <!-- low | med | high -->
- **Rationale:** <!-- why this risk tier was assigned -->

## Required Checks
<!-- Check boxes based on risk tier from CALYX_CONTRACT.yaml -->
- [ ] Lint
- [ ] Unit tests
- [ ] Schema validation
- [ ] Harness lane(s) relevant <!-- med+ -->
- [ ] Receipt presence check <!-- med+ -->
- [ ] Mandatory human approval marker <!-- high -->
- [ ] Extra regression suite <!-- high -->

## Receipts/Manifests
- **Contract SHA256:** <!-- SHA256 of CALYX_CONTRACT.yaml -->
- **Run Manifest:** <!-- path to manifest in runtime/manifests/ -->
- **Result JSONL:** <!-- path to results in runtime/benchmarks/results/ -->
- **Hub Runner Receipt:** <!-- path to receipt in runtime/receipts/ -->

## Rollback Plan
<!-- Required for high risk or refactor_scope tasks -->
<!-- Steps to revert changes if needed -->
<!-- List of affected files -->

## Changes Summary
<!-- Brief description of what changed and why -->

## Testing
<!-- How this was tested, test results -->

## Related
<!-- Links to related issues, envelopes, or discussions -->
