# UCC × DDM-MC v1.0 Summary

Generated: 2025-12-13T02:21:26.316Z

## N2_mu0.2
- Trials: 500
- k_emp_MC: -3.135
- RT mean=1.503, var=2.147, min=0.100, max=5.000, median=0.870
- Anomalies (entropy): fail=113, premature_emp=2
- RT-only flags: timeouts=37, fast=46

## N2_mu0.4
- Trials: 500
- k_emp_MC: -2.961
- RT mean=1.303, var=1.748, min=0.100, max=5.000, median=0.760
- Anomalies (entropy): fail=96, premature_emp=2
- RT-only flags: timeouts=27, fast=49

## N4_mu0.2
- Trials: 500
- k_emp_MC: -3.135
- RT mean=0.806, var=0.709, min=0.060, max=5.000, median=0.550
- Anomalies (entropy): fail=37, premature_emp=0
- RT-only flags: timeouts=7, fast=47

## N4_mu0.4
- Trials: 500
- k_emp_MC: -2.961
- RT mean=0.744, var=0.551, min=0.060, max=5.000, median=0.520
- Anomalies (entropy): fail=32, premature_emp=0
- RT-only flags: timeouts=3, fast=46

## N8_mu0.2
- Trials: 500
- k_emp_MC: -3.135
- RT mean=0.444, var=0.117, min=0.080, max=3.980, median=0.350
- Anomalies (entropy): fail=4, premature_emp=0
- RT-only flags: timeouts=0, fast=46

## N8_mu0.4
- Trials: 500
- k_emp_MC: -2.961
- RT mean=0.435, var=0.115, min=0.080, max=3.980, median=0.350
- Anomalies (entropy): fail=4, premature_emp=0
- RT-only flags: timeouts=0, fast=48

Diagnostics locked: softmax belief (beta=1), H_norm entropy; fail via plateau_time_post_med>0.25*Tmax with H_norm>0.6 or timeout; premature via k_emp_MC (1st percentile early dH_norm from N=2 baselines per mu). No analytic slope, no transients, Wiener noise only.
