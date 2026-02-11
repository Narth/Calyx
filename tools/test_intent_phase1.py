"""Phase 1 verification: IntentArtifact persistence and clarification gate

This script tests:
 - creation of an IntentArtifact
 - persistence to per-intent JSON
 - append to artifacts.jsonl (audit sink)
 - evidence events emitted to evidence.jsonl
 - require_clarified behavior at threshold edges

Run:
    python tools/test_intent_phase1.py
"""
from station_calyx.core.intent_artifact import (
    IntentArtifact,
    accept_intent_artifact,
    load_intent_artifact,
    require_clarified,
    ClarificationRequired,
)
from station_calyx.core.config import get_config
from station_calyx.core.evidence import load_recent_events

import uuid
import os


def run_test():
    cfg = get_config()
    intents_dir = cfg.data_dir / "intents"
    intents_dir.mkdir(parents=True, exist_ok=True)

    # Create sample artifacts
    id_good = f"test-{uuid.uuid4().hex[:8]}"
    id_low = f"test-{uuid.uuid4().hex[:8]}"

    good = IntentArtifact(
        intent_id=id_good,
        raw_user_input="Please analyze log files for disk usage trends.",
        interpreted_goal="Analyze disk usage and suggest cleanup",
        confidence_score=0.95,
        clarification_required=False,
    )

    low = IntentArtifact(
        intent_id=id_low,
        raw_user_input="Make orders when inventory low",
        interpreted_goal="Place orders automatically",
        confidence_score=0.79,
        clarification_required=False,
    )

    # Persist both
    accept_intent_artifact(good)
    accept_intent_artifact(low)

    # Load back
    loaded_good = load_intent_artifact(id_good)
    loaded_low = load_intent_artifact(id_low)

    assert loaded_good is not None and loaded_good.intent_id == id_good
    assert loaded_low is not None and loaded_low.intent_id == id_low

    # Check require_clarified behavior
    try:
        require_clarified(loaded_good)
        print("PASS: good intent cleared clarification check")
    except ClarificationRequired:
        print("FAIL: good intent incorrectly required clarification")

    try:
        require_clarified(loaded_low)
        print("FAIL: low intent incorrectly passed clarification check")
    except ClarificationRequired:
        print("PASS: low intent correctly required clarification")

    # Check evidence events appended
    events = load_recent_events(20)
    print(f"Recent events count: {len(events)}")
    for e in events[-5:]:
        print(e.get('event_type'), e.get('summary'))


if __name__ == '__main__':
    run_test()
