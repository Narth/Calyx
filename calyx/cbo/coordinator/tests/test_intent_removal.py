import json
import tempfile
from pathlib import Path

import pytest

from calyx.cbo.coordinator.coordinator import Coordinator
from calyx.cbo.coordinator.schemas import Intent


def test_executed_intent_removed(tmp_path: Path):
    """Ensure that when an intent is executed during a pulse it is removed from persistence."""
    # Setup a minimal coordinator with temp root
    root = tmp_path
    (root / "outgoing").mkdir()
    # Create a small state file to use default state
    coord = Coordinator(root=root)

    # Add a dummy intent that will be considered for execution
    intent = Intent(
        id="test-intent-1",
        origin="unit-test",
        description="unit test intent",
        required_capabilities=["schema_validation"],
        desired_outcome="validate schema",
        autonomy_required="execute",
    )
    coord.intents.add_intent(intent)

    # Ensure coordinator is allowed to execute intents
    coord.state.set_autonomy_mode("execute")

    # Run a pulse; coordinator should attempt to execute the intent
    report = coord.pulse()

    # After pulse, the intent should no longer be in the queue
    remaining = [i.id for i in coord.intents.intents]
    assert "test-intent-1" not in remaining
