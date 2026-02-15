"""
Phase 4B: Deterministic Plan Compaction Engine.
Safe transformations only: never broaden scope, never add tools/actions.
All compaction events logged; dry-run guard ensures no mutation-surface change.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

# Must match autonomous_suite_runner_llm
MUTATING_TOOLS = frozenset({"write_file", "delete_file"})
NON_MUTATING_TOOLS = frozenset({"read_file", "list_dir"})
AVG_ACTION_TOKEN_ESTIMATE = 50  # for compaction_token_savings_est


def _get_path(action: dict) -> str | None:
    """Extract sandbox-relative path from action arguments."""
    args = action.get("arguments") or {}
    path = args.get("path")
    return str(path).strip() if path is not None else None


def _simulate_actions(actions: list[dict]) -> dict[str, str]:
    """
    Dry-run: apply actions to in-memory state. No I/O.
    state[path] = content; delete removes key.
    """
    state: dict[str, str] = {}
    for a in actions:
        tool = (a.get("tool_name") or "").strip()
        path = _get_path(a)
        if tool == "write_file" and path is not None:
            state[path] = str((a.get("arguments") or {}).get("content", ""))
        elif tool == "delete_file" and path is not None:
            state.pop(path, None)
        # read_file, list_dir: no state change
    return state


def _state_hash(state: dict[str, str]) -> str:
    """Deterministic hash of simulated sandbox state."""
    canonical = json.dumps(sorted(state.items()), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _apply_compaction_rules(actions: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """
    Apply Rules A–D. Returns (compacted_actions, rules_applied, dropped_action_ids).
    Never broadens scope; only drops actions.
    """
    if not actions:
        return [], [], []

    rules_applied: list[str] = []
    n = len(actions)
    drop: set[int] = set()

    # Rule C — Last-Write-Wins per path: keep only final write_file(path=X)
    last_write_index: dict[str, int] = {}
    rule_c_dropped = False
    for i, a in enumerate(actions):
        tool = (a.get("tool_name") or "").strip()
        path = _get_path(a)
        if tool == "write_file" and path is not None:
            if path in last_write_index:
                drop.add(last_write_index[path])
                rule_c_dropped = True
            last_write_index[path] = i
    if rule_c_dropped:
        rules_applied.append("last_write_wins")

    # Rule B — Redundant read after write: read_file(X) immediately after write_file(X) with no other mutation to X
    last_mut_to_path: dict[str, int] = {}
    for i, a in enumerate(actions):
        tool = (a.get("tool_name") or "").strip()
        path = _get_path(a)
        if path is None:
            continue
        if tool in MUTATING_TOOLS:
            last_mut_to_path[path] = i
        elif tool == "read_file":
            j = last_mut_to_path.get(path, -1)
            if j >= 0:
                # Check no other mutation to path between j and i
                between_has_mut = any(
                    (ac.get("tool_name") or "").strip() in MUTATING_TOOLS and _get_path(ac) == path
                    for ac in actions[j + 1 : i]
                )
                if not between_has_mut:
                    drop.add(i)
                    if "redundant_read_after_write" not in rules_applied:
                        rules_applied.append("redundant_read_after_write")

    # Rule D — Duplicate sequential reads: read_file(X) read_file(X) -> keep first
    prev_read_path: str | None = None
    for i, a in enumerate(actions):
        tool = (a.get("tool_name") or "").strip()
        if tool == "read_file":
            path = _get_path(a)
            if path is not None and path == prev_read_path:
                drop.add(i)
                if "duplicate_sequential_reads" not in rules_applied:
                    rules_applied.append("duplicate_sequential_reads")
            prev_read_path = path
        else:
            prev_read_path = None

    # Rule A — Trailing non-mutating drop
    i = n - 1
    while i >= 0 and (actions[i].get("tool_name") or "").strip() in NON_MUTATING_TOOLS:
        drop.add(i)
        i -= 1
    if i < n - 1:
        rules_applied.append("trailing_non_mutating_drop")

    kept = [a for i, a in enumerate(actions) if i not in drop]
    dropped_ids = [actions[i].get("action_id", str(i + 1)) for i in sorted(drop)]

    # Renumber action_id and order
    for idx, a in enumerate(kept):
        a = dict(a)
        a["action_id"] = str(idx + 1)
        a["order"] = idx + 1
        kept[idx] = a

    return kept, rules_applied, dropped_ids


def compact_plan(
    plan: dict,
    *,
    skip_if_uncertain: bool = True,
) -> tuple[dict, dict]:
    """
    Deterministic plan compaction. Never broadens scope.
    Returns (compacted_plan, compaction_info).
    compaction_info: {
      compaction_applied: bool,
      original_action_count: int,
      compacted_action_count: int,
      rules_applied: list[str],
      dropped_action_ids: list[str],
      compaction_aborted: bool,
      compaction_aborted_reason: str | None,
      sandbox_state_hash_simulated_before: str | None,
      sandbox_state_hash_simulated_after: str | None,
      dropped_action_count: int,
    }
    If compaction would change final state (guard fails), compaction_aborted=True and plan unchanged.
    """
    actions = list(plan.get("actions") or [])
    compaction_info: dict = {
        "compaction_applied": False,
        "original_action_count": len(actions),
        "compacted_action_count": len(actions),
        "rules_applied": [],
        "dropped_action_ids": [],
        "compaction_aborted": False,
        "compaction_aborted_reason": None,
        "sandbox_state_hash_simulated_before": None,
        "sandbox_state_hash_simulated_after": None,
        "dropped_action_count": 0,
    }

    if len(actions) == 0:
        return plan, compaction_info

    compacted, rules_applied, dropped_ids = _apply_compaction_rules(actions)
    dropped_count = len(dropped_ids)

    if dropped_count == 0:
        return plan, compaction_info

    # Safety guard: dry-run both plans, hashes must match
    state_before = _simulate_actions(actions)
    state_after = _simulate_actions(compacted)
    hash_before = _state_hash(state_before)
    hash_after = _state_hash(state_after)
    compaction_info["sandbox_state_hash_simulated_before"] = hash_before
    compaction_info["sandbox_state_hash_simulated_after"] = hash_after

    if hash_before != hash_after:
        compaction_info["compaction_aborted"] = True
        compaction_info["compaction_aborted_reason"] = "simulated_state_mismatch"
        return plan, compaction_info

    compaction_info["compaction_applied"] = True
    compaction_info["compacted_action_count"] = len(compacted)
    compaction_info["rules_applied"] = rules_applied
    compaction_info["dropped_action_ids"] = dropped_ids
    compaction_info["dropped_action_count"] = dropped_count

    compacted_plan = {
        "plan_id": plan.get("plan_id", ""),
        "actions": compacted,
    }
    return compacted_plan, compaction_info
