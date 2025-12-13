"""Simple evaluator for wake-word detection (mock mode).

This is a lightweight alternative to tools/eval_wake_word.py used for quick local
smoke tests. It avoids any previous duplicated/merged content and is safe to run.
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
    return [p for p in folder.iterdir() if p.suffix.lower() == ".wav"]


def mock_transcribe_for_file(p: Path):
    text = p.stem.replace("_", " ")
    tokens = text.split()
    words = [(t, 0.0, 0.0) for t in tokens]
    return {"text": text, "words": words, "decoder_probs": {t.lower(): 0.9 for t in tokens}}


def evaluate_dirs(positive_dir: Path, negative_dir: Path, out_csv: Path, cfg, mock: bool = True):
    rows = []
    stats = {"tp": 0, "fp": 0, "fn": 0}

    for label, folder in [("positive", positive_dir), ("negative", negative_dir)]:
        for p in list_wavs(folder):
            t0 = time.time()
            if mock:
                result = mock_transcribe_for_file(p)
            else:
                # non-mock not implemented here
                result = {"text": "", "words": []}
            t1 = time.time()
            words = result.get("words", [])
            decoder_probs = result.get("decoder_probs", {})
            candidates = cfg.settings().get("kws", {}).get("variants", ["calyx", "calix"])
            hits = score_wake_word(words, candidates, decoder_probs=decoder_probs)
            pred = 1 if hits else 0
            if pred == 1 and label == "positive":
                stats["tp"] += 1
            if pred == 1 and label == "negative":
                stats["fp"] += 1
            if pred == 0 and label == "positive":
                stats["fn"] += 1
            rows.append({"file": str(p), "label": label, "pred": pred, "n_hits": len(hits), "latency_ms": int((t1 - t0) * 1000)})

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="logs/eval_wake_word_simple.csv")
    args = parser.parse_args()
    cfg = load_config()
    positive = Path(ROOT) / "samples" / "wake_word" / "positive"
    negative = Path(ROOT) / "samples" / "wake_word" / "negative"
    metrics = evaluate_dirs(positive, negative, Path(args.out), cfg, mock=True)
    print("Metrics:", metrics)


if __name__ == "__main__":
    main()
