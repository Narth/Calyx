# BloomOS Epistemic Glossary v1.0

**Status:** Published. Safe Mode / HALT; observation-only. Descriptive naming only—no behavior, logic, policy, or enforcement.

---

## 1. Reality Inference

**Plain-language:** The process by which BloomOS interprets system state from telemetry for understanding only—never as a basis for dispatch, policy, or automation. Interpretation stays read-only; no step from "what we see" to "what we do."

**Formal:** *Reality inference* is the process by which Station Calyx interprets system state from telemetry and represents it in mirrors and advisories, under the constraint that such interpretation is used only for observation, logging, and advisory output. It does not drive scheduler, dispatch, policies, or Interceptor; it does not constitute inference-to-action. The prohibition on acting from inferred state belongs here; derived state and other epistemic classifications do not themselves grant or imply any exception to that prohibition.

**Evidence:** `bloomos/telemetry/README.md`, `bloomos/telemetry/self_mirror/SELF_MIRROR_SPEC_v1.0.md`, `bloomos/telemetry/mirrors/TELEMETRY_MIRROR_SPEC_v1.0.md`.

---

## 2. Observed Truth

**Plain-language:** A system statement that directly reflects raw telemetry or OS-reported state: what a specific query or sensor returned, with at most format normalization (e.g. units, encoding)—no aggregation, inference, or rate/trend computation.

**Formal:** *Observed truth* is a system statement that directly reflects the value or state reported by a single telemetry source (e.g. OS API, firmware, or a single evidence-gathering command) at a point in time, with at most **format normalization**. Format normalization includes: timestamp encoding (e.g. ISO vs /Date/), units, string casing, or serialization. It does **not** include semantic normalization: changing meaning, combining sources, or interpreting values (e.g. mapping a numeric code to a policy-relevant category). No aggregation over time, no rate calculation, no "provisional" marking.

**Format vs semantic normalization boundary:** If the transformation preserves a one-to-one mapping from source value to stored value (same meaning, different representation), it is format normalization and the result can remain observed truth. If the transformation changes meaning, merges sources, or applies policy/domain logic, the result is derived state.

**Evidence:** `telemetry/energy/energy_snapshot_t0.json` (evidence_commands + power_status/battery); `telemetry/energy/scenario_c_note.json` ("state_observations": true); `telemetry/energy/charge_intake_e2b_temporal_note.json` ("state observation" vs "rate calculations provisional").

---

## 3. Derived State

**Plain-language:** A system statement produced by computation, normalization across sources, or summarization over time from one or more observed truths—e.g. drain rate, charge rate, or normalized findings. It may be marked provisional or validity-scoped.

**Formal:** *Derived state* is a system statement that is computed, aggregated, or summarized from one or more observed truths (or other derived states), including semantic normalization across sources or time. It is explicitly distinguished from observed truth by lifecycle annotations (e.g. provisional, validity scope) or by schema (e.g. reflection_summary, normalized findings). Derived state is never used as a trigger for scheduler, dispatch, policies, or Interceptor under Safe Mode; the action prohibition is defined under Reality Inference.

**Evidence:** `telemetry/energy/charge_intake_e2b_temporal_note.json`; `telemetry/energy/scenario_c_note.json` (validity.rate_calculations); `tools/calyx_guardian/README.md` (normalizes findings, confidence + added_due_to); `bloomos/telemetry/self_mirror/SELF_MIRROR_STATE_SCHEMA.json` (reflection_summary).

---

## 4. Unknown

**Plain-language:** A condition in which telemetry or confirmation the system would use to make a statement is missing, not available from the source, or explicitly deferred—so the system does not assert a value or state for that aspect.

**Formal:** *Unknown* is a condition in which required telemetry or confirmation is absent, unavailable, or explicitly deferred. The system does not assert an observed truth or derived state for that aspect; it may record the unknown (e.g. via a flag, scope, or statement) or omit the assertion. Unknown is an epistemic condition, not a value; it is distinct from "false" (a stated boolean) and from "evidence of absence" (a positive assertion that something was checked and not found).

**Explicit vs implicit unknown:**
- **Explicit unknown:** The system records that data is missing or deferred (e.g. `power_status_unavailable: true`, scope `ac_power_unavailable_or_unstable`, statement "telemetry deferred due to unavailable or unsafe AC power"). The absence is named and traceable.
- **Implicit unknown:** No assertion is made and no flag or note records why; a later consumer cannot distinguish "we did not collect" from "we collected and omitted." Explicit unknown is preferred for audit and Reality Atom classification; implicit unknown is acceptable only where governance explicitly permits (e.g. optional fields omitted).

**Evidence:** `telemetry/energy/energy_e2_wait_receipt.json` (deferred, scope); energy snapshots `power_status_unavailable`; `tools/calyx_guardian/README.md` (findings withdrawn when visibility or confidence insufficient).

---

## 5. Blind Spot

**Plain-language:** An unknown that is formally recorded because of a specific limit: access (e.g. elevation), resource unavailability, or governance (e.g. read-only, no network). Documented so that absence of an assertion is understood as "we could not observe," not "we observed that X is false."

**Formal:** *Blind spot* is a formally declared unknown caused by access limits (e.g. insufficient privileges), unavailable resources (e.g. sensor or service down), or governance constraints (e.g. read-only phase, no network). It is documented in reports or run artifacts so that the lack of a finding or telemetry value is interpretable as "observation was not possible under current constraints" rather than as a negative result or evidence of absence.

**Blind spot vs deferral:**
- **Blind spot:** Observation was attempted or was in scope but could not be completed (e.g. command requires elevation and failed; resource unavailable). The limit is structural or environmental.
- **Deferral:** The system chose not to collect or not to use telemetry for a defined reason (e.g. "charge-window telemetry deferred due to unavailable or unsafe AC power"). Deferral is a decision to treat conditions as unsuitable for collection; blind spot is a documented failure or impossibility of collection. Both result in unknown; only blind spot implies "we tried and could not."

**Evidence:** `tools/calyx_guardian/README.md` ("If a command requires elevation and fails, the report will document the blind spot."); `telemetry/energy/energy_e2_wait_receipt.json` (deferral example: "telemetry deferred due to unavailable or unsafe AC power").

---

## Cross-Cutting Distinctions

| Dimension | Observation | Derivation |
|-----------|-------------|------------|
| Source | Single source, point-in-time; evidence_commands cited | Computed, normalized, or summarized; lifecycle/provisional/validity_scope |
| Format vs semantic | Format-only normalization keeps observed truth | Semantic normalization produces derived state |

| Dimension | Unknown | False |
|-----------|---------|--------|
| Meaning | No assertion made; data absent/unavailable/deferred | Asserted value is false (e.g. boolean false, negative result) |

| Dimension | Absence of evidence | Evidence of absence |
|-----------|---------------------|----------------------|
| Meaning | We did not obtain data; we do not assert | We performed a check and record that something was not present |

---

## Alignment

- **Telemetry mirrors:** Read-only lenses; state reflected as mirror text—never as triggers.
- **Guardian:** Evidence → observed truth; normalized findings + lifecycle → derived state; blind spot documented; findings withdrawn when visibility/confidence insufficient.
- **Safe Mode:** Reality inference carries the sole action prohibition; all epistemic classifications remain descriptive.

---

*Naming reality only. No behavior, logic, or policy changes.*
