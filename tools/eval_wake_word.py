"""Evaluator for wake-word detection.

Simple, single-file evaluator that supports mock mode for CI and real mode for local runs.

Usage examples:
  python tools/eval_wake_word.py --mock --out logs/eval_mock.csv --limit 10
  python tools/eval_wake_word.py --out logs/eval_real.csv --limit 20
"""
from pathlib import Path
import argparse
import csv
import time
from typing import List
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.kws import score_wake_word
from asr.config import load_config


def list_wavs(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if p.suffix.lower() in (".wav", ".flac", ".mp3")]


def mock_transcribe_for_file(p: Path):
    text = p.stem.replace("_", " ")
    tokens = text.split()
    words = [(t, 0.0, 0.0) for t in tokens]
    return {"text": text, "words": words, "decoder_probs": {t.lower(): 0.9 for t in tokens}}


def transcribe_file_real(p: Path, cfg):
    try:
        import soundfile as sf
    except Exception:
        # soundfile missing; caller should handle this
        raise
    try:
        audio, sr = sf.read(str(p))
        from asr.pipeline import transcribe_chunk
        return transcribe_chunk(audio, cfg, sr=sr)
    except Exception as e:
        print("warning: failed to read or transcribe", p, e)
        return {"text": "", "words": []}


"""Batch evaluator for wake-word using repository transcribe and kws utilities.

Features:
- Walks `samples/wake_word/positive` and `samples/wake_word/negative` for audio files
- Runs `asr.pipeline.transcribe_chunk` when available, otherwise supports `--mock`
- Writes per-file CSV with predictions and prints precision/recall/F1

Example:
  python tools/eval_wake_word.py --mock --out logs/eval_mock.csv --limit 8
"""

from pathlib import Path
import argparse
import csv
import time
from typing import List, Optional
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.kws import score_wake_word
from asr.config import load_config


def list_wavs(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    exts = {".wav", ".flac", ".mp3"}
    return [p for p in sorted(folder.iterdir()) if p.suffix.lower() in exts]


def mock_transcribe_for_file(p: Path):
    # simple deterministic mock: filename -> transcript tokens
    text = p.stem.replace("_", " ")
    tokens = text.split()
    words = [(t, 0.0, 0.0) for t in tokens]
    return {"text": text, "words": words, "decoder_probs": {t.lower(): 0.9 for t in tokens}}


def transcribe_file_real(p: Path, cfg):
    try:
        import soundfile as sf
    except Exception as e:
        raise RuntimeError("soundfile not available") from e

    try:
        audio, sr = sf.read(str(p))
    except Exception as e:
        print("warning: failed to read", p, e)
        return {"text": "", "words": []}

    try:
        from asr.pipeline import transcribe_chunk
        return transcribe_chunk(audio, cfg, sr=sr)
    except Exception as e:
        print("warning: transcribe_chunk failed for", p, e)
        return {"text": "", "words": []}


def evaluate_dirs(sample_dirs: List[tuple], out_csv: Path, cfg, mock: bool = True, limit: Optional[int] = None):
    rows = []
    stats = {"tp": 0, "fp": 0, "fn": 0}

    candidates = cfg.settings().get("kws", {}).get("variants", ["calyx", "calix", "kallax", "kalex", "kalix"])

    for label, folder in sample_dirs:
        wavs = list_wavs(folder)
        if limit:
            wavs = wavs[:limit]
        for p in wavs:
            t0 = time.time()
            if mock:
                result = mock_transcribe_for_file(p)
            else:
                try:
                    result = transcribe_file_real(p, cfg)
                except RuntimeError:
                    print("warning: soundfile not available; skipping", p)
                    result = {"text": "", "words": []}
            t1 = time.time()

            words = result.get("words", []) or []
            decoder_probs = result.get("decoder_probs", {}) or {}

            hits = score_wake_word(words, candidates, decoder_probs=decoder_probs, cfg=cfg)
            pred = 1 if hits else 0

            if pred == 1 and label == "positive":
                stats["tp"] += 1
            if pred == 1 and label == "negative":
                stats["fp"] += 1
            if pred == 0 and label == "positive":
                stats["fn"] += 1

            rows.append({
                "file": str(p),
                "label": label,
                "pred": pred,
                "n_hits": len(hits),
                "latency_ms": int((t1 - t0) * 1000),
            })

    tp = stats["tp"]
    fp = stats["fp"]
    fn = stats["fn"]
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "label", "pred", "n_hits", "latency_ms"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return {"precision": prec, "recall": rec, "f1": f1}


def main():
    parser = argparse.ArgumentParser(description="Evaluate wake-word detection on samples/wake_word")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode and skip model transcribe")
    parser.add_argument("--out", default="logs/eval_wake_word.csv", help="Output CSV path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files per dir for quick runs")
    args = parser.parse_args()

    cfg = load_config()

    positive = Path(ROOT) / "samples" / "wake_word" / "positive"
    negative = Path(ROOT) / "samples" / "wake_word" / "negative"

    metrics = evaluate_dirs([("positive", positive), ("negative", negative)], Path(args.out), cfg, mock=args.mock, limit=args.limit)
    print("Metrics:", metrics)


if __name__ == "__main__":
    main()
