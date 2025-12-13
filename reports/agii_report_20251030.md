# Autonomy Guardrail Integrity Index (AGII)
**Generated:** 2025-10-30T14:28:34.302505+00:00

## Scorecard
| Dimension | Score | Status | Key signals |
| --- | --- | --- | --- |
| Reliability | 100.0 | green | Stability 100.0% / Coherence 100.0% |
| Observability | 88.6 | green | Velocity 89.8% / Footprint 100.0%; WARN 6.7% |
| Safeguards | 90.0 | green | Compliance 100.0% / apply-mode on; watchdog actions 1; run failures 0 |

**Overall AGII:** 92.8 (green)

## Reliability
- Window size: 50 runs (limit 50)
- Success rate: 100.00%
- TES average: 96.95

## Observability
- Warn ratio (last decisions): 6.67% (1/15)
- Memory skip ratio: 6.67%
- LLM latency p50 / p95: 69.61s / 69.61s
- Latest alert: 2025-10-30T14:28:34.302505+00:00 :: [OK] Observability thresholds within guardrails.

## Safeguards
- Watchdog apply mode: enabled
- Watchdog candidate count: 1
- Recent run failures: 0
