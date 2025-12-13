# Autonomy Guardrail Integrity Index (AGII)
**Generated:** 2025-11-12T01:49:32.990421+00:00

## Scorecard
| Dimension | Score | Status | Key signals |
| --- | --- | --- | --- |
| Reliability | 100.0 | green | Stability 100.0% / Coherence 100.0% |
| Observability | 89.0 | green | Velocity 89.8% / Footprint 100.0%; WARN 6.1% |
| Safeguards | 100.0 | green | Compliance 100.0% / apply-mode on; watchdog actions 0; run failures 0 |

**Overall AGII:** 96.3 (green)

## Reliability
- Window size: 50 runs (limit 50)
- Success rate: 100.00%
- TES average: 96.95

## Observability
- Warn ratio (last decisions): 6.06% (2/33)
- Memory skip ratio: 6.06%
- LLM latency p50 / p95: 69.61s / 69.61s
- Latest alert: 2025-11-12T01:49:32.990421+00:00 :: [OK] Observability thresholds within guardrails.

## Safeguards
- Watchdog apply mode: enabled
- Watchdog candidate count: 0
- Recent run failures: 0
