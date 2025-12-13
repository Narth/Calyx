"""Generate a per-file decoder_probs report for samples/wake_word.

Writes `decoder_probs_report.csv` with columns: file, detected_words, decoder_probs_json
This is a debugging helper to inspect what `transcribe_chunk` returns.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.config import load_config
from asr.pipeline import transcribe_chunk

import soundfile as sf


def main(limit: int | None = None):
    cfg = load_config("config.yaml")
    base = Path("samples/wake_word")
    rows = []
    count = 0
    for sub in ("positive", "negative"):
        d = base / sub
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if limit is not None and count >= limit:
                break
            if f.suffix.lower() not in [".wav", ".flac", ".mp3"]:
                continue
            audio, sr = sf.read(f)
            res = transcribe_chunk(audio, cfg, sr=sr)
            words = res.get("words", [])
            decoder = res.get("decoder_probs", {}) or {}
            # flatten words to simple strings
            wstr = ";".join([str(w[0]) if isinstance(w, (list, tuple)) else str(w.get("word", "")) for w in words])
            rows.append({"file": str(f), "detected_words": wstr, "decoder_probs": json.dumps(decoder, ensure_ascii=False)})
            count += 1

    out = Path("decoder_probs_report.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "detected_words", "decoder_probs"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {out.absolute()} ({len(rows)} entries)")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="Max number of files to process (positive+negative combined)")
    args = p.parse_args()
    main(limit=args.limit)
