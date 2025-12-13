# Autonomy Guardrail Integrity Index (AGII)
**Generated:** 2025-12-13T01:49:32.790686+00:00

## Scorecard
| Dimension | Score | Status | Key signals |
| --- | --- | --- | --- |
| Reliability | 96.0 | green | Stability 96.0% / Coherence 96.0% |
| Observability | 91.1 | green | Velocity 87.9% / Footprint 95.8%; WARN 0.0% |
| Safeguards | 100.0 | green | Compliance 100.0% / apply-mode on; watchdog actions 0; run failures 0 |

**Overall AGII:** 95.7 (green)

## Reliability
- Window size: 50 runs (limit 50)
- Success rate: 100.00%
- TES average: 95.81

## Observability
- Warn ratio (last decisions): 0.00% (0/120)
- Memory skip ratio: 0.00%
- LLM latency p50 / p95: 69.61s / 69.61s
- Latest alert: 2025-12-13T01:49:32.790686+00:00 :: [OK] Observability thresholds within guardrails.

## Safeguards
- Watchdog apply mode: enabled
- Watchdog candidate count: 0
- Recent run failures: 0
