from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import difflib
import functools
import time
import threading
import csv
from pathlib import Path

try:
    # doublemetaphone from 'metaphone' package
    from metaphone import doublemetaphone
    DM_AVAILABLE = True
except Exception:
    DM_AVAILABLE = False


@functools.lru_cache(maxsize=1024)
def phonetic_encode(word: str) -> Tuple[str, Optional[str]]:
    w = (word or "").lower()
    if DM_AVAILABLE:
        return doublemetaphone(w)
    # fallback: simple Soundex-ish hash
    def soundex(s: str) -> str:
        s = s.upper()
        if not s:
            return ""
        mapping = {"BFPV": "1", "CGJKQSXZ": "2", "DT": "3", "L": "4", "MN": "5", "R": "6"}
        first = s[0]
        tail = "".join(mapping.get(ch, "") if any(ch in k for k in mapping) else "" for ch in s[1:])
        head = first + tail
        return (head + "000")[:4]

    return (soundex(w), None)


def _clamp01(x: float) -> float:
    try:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return float(x)
    except Exception:
        return 0.0


def _phonetic_soft_score(token: str, kw: str, confusables: List[str]) -> float:
    """Return a confusable-aware phonetic similarity in [0,1].

    - Computes soft phonetic similarity between token and the wake word.
    - Discounts the score when token is also close to any confusable.
    """
    try:
        t_enc = phonetic_encode(token or "")
        kw_enc = phonetic_encode(kw or "")
        kw_sim = _phonetic_distance(t_enc, kw_enc)
        conf_max = 0.0
        for c in (confusables or []):
            try:
                conf_sim = _phonetic_distance(t_enc, phonetic_encode(c))
                if conf_sim > conf_max:
                    conf_max = conf_sim
            except Exception:
                pass
        # discount by half of the strongest confusable similarity
        raw = kw_sim - 0.5 * conf_max
        return _clamp01(raw)
    except Exception:
        return 0.0


@functools.lru_cache(maxsize=1024)
def precompute_variants(variants: List[str]) -> Dict[str, Tuple[str, Optional[str]]]:
    """Return a mapping of lowercased variant -> phonetic encoding tuple.

    Used by tests and to cheaply build candidate encodings.
    """
    return {v.lower(): phonetic_encode(v) for v in variants}


def _phonetic_distance(enc_a: Tuple[str, Optional[str]], enc_b: Tuple[str, Optional[str]]) -> float:
    """Compute a soft phonetic similarity score in [0,1].

    Exact primary-code matches return 1.0. Otherwise fall back to a
    SequenceMatcher ratio on the concatenated encodings.
    """
    a_primary = (enc_a[0] or "")
    b_primary = (enc_b[0] or "")
    if a_primary and b_primary and a_primary == b_primary:
        return 1.0
    # build representative strings including secondary code when present
    a = (enc_a[0] or "") + ("|" + (enc_a[1] or "") if enc_a[1] else "")
    b = (enc_b[0] or "") + ("|" + (enc_b[1] or "") if enc_b[1] else "")
    if not a and not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


@dataclass
class WakeWordHit:
    word: str
    confidence: float
    start_time: float
    end_time: float
    source: str
    matched_variant: str
    phonetic_score: float = 0.0
    lev_score: float = 0.0
    decoder_score: float = 0.0


def _levenshtein_ratio(a: str, b: str) -> float:
    """Return a normalized similarity in [0,1].

    Prefer rapidfuzz when available for speed/quality; otherwise fall back to
    difflib.SequenceMatcher.
    """
    try:
        # rapidfuzz is optional and fast; normalized_similarity returns 0..100
        from rapidfuzz.distance import Levenshtein as _Lev  # type: ignore
        return float(_Lev.normalized_similarity(a, b) / 100.0)
    except Exception:
        # difflib fallback
        return difflib.SequenceMatcher(None, a, b).ratio()


# simple audit logging
_audit_lock = threading.Lock()
_audit_path = Path("logs") / "wake_word_audit.csv"
_audit_path.parent.mkdir(parents=True, exist_ok=True)
# include extra telemetry fields: session_id, source_file_or_clip
if not _audit_path.exists():
    with _audit_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ts", "session_id", "source", "word", "variant", "phonetic", "lev", "decoder", "fused", "decision"])


def _audit_log(row: List):
    with _audit_lock:
        with _audit_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)


def precompute_variants(variants: List[str]) -> Dict[str, Tuple[str, Optional[str]]]:
    """Precompute and cache phonetic encodings for a list of variants.

    Returns a mapping variant->phonetic_encoding tuple as returned by phonetic_encode.
    """
    enc = {v: phonetic_encode(v) for v in variants}
    return enc


def _phonetic_distance(enc_a: Tuple[str, Optional[str]], enc_b: Tuple[str, Optional[str]]) -> float:
    """Compute a soft phonetic similarity score between two metaphone encodings.

    Returns a float in [0.0, 1.0] where 1.0 is exact match and 0.0 is different.
    When metaphone isn't available the fallback uses soundex equality (binary) or prefix similarity.
    """
    a0 = (enc_a[0] or "").lower()
    b0 = (enc_b[0] or "").lower()
    if not a0 or not b0:
        return 0.0
    if a0 == b0:
        return 1.0
    # soft score: normalized longest common subsequence / maxlen
    import difflib as _difflib
    ratio = _difflib.SequenceMatcher(None, a0, b0).ratio()
    return float(ratio)


def score_wake_word(
    transcript_words: List[Tuple[str, float, float]],
    candidates: List[str],
    decoder_probs: Dict[str, float] | None = None,
    weights: Dict[str, float] | None = None,
    session_id: str = "",
    source_file_or_clip: str = "",
    cfg=None,
    min_confidence: float | None = None,
) -> List[WakeWordHit]:
    """Score possible wake-word hits from word-level transcript with timestamps.

    transcript_words: list of (word, start, end)
    candidates: list of candidate variant strings
    decoder_probs: optional mapping from word->decoder confidence (0..1)
    weights: optional fusion weights
    """
    hits: List[WakeWordHit] = []
    if not transcript_words:
        return hits

    # use precompute_variants to cache encodings (and leverage lru_cache on phonetic_encode)
    try:
        cand_enc = precompute_variants(candidates)
    except Exception:
        cand_enc = {c: phonetic_encode(c) for c in candidates}
    # if cfg provided, attempt to read kws settings for weights/thresholds
    if cfg is not None:
        try:
            kws_settings = cfg.settings().get("kws", {})
            cfg_weights = kws_settings.get("weights")
            if cfg_weights:
                weights = cfg_weights
            else:
                weights = weights or {"phonetic": kws_settings.get("phonetic", 0.5), "lev": kws_settings.get("lev", 0.3), "decoder": kws_settings.get("decoder", 0.2)}
            if min_confidence is None:
                min_confidence = kws_settings.get("trigger_threshold", min_confidence)
            # soft-phonetic gating and parameters
            ph_cfg = kws_settings.get("phonetic", {})
            soft_allow = bool(ph_cfg.get("allow", False))
            soft_confusables = list(ph_cfg.get("confusables", [])) if isinstance(ph_cfg.get("confusables", []), list) else []
        except Exception:
            weights = weights or {"phonetic": 0.5, "lev": 0.3, "decoder": 0.2}
            soft_allow = False
            soft_confusables = []
    else:
        weights = weights or {"phonetic": 0.5, "lev": 0.3, "decoder": 0.2}
        soft_allow = False
        soft_confusables = []
    decoder_probs = decoder_probs or {}

    for word, t0, t1 in transcript_words:
        w = word.strip().lower()
        if not w:
            continue
        w_enc = phonetic_encode(w)
        best_conf = 0.0
        best_variant = ""
        best_components = (0.0, 0.0, 0.0)
        for c, enc in cand_enc.items():
            # phonetic score: prefer exact metaphone match but allow soft score
            phon_score = 1.0 if (w_enc[0] and enc[0] and w_enc[0] == enc[0]) else _phonetic_distance(w_enc, enc)
            # optional confusable-aware soft phonetic score (independent term)
            phon_soft = 0.0
            if soft_allow:
                try:
                    phon_soft = _phonetic_soft_score(w, c, soft_confusables)
                except Exception:
                    phon_soft = 0.0
            lev = _levenshtein_ratio(w, c)
            # normalize token when looking up decoder_probs
            key = w.lower().strip().strip(".,!?\"'()[]")
            decoder_score = float(decoder_probs.get(key, 0.0))
            fused = (
                weights.get("phonetic", 0.5) * phon_score
                + weights.get("lev", 0.3) * lev
                + weights.get("decoder", 0.2) * decoder_score
                + weights.get("phonetic_soft", 0.0) * phon_soft
            )
            if fused > best_conf:
                best_conf = fused
                best_variant = c
                # keep base components for audit consistency; soft term is implicit in fused
                best_components = (phon_score, lev, decoder_score)

        if best_conf > 0.0:
            p, l, d = best_components
            hit = WakeWordHit(word=best_variant.title(), confidence=min(1.0, best_conf), start_time=t0, end_time=t1, source="kws", matched_variant=w, phonetic_score=p, lev_score=l, decoder_score=d)
            # apply min_confidence filtering if requested
            if (min_confidence is None) or (hit.confidence >= min_confidence):
                hits.append(hit)
            _audit_log([time.time(), session_id, source_file_or_clip, w, best_variant, p, l, d, best_conf, "scored"])

    return hits
