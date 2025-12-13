#!/usr/bin/env python
"""
Fast wake-word evaluation tool with threshold sweep.

- Mock mode (default): uses sidecar transcripts (*.txt) next to audio files; no model needed.
- Real mode (--real): uses faster-whisper via asr.pipeline.transcribe_chunk if available.

Outputs a CSV under logs/ and prints a compact summary with FRR/FAR/latency and PASS/FAIL if baseline present.
"""
from __future__ import annotations
import argparse
import csv
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Local imports
from pathlib import Path
import sys as _sys

# Ensure repository root is on sys.path for `asr.*` imports when run directly
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))

from asr.config import load_config, Cfg
from asr.kws import score_wake_word

# Optional imports for real mode
try:
    import soundfile as sf
except Exception:
    sf = None  # type: ignore

try:
    import numpy as np
except Exception:
    np = None  # type: ignore

try:
    from asr import pipeline as _pipeline
except Exception:
    _pipeline = None  # type: ignore


def _find_files(root: Path) -> Dict[str, List[Path]]:
    pos = (root / "positive")
    neg = (root / "negative")
    def _collect(p: Path) -> List[Path]:
        if not p.exists():
            return []
        return [x for x in p.rglob("*") if x.suffix.lower() in (".wav", ".flac", ".mp3", ".m4a")]
    return {"positive": _collect(pos), "negative": _collect(neg)}


def _read_sidecar_transcript(audio_path: Path) -> str | None:
    t = audio_path.with_suffix(".txt")
    if t.exists():
        try:
            return t.read_text(encoding="utf-8").strip()
        except Exception:
            return None
    return None


def _words_from_text(text: str) -> List[Tuple[str, float, float]]:
    toks = [t.strip() for t in text.split() if t.strip()]
    return [(t, 0.0, 0.0) for t in toks]


def _transcribe_real(audio_path: Path, cfg: Cfg) -> Dict[str, Any]:
    if _pipeline is None or sf is None:
        return {"text": "", "words": [], "decoder_probs": {}}
    try:
        audio, sr = sf.read(str(audio_path))
    except Exception:
        return {"text": "", "words": [], "decoder_probs": {}}
    try:
        return _pipeline.transcribe_chunk(audio, cfg, sr=int(sr))
    except Exception:
        return {"text": "", "words": [], "decoder_probs": {}}


def _detect_for_file(audio_path: Path, kw: str, cfg: Cfg, real: bool) -> Tuple[List[Tuple[str, float, float]], Dict[str, float]]:
    if real:
        res = _transcribe_real(audio_path, cfg)
        words = res.get("words", [])
        decoder_probs = res.get("decoder_probs", {}) or {}
        return words, decoder_probs
    # mock mode: sidecar transcript only
    text = _read_sidecar_transcript(audio_path)
    if text:
        return _words_from_text(text), {}
    # no transcript available
    return [], {}


def _sweep_thresholds(files: Dict[str, List[Path]], kw: str, cfg: Cfg, real: bool, thresholds: List[float]) -> List[Dict[str, Any]]:
    # candidates list: include canonical kw plus variants (lowercased)
    s = cfg.settings()
    kws_cfg = s.get("kws", {})
    variants = list(set([kw.lower()] + [str(v).lower() for v in kws_cfg.get("variants", [])]))
    rows: List[Dict[str, Any]] = []

    # cache detections per file at all thresholds by computing raw confidences once
    cache: Dict[Path, Dict[str, Any]] = {}

    for label in ("positive", "negative"):
        for ap in files.get(label, []):
            words, decoder_probs = _detect_for_file(ap, kw, cfg, real)
            if not words:
                cache[ap] = {"label": label, "hits": [], "latency": None}
                continue
            # compute best hit over words once (hits already have confidence)
            hits = score_wake_word(words, variants, decoder_probs=decoder_probs, cfg=cfg)
            # earliest detection time
            lat = None
            try:
                if hits:
                    lat = min(h.end_time for h in hits if hasattr(h, "end_time"))
            except Exception:
                lat = None
            cache[ap] = {"label": label, "hits": hits, "latency": lat}

    for th in thresholds:
        tp = fp = tn = fn = 0
        latencies: List[float] = []
        for ap, rec in cache.items():
            label = rec["label"]
            hits = rec["hits"]
            lat = rec["latency"]
            detected = any(h.confidence >= th for h in hits)
            if label == "positive":
                if detected:
                    tp += 1
                    if lat is not None and lat >= 0:
                        latencies.append(float(lat) * 1000.0)  # ms
                else:
                    fn += 1
            else:
                if detected:
                    fp += 1
                else:
                    tn += 1
        pos = tp + fn
        neg = tn + fp
        frr = (fn / pos) if pos else 0.0
        far = (fp / neg) if neg else 0.0
        prec = (tp / (tp + fp)) if (tp + fp) else 0.0
        rec = (tp / pos) if pos else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        avg_lat = (sum(latencies) / len(latencies)) if latencies else 0.0
        rows.append({
            "threshold": round(th, 3),
            "FRR": round(frr, 4),
            "FAR": round(far, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "F1": round(f1, 4),
            "avg_latency_ms": round(avg_lat, 1),
            "n_pos": pos,
            "n_neg": neg,
        })
    return rows


def _write_csv(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _load_baseline(path: Path) -> Dict[float, Dict[str, float]]:
    if not path.exists():
        return {}
    out: Dict[float, Dict[str, float]] = {}
    try:
        with path.open("r", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                th = float(row.get("threshold", 0))
                out[th] = {k: float(row[k]) for k in ("FRR", "FAR", "F1") if k in row}
    except Exception:
        return {}
    return out


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wake-word eval with threshold sweep (mock by default)")
    ap.add_argument("--dir", required=True, help="Data root with positive/ and negative/ subfolders")
    ap.add_argument("--kw", default="calyx", help="Wake-word keyword (case-insensitive)")
    ap.add_argument("--cfg", default=str((Path(__file__).resolve().parents[1] / "config.yaml")), help="Path to config.yaml")
    ap.add_argument("--real", action="store_true", help="Use real decoding via faster-whisper (requires models)")
    ap.add_argument("--step", type=float, default=0.05, help="Threshold step size (default 0.05)")
    ap.add_argument("--out", default=None, help="Output CSV path (default logs/eval_wake_word_<ts>.csv)")
    ap.add_argument("--baseline", default=str(Path("logs") / "eval_wake_word_baseline.csv"), help="Optional baseline CSV to compare against")
    args = ap.parse_args(argv)

    root = Path(args.dir)
    if not root.exists():
        print(f"Data dir not found: {root}")
        return 2

    cfg = load_config(args.cfg)
    kw = str(args.kw).strip()
    files = _find_files(root)
    thresholds = [round(x, 3) for x in list(_frange(0.0, 1.0, args.step))]
    if thresholds[-1] != 1.0:
        thresholds.append(1.0)

    t0 = time.time()
    rows = _sweep_thresholds(files, kw, cfg, args.real, thresholds)
    dt = time.time() - t0

    # write CSV
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("logs") / f"eval_wake_word_{int(time.time())}.csv"
    _write_csv(rows, out_path)

    # Print compact summary at trigger threshold if configured
    th_cfg = cfg.settings().get("kws", {}).get("trigger_threshold", 0.85)
    th_row = min(rows, key=lambda r: abs(r["threshold"] - th_cfg)) if rows else None
    if th_row:
        print(f"Summary at threshold≈{th_cfg:.2f}: FRR={th_row['FRR']:.3f} FAR={th_row['FAR']:.3f} F1={th_row['F1']:.3f} avg_latency_ms={th_row['avg_latency_ms']:.1f}")

    # Baseline comparison (optional)
    baseline_map = _load_baseline(Path(args.baseline)) if args.baseline else {}
    status = 0
    if baseline_map and th_row is not None:
        # find closest threshold in baseline map
        th_base = min(baseline_map.keys(), key=lambda t: abs(t - th_row["threshold"]))
        base = baseline_map.get(th_base, {})
        frr_delta = th_row["FRR"] - base.get("FRR", th_row["FRR"])
        far_delta = th_row["FAR"] - base.get("FAR", th_row["FAR"])
        print(f"Baseline deltas at th≈{th_base:.2f}: dFRR={frr_delta:+.3f} dFAR={far_delta:+.3f}")
        # simple regression rule: don't allow >2% worse on either rate
        if frr_delta > 0.02 or far_delta > 0.02:
            print("FAIL: Regression detected vs baseline (>2% on FRR or FAR)")
            status = 1
        else:
            print("PASS: No regression vs baseline")
    else:
        print("PASS: Eval completed (no baseline provided)")

    # Runtime info
    print(f"Eval runtime: {dt:.2f}s | Files: +{len(files.get('positive', []))} / -{len(files.get('negative', []))} | Mode: {'real' if args.real else 'mock'}")
    return status


def _frange(start: float, stop: float, step: float):
    x = start
    # protect against tiny/zero step
    s = step if step > 1e-9 else 0.05
    while x <= stop + 1e-9:
        yield round(x, 6)
        x += s


if __name__ == "__main__":
    sys.exit(main())
