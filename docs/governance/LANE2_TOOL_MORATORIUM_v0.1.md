# Lane 2 Tool Moratorium v0.1

## Scope

**Suite:** `prompt_injection_v0_2` (Lane 2) only. Lane 1 and other suites are unchanged.

## Rationale

To enable **cross-node “system wavelength” convergence** for GDH and governance auditing, Lane 2 defines a canonical system action of **NO_TOOL** regardless of what the model attempted. This way:

- All nodes report the same canonical outcome for action hashing (`lane2_system_action = NO_TOOL`).
- Attempted tool calls remain recorded as **telemetry** (`tool_calls_attempted`, `lane2_violation_flags`) for forensics and temperament hashing.
- Security gates (containment, no unauthorized execution) are unchanged: tool execution remains policy-gated and blocked for non-allowlisted tools.

## Invariants

1. **No tool execution change:** Policy and execution logic are unchanged. Non-allowlisted tools are still blocked; allowlisted tools still require policy check. No new tools are executed.
2. **Gate metrics unchanged:** `containment_rate`, `attack_success_rate`, `unauthorized_tool_invocation_rate` are computed from existing receipt fields (`tool_calls_executed`, `pass`, etc.) and must not regress.
3. **Receipt addendum only:** New fields are additive: `lane2_system_action`, `lane2_violation_flags`, `lane2_parse_ok`. Existing fields and suite content are unchanged.
4. **Lane 1 unchanged:** No changes to protocol_probe_v0_1 or Lane 1 behavior.

## Receipt fields (Lane 2 only)

When `suite_id == "prompt_injection_v0_2"`, each receipt includes:

| Field | Value | Description |
|-------|--------|-------------|
| **lane2_system_action** | `"NO_TOOL"` | Canonical system action for this suite (always NO_TOOL for moratorium). |
| **lane2_violation_flags** | `["ATTEMPTED_TOOL:<name>", ...]` | Sorted list of attempted tool names (allowlisted or not), prefixed for telemetry. |
| **lane2_parse_ok** | same as `llm_parse_ok` | Parse success; reused from existing LLM receipt field (or true for stub). |

- `tool_calls_attempted` and `tool_calls_executed` remain as today.
- Gate metrics (containment_rate, attack_success_rate, unauthorized_tool_invocation_rate) are computed from existing fields only.

## Implementation

- **Harness:** In the Lane 2 evaluator path (runner), when writing a receipt for `prompt_injection_v0_2`, the three fields above are set. No change to policy checks or to which tools are executed.
- **Isolation:** Changes are in the harness policy/evaluator layer (receipt writing), not in suite definitions or case content.

## Version

- **Spec version:** v0.1
- **Suite:** prompt_injection_v0_2 only.
