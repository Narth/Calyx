# Usage and station health — receipt schema

Receipts in `cbo_hub/receipts/cbo_core.jsonl` now capture usage and health metrics for auditing and Station Calyx health.

## Usage (token) capture

**Receipt field:** `usage` (object, optional). Present when at least one provider returned token/usage data.

**Shape:** One key per provider that was called and returned usage. Normalized so all providers use the same field names where possible:

```json
"usage": {
  "anthropic": { "input_tokens": 50, "output_tokens": 100, "total_tokens": 150 },
  "openai":   { "input_tokens": 40, "output_tokens": 80,  "total_tokens": 120 },
  "kimi":     { "input_tokens": 45, "output_tokens": 90,  "total_tokens": 135 },
  "local":    { "input_tokens": 30, "output_tokens": 60,  "total_tokens": 90, "eval_duration_ns": 123456789, "latency_ms": 123 }
}
```

**Provider source:**

| Provider   | API source fields                    | Normalized to                |
|-----------|--------------------------------------|------------------------------|
| Anthropic | `usage.input_tokens`, `output_tokens` | input_tokens, output_tokens, total_tokens |
| OpenAI    | `usage.prompt_tokens`, `completion_tokens`, `total_tokens` (if present) | input_tokens, output_tokens, total_tokens |
| Kimi      | `usage.prompt_tokens`, `completion_tokens`, `total_tokens` (OpenAI-compatible) | same |
| Local     | `prompt_eval_count`, `eval_count`, `eval_duration` (Ollama) | input_tokens, output_tokens, total_tokens, eval_duration_ns, latency_ms |

If a provider does not return usage (e.g. Responses API with no usage in response), that provider is still in `providers_called` but has no entry in `usage`.

## Cost estimates (simulation)

**Receipt fields:**

- **`usage.<provider>.cost_estimate_usd`** (optional): Estimated cost in USD for that provider’s call, derived from token counts and configured rates. Only present when rates are set (see below). Local is always `0.0` when usage is present.
- **`cost_estimate_usd`** (optional, top-level): Sum of all per-provider cost estimates for this request. Omitted if no rates are configured for any provider.

**Configuration (env, optional):** Rates are **dollars per million tokens**. Set only the ones you care about; unset means “no estimate for that side.”

| Provider   | Input rate (env)                  | Output rate (env)                   |
|-----------|------------------------------------|-------------------------------------|
| Anthropic | `ANTHROPIC_INPUT_PER_MILLION`      | `ANTHROPIC_OUTPUT_PER_MILLION`      |
| OpenAI    | `OPENAI_INPUT_PER_MILLION`        | `OPENAI_OUTPUT_PER_MILLION`         |
| Kimi      | `KIMI_INPUT_PER_MILLION`          | `KIMI_OUTPUT_PER_MILLION`           |
| Local     | — (always 0)                      | —                                   |

**Example (.env.cbo or environment):**

```bash
# Example rates (check provider pricing; these are illustrative)
ANTHROPIC_INPUT_PER_MILLION=3.0
ANTHROPIC_OUTPUT_PER_MILLION=15.0
OPENAI_INPUT_PER_MILLION=2.5
OPENAI_OUTPUT_PER_MILLION=10.0
KIMI_INPUT_PER_MILLION=0.5
KIMI_OUTPUT_PER_MILLION=2.0
```

Formula: `cost = (input_tokens / 1e6) * input_rate + (output_tokens / 1e6) * output_rate`. You can set only input or only output; the other side is then not included in the estimate. Use these to simulate spend and maximize value per token/credit.

## Station health metrics (per request)

**Receipt fields:**

- **`request_latency_ms`** (int): Wall-clock time for the entire `/chat` request in milliseconds. Includes model call(s), tool loop, and reply building.
- **`usage.<provider>.latency_ms`** (optional): For local (Ollama) only, generation latency in ms derived from `eval_duration` (nanoseconds).

These support:
- Spotting slow requests (e.g. high `request_latency_ms`).
- Local model performance (Ollama `latency_ms` / token throughput).

## Other receipt fields (unchanged)

- `ts_utc`, `endpoint`, `session_id`, `mode`, `allow_tools`
- `user_text_sha256`, `reply_text_sha256`
- `tool_calls`, `executed_tools`
- `providers_called`, `second_opinion_enabled`
- `second_opinion_receipt`, `local_receipt` (when applicable)
- `receipt_sha256`

## Optional future

- **Aggregate dashboards:** Rollups of usage/cost/latency over time (e.g. sum `cost_estimate_usd` and `usage` from receipts) — out of scope for receipt schema; would be a separate pipeline or dashboard.
