from typing import List
from .kws import WakeWordHit


def normalize_proper_nouns(text: str, hits: List[WakeWordHit], cfg) -> str:
    """Apply safe mapping of near-variants to canonical proper nouns like 'Calyx'.

    Rules:
    - Only auto-replace when hit.confidence >= `auto_replace_threshold` in cfg.settings
    - For near-misses, require surrounding context keywords
    """
    if not hits:
        return text

    settings = cfg.settings()
    auto_thresh = settings.get("auto_replace_threshold", 0.85)
    context_keywords = ["terminal", "launch", "hey", "open", "summon"]
    out = text

    for h in hits:
        if h.confidence >= auto_thresh:
            # naive replace; match case-insensitive
            out = out.replace(h.matched_variant, "Calyx")
            out = out.replace(h.matched_variant.title(), "Calyx")
        else:
            # check context words around the matched variant
            lowered = text.lower()
            surround_ok = any(k in lowered for k in context_keywords)
            if h.confidence >= settings.get("kws", {}).get("near_miss_low", 0.6) and surround_ok:
                out = out.replace(h.matched_variant, "Calyx")

    return out
