# UCC × DDM Entropy Diagnostics v0.1 Summary

Generated: 2025-12-13T01:32:38.591Z

## C0
- Trials: 5000
- Params: {'mu': 0.3, 'sigma': 1.0, 'a': 1.0, 'z': 0.0, 'dt': 0.01, 't_max': 5.0, 'transient_sigma': None}
- RT mean=1.051, var=0.693, min=0.060, max=5.000
- Anomalies (entropy labels): premature=5, fail_to_commit=538
- RT-only flags: timeouts=19, fast=3506

## C1
- Trials: 5000
- Params: {'mu': 0.3, 'sigma': 1.0, 'a': 1.0, 'z': 0.0, 'dt': 0.01, 't_max': 5.0, 'transient_sigma': 1.8}
- RT mean=0.497, var=0.385, min=0.020, max=5.000
- Anomalies (entropy labels): premature=15, fail_to_commit=155
- RT-only flags: timeouts=2, fast=4487

## C2
- Trials: 5000
- Params: {'mu': 0.05, 'sigma': 1.0, 'a': 1.0, 'z': 0.0, 'dt': 0.01, 't_max': 5.0, 'transient_sigma': None}
- RT mean=1.116, var=0.809, min=0.050, max=5.000
- Anomalies (entropy labels): premature=4, fail_to_commit=558
- RT-only flags: timeouts=31, fast=3428

## C4
- Trials: 5000
- Params: {'mu': 0.3, 'sigma': 1.0, 'a': 1.0, 'z': 0.2, 'dt': 0.01, 't_max': 5.0, 'transient_sigma': None}
- RT mean=1.016, var=0.757, min=0.030, max=5.000
- Anomalies (entropy labels): premature=3, fail_to_commit=496
- RT-only flags: timeouts=19, fast=3560

Calibrated k_premature=-7.336 from C0 (percentile ~1 of dH_min in early window).\nC3 (OU) dropped in v0.2; to restore, implement true OU noise. Entropy features computed with linear belief mapping.\n