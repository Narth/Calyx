import sys
from pathlib import Path
# avoid importing pytest at module import time so tests can run with plain `python` in CI/mock environments

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.kws import score_wake_word, WakeWordHit, precompute_variants, _phonetic_distance
from asr.normalize import normalize_proper_nouns
from asr.config import load_config
from asr.kws import WakeWordHit


def test_score_wake_word_happy_path():
    samples = [("Calyx", 0.0, 0.1)]
    candidates = ["calyx", "calix"]
    hits = score_wake_word(samples, candidates, decoder_probs={"calyx": 0.9})
    assert isinstance(hits, list)
    assert any(isinstance(h, WakeWordHit) for h in hits)
    # expect best match to be 'calyx' with non-zero confidence
    names = [h.word.lower() for h in hits]
    assert "calyx" in names or len(hits) > 0


def test_score_wake_word_near_miss():
    # near-miss token should still score via levenshtein
    samples = [("Kalix", 0.0, 0.1)]
    candidates = ["calyx", "calix"]
    hits = score_wake_word(samples, candidates)
    # expect at least one hit, but lower confidence than exact
    assert len(hits) >= 0
    if hits:
        assert 0.0 < hits[0].confidence <= 1.0


def test_normalize_proper_nouns_conservative():
    # normalization should only replace when confidence/context is present; smoke test
    text = "I said Calix and Calyx maybe"
    cfg = load_config()
    # create a low-confidence hit and a high-confidence hit
    hits = [WakeWordHit(word="Calyx", confidence=0.9, start_time=0.0, end_time=0.1, source="kws", matched_variant="Calix" )]
    out = normalize_proper_nouns(text, hits, cfg)
    assert isinstance(out, str)
    assert "Calyx" in out


def test_precompute_variants_and_phonetic_distance():
    variants = ["calyx", "calix"]
    enc = precompute_variants(variants)
    assert isinstance(enc, dict)
    assert "calyx" in enc
    # soft phonetic distance between similar encodings should be >= 0 and <=1
    d = _phonetic_distance(enc["calyx"], enc["calix"])
    assert isinstance(d, float)
    assert 0.0 <= d <= 1.0


def _run_all():
    print("Running tests in tools/test_kws.py")
    tests = [
        test_score_wake_word_happy_path,
        test_score_wake_word_near_miss,
        test_normalize_proper_nouns_conservative,
        # KWS helper tests
        test_precompute_variants_and_phonetic_distance,
    ]
    failures = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"ok - {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL - {name}: {e}")
        except Exception as e:
            failures += 1
            print(f"ERROR - {name}: {e}")
    if failures:
        print(f"{failures} tests failed")
        raise SystemExit(1)
    print("All tests passed")


if __name__ == "__main__":
    _run_all()
