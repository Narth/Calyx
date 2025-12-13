from __future__ import annotations
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ph = root / "outgoing" / "shared_voice" / "persona_history.json"
ps = root / "outgoing" / "shared_voice" / "persona.json"
rg = root / "outgoing" / "agents" / "registry.json"


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    ph_d = load_json(ph)
    ps_d = load_json(ps)
    rg_d = load_json(rg)

    # persona history
    entities_with_history = 0
    num_events = 0
    unique_tones: set[str] = set()
    hist = ph_d.get("history") if isinstance(ph_d, dict) else None
    if isinstance(hist, dict):
        for ent, lst in hist.items():
            if isinstance(lst, list) and lst:
                entities_with_history += 1
                num_events += len(lst)
                for ev in lst:
                    if isinstance(ev, dict):
                        t = ev.get("tone")
                        if isinstance(t, str) and t:
                            unique_tones.add(t.strip())

    # snapshot
    last_tone = ps_d.get("last_tone") if isinstance(ps_d.get("last_tone"), dict) else {}
    entities_with_snapshot = len(last_tone)

    # registry
    agents = rg_d.get("agents") if isinstance(rg_d.get("agents"), dict) else {}
    num_agents = len(agents)
    entities_with_tone_in_registry = sum(
        1
        for e in agents.values()
        if isinstance(e, dict) and isinstance(e.get("last_tone"), str) and e.get("last_tone")
    )

    summary = {
        "persona_history": {
            "entities_with_history": entities_with_history,
            "num_events": num_events,
            "unique_tones": sorted(unique_tones),
            "unique_tones_count": len(unique_tones),
            "source": str(ph.relative_to(root)) if ph.exists() else None,
        },
        "persona_snapshot": {
            "entities_with_snapshot": entities_with_snapshot,
            "source": str(ps.relative_to(root)) if ps.exists() else None,
        },
        "registry": {
            "entities_total": num_agents,
            "entities_with_tone": entities_with_tone_in_registry,
            "source": str(rg.relative_to(root)) if rg.exists() else None,
        },
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
