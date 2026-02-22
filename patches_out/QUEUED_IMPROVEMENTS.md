# Queued improvements (Phase 6+)

Low drama, deterministic. No target date; implement when 3-call workflows are routine.

---

## ✅ Spend summary in receipts (done)

Implemented in `cbo_core/app.py`: each receipt has `providers_called` (e.g. `["anthropic"]`, `["local"]`) and `second_opinion_enabled`. Lets you scan “who was called” at a glance.

**Done:** Token/usage capture and request latency. See `cbo_hub/docs/USAGE_AND_HEALTH.md`. Receipt now has `usage` (per-provider input_tokens, output_tokens, total_tokens; local also eval_duration_ns, latency_ms) and `request_latency_ms`.

**Done:** Cost estimate simulation. Set `*_INPUT_PER_MILLION` and `*_OUTPUT_PER_MILLION` (USD per million tokens) in env for anthropic/openai/kimi; local is always 0. Receipt gets `usage.<provider>.cost_estimate_usd` and top-level `cost_estimate_usd`. See `cbo_hub/docs/USAGE_AND_HEALTH.md`.
