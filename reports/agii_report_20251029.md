# Autonomy Guardrail Integrity Index (AGII)
**Generated:** 2025-10-29T14:12:10.929891+00:00

## Scorecard
| Dimension | Score | Status | Key signals |
| --- | --- | --- | --- |
| Reliability | 100.0 | green | Success 100.0% (n=50); TES avg 97.0 |
| Observability | 95.5 | green | Warn ratio 9.1%; memory skips 0.0%; LLM p95 69.6s |
| Safeguards | 82.5 | amber | Watchdog candidates 1; apply-mode on; run failures 1 |

**Overall AGII:** 92.7 (green)

## Reliability
- Window size: 50 runs (limit 50)
- Success rate: 100.00%
- TES average: 96.95

## Observability
- Warn ratio (last decisions): 9.09% (1/11)
- Memory skip ratio: 0.00%
- LLM latency p50 / p95: 69.61s / 69.61s
- Latest alert: 2025-10-29T14:12:10.929891+00:00 :: [OK] Observability thresholds within guardrails.

## Safeguards
- Watchdog apply mode: enabled
- Watchdog candidate count: 1
- Recent run failures: 1
