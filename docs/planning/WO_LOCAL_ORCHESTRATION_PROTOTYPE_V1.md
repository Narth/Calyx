---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_LOCAL_ORCHESTRATION_PROTOTYPE_V1

## Purpose

Prepare the first bounded local orchestration prototype using:

- Ollama as the local model runtime
- LangGraph as the explicit state/orchestration engine
- LangChain as the prompt/parser/model-adapter utility layer

This work order is prototype-only. It does not authorize production wiring, startup integration, or authority expansion.

## Scope

The prototype is a local-only test flow that:

1. Accepts a bounded test input
2. Moves through explicit state transitions
3. Invokes a preferred Ollama model: `qwen2.5-coder:latest`
4. Normalizes output through LangChain utilities
5. Emits receipts at each step
6. Returns a final bounded result

## Non-Goals

- No sunrise changes
- No canonical launcher changes
- No background services
- No network-exposed endpoints
- No OpenClaw involvement
- No AutoGPT installation or staging

## Recommended Implementation Surfaces

- Prototype code root:
  - `C:\Calyx_Terminal\staging\work\local_orchestration_prototype`
- Python environment:
  - `C:\Calyx_Terminal\venvs\langgraph_langchain_dev`
- Prototype receipts:
  - `C:\Calyx_Terminal\runtime\receipts\prototype`
- Prototype reports:
  - `C:\Calyx_Terminal\reports`

## Prototype Purpose and Scope

### Purpose

Demonstrate that Station Calyx can run a receipt-first, local-only orchestration flow without changing canonical runtime behavior.

### Bounded Test Input

Use a small JSON-like payload:

```json
{
  "prototype_id": "local_orch_v1",
  "input_text": "Summarize this test input in one short sentence.",
  "max_output_chars": 160,
  "mode": "prototype_local_only"
}
```

### Bounded Final Result

The prototype should return:

- normalized final text
- model identifier used
- state path traversed
- receipt paths written
- terminal outcome classification

## State / Node Design

### State Diagram

`input_received` -> `input_validated` -> `prompt_prepared` -> `model_invoked` -> `output_normalized` -> `result_finalized`

### Node Sequence

1. `receive_input`
   - Accepts the bounded input payload from a local CLI-style call or direct function invocation.
   - Rejects missing or oversized input.

2. `validate_input`
   - Confirms required fields.
   - Enforces bounded limits such as `max_output_chars`.
   - Emits validation receipt.

3. `prepare_prompt`
   - Uses LangChain prompt utilities to create a strict local prompt.
   - Includes explicit output constraints.
   - Emits prompt-preparation receipt.

4. `invoke_local_model`
   - Calls Ollama at `http://127.0.0.1:11434`.
   - Uses `qwen2.5-coder:latest`.
   - Emits invocation receipt with latency and response metadata.

5. `normalize_output`
   - Uses LangChain parser/transform utilities to trim, bound, and normalize the model output.
   - Emits normalization receipt.

6. `finalize_result`
   - Builds the final bounded result envelope.
   - Emits final-result receipt.

### LangGraph State Shape

Recommended initial state fields:

```python
{
  "prototype_id": str,
  "input_text": str,
  "max_output_chars": int,
  "prompt_text": str,
  "raw_model_text": str,
  "normalized_text": str,
  "model_id": str,
  "receipt_paths": list[str],
  "failure_classification": str | None,
  "status": str
}
```

## Model Invocation Plan

### Preferred Model

- `qwen2.5-coder:latest`

### Invocation Surface

- Local Ollama HTTP API only
- `http://127.0.0.1:11434/api/generate`

### Prompt Strategy

Use a prompt that constrains:

- one short sentence only
- no markdown
- no bullets
- maximum output length reflected from input bounds

### LangChain Utility Layer

Use LangChain for:

- prompt templating
- parser/normalizer logic
- model-adapter boundary helpers

Do not let LangChain define governance logic. Governance stays explicit in the prototype code and receipts.

## Receipt Plan

Emit one receipt per node:

1. `prototype_input_received`
2. `prototype_input_validated`
3. `prototype_prompt_prepared`
4. `prototype_model_invoked`
5. `prototype_output_normalized`
6. `prototype_result_finalized`

Recommended receipt fields:

- `ts_utc`
- `prototype_id`
- `node`
- `status`
- `input_sha256`
- `model_id` when applicable
- `latency_ms` when applicable
- `failure_classification` when applicable
- `notes`

Prototype receipts should remain clearly non-canonical, for example by using a dedicated receipt type prefix such as `prototype.local_orch.*`.

## Validation Plan

1. Static validation
   - Confirm required files and Python environment exist.

2. Input-bound validation
   - Pass valid bounded input.
   - Reject empty input.
   - Reject oversized input.

3. Local model validation
   - Confirm Ollama endpoint reachable.
   - Confirm `qwen2.5-coder:latest` available.

4. Graph validation
   - Confirm nodes execute in the expected order.
   - Confirm terminal state is deterministic on success/failure classes.

5. Receipt validation
   - Confirm each node writes exactly one receipt.
   - Confirm final result includes all receipt paths.

## Failure Classifications

- `input_invalid`
- `input_oversized`
- `ollama_unreachable`
- `model_unavailable`
- `invocation_failed`
- `normalization_failed`
- `receipt_write_failed`
- `unexpected_state_transition`

These are prototype-only classifications and do not redefine canonical Station failure taxonomies.

## Exact Test Order

1. Environment check in `venvs\langgraph_langchain_dev`
2. Receipt directory existence check
3. Ollama endpoint reachability check
4. Model availability check for `qwen2.5-coder:latest`
5. Happy-path input execution
6. Empty-input rejection test
7. Oversized-input rejection test
8. Forced model-unavailable simulation
9. Receipt completeness verification
10. Final bounded-result verification

## Risks / Constraints

- Local-model output may still vary, so output normalization must be explicit.
- Receipt writes must stay separate from canonical production lanes.
- The prototype must remain manually invoked and non-resident.
- No startup hooks or service registration are permitted in this work order.

## Recommended Next Work Order

1. Create scaffold files under `staging/work/local_orchestration_prototype/`
2. Add a local script entrypoint with no service registration
3. Implement LangGraph state and nodes
4. Implement Ollama call wrapper pinned to `qwen2.5-coder:latest`
5. Implement LangChain prompt/parser utilities
6. Implement prototype receipt writer
7. Run the exact test order above
