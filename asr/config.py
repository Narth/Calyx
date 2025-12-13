import pathlib
import os
import yaml
from dataclasses import dataclass
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config.yaml"


@dataclass
class Cfg:
    raw: Dict[str, Any]

    def settings(self) -> Dict[str, Any]:
        return self.raw.get("settings", {})


def load_config(path: str | None = None) -> Cfg:
    p = CFG_PATH if path is None else pathlib.Path(path)
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    # Overlay environment hints (CBO GPU gate & faster-whisper hints)
    try:
        settings = dict(raw.get("settings", {}))
        if os.getenv("CBO_GPU_ALLOWED") == "1":
            dev = os.getenv("FASTER_WHISPER_DEVICE")
            comp = os.getenv("FASTER_WHISPER_COMPUTE_TYPE") or os.getenv("CT2_COMPUTE_TYPE")
            if dev:
                settings["faster_whisper_device"] = dev
            if comp:
                settings["faster_whisper_compute_type"] = comp
        raw["settings"] = settings
    except Exception:
        pass
    return Cfg(raw=raw)
