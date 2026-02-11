import tempfile
from pathlib import Path

from calyx.cbo.coordinator.intent_pipeline import IntentPipeline
from calyx.cbo.coordinator.schemas import Intent


def test_rejects_unclarified_intent(tmp_path: Path):
    root = tmp_path
    pipeline = IntentPipeline(root=root)

    intent = Intent(
        id="intent-demo-01",
        origin="unit-test",
        description="Try to auto-order inventory",
        required_capabilities=["inventory.order"],
        desired_outcome="Reorder items",
    )

    # Ensure no artifact exists
    added = pipeline.add_intent(intent)
    assert added is False
