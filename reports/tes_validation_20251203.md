# Station Calyx — TES Validation (2025-12-03)

## Objective
Demonstrate responsible TES behavior (≥95 on clean runs) and guardrail penalties under Safe Mode governance hash `4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7`.

## Evidence Artifacts
- Recalculated metrics: `logs/agent_metrics_recalculated.csv` (541 records; min 68.0, max 100.0, mean 93.88).
- Golden sample (≥99 TES): `logs/tes_golden_sample.csv` (12 runs, all stability_new=1.0, velocity/footprint intact).
- Failure/penalty sample: `logs/tes_failure_sample.csv`
  - Tests-mode failures with graduated credit (stability_new=0.6 → TES_new ≈75–76).
  - Apply_tests failures with enforced penalty (stability_new=0.2 → TES_new 53.0/50.0) at `outgoing/agent_run_synth_apply_fail` and `_mistral`.
  - Long-duration runs (>900s) showing velocity-driven TES=70.
  - Large-footprint runs (14 files, 15 files) showing footprint penalties (TES=76.7; compounded long+footprint yields TES=50.0).
- Uptime/health context: `reports/bridge_pulse_bp-0027.md` (uptime 100%, 6 active agents; TES mean 90.2 flagged Attention).

## Findings
1) Safe-success ceiling proven: golden sample holds TES_new 99–100 with stability_new=1.0, confirming scorer does not over-penalize compliant runs.
2) Graduated failure penalties: tests-mode failures retain partial credit (TES_new +30 vs old), reflecting Safe Mode guardrails while discouraging bad outputs.
3) Performance drag surfaced: long jobs drop TES to 70 via velocity component; large-footprint runs confirm footprint penalty (TES 76.7 with 14 files; compounded long+footprint drives TES to 50.0 with stability_new=1.0).
4) Apply_tests penalty captured twice (different models) with stability_new=0.2 → TES_new 53.0/50.0, demonstrating cross-model apply-mode penalty.

## Next Validation Steps (recommended)
- Optionally vary model families (e.g., Llama/Qwen/TinyLlama) for apply_tests penalties to broaden cross-model proof.
- Periodic pulses tied to snapshot windows after future TES changes.

## Status
Safe-mode validation complete with apply_tests penalties (multi-model) and compounded footprint/velocity penalties; TES guardrail behavior demonstrated.
