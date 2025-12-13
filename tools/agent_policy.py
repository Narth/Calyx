import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"


def load_manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_model_entry(model_id: str = None):
    m = load_manifest()
    if model_id is None:
        return m["models"][0]
    for e in m.get("models", []):
        if e.get("id") == model_id:
            return e
    return None


def assert_allowed(action: str, model_id: str = None):
    """Assert that the requested action is allowed by the manifest.

    Actions: 'inference', 'training', 'export', 'publish'
    Raises RuntimeError if disallowed.
    """
    entry = get_model_entry(model_id)
    if entry is None:
        raise RuntimeError("No model entry found in manifest")

    if action == "inference":
        return True
    if action == "training" and not entry.get("allow_training", False):
        raise RuntimeError("Training is disallowed by model manifest")
    if action in ("export", "publish") and not entry.get("allow_redistribution", False):
        raise RuntimeError(f"Action '{action}' is disallowed by model manifest")

    return True


if __name__ == "__main__":
    print("Model manifest at:", MANIFEST_PATH)
    print("Sample entry:", get_model_entry())
