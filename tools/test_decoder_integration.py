import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.config import load_config
from asr.pipeline import transcribe_chunk
from asr.kws import score_wake_word

def run_test(wav_path):
    p = Path(wav_path)
    if not p.exists():
        print("Missing:", p)
        return
    import soundfile as sf
    audio, sr = sf.read(p)
    cfg = load_config("config.yaml")
    res = transcribe_chunk(audio, cfg, sr=sr)
    print("TRANSCRIBE OUTPUT:")
    print(res)
    raw_words = res.get("words", [])
    decoder_probs = res.get("decoder_probs", {}) or {}
    print("DECODER PROBS:", decoder_probs)
    # coerce words
    words = []
    for w in raw_words:
        try:
            word_text = str(w[0])
            start_t = float(w[1]) if len(w) > 1 else 0.0
            end_t = float(w[2]) if len(w) > 2 else 0.0
        except Exception:
            try:
                word_text = str(w.get("word", ""))
                start_t = float(w.get("start", 0.0))
                end_t = float(w.get("end", 0.0))
            except Exception:
                continue
        words.append((word_text, start_t, end_t))

    candidates = ["calix","kaylix","calyxes","kelly's","kallax","caleks"]
    hits = score_wake_word(words, candidates, decoder_probs=decoder_probs)
    print("HITS:")
    for h in hits:
        print(h)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tools/test_decoder_integration.py <wav_path>")
    else:
        run_test(sys.argv[1])
