#!/usr/bin/env python3
"""
CP10 — The Whisperer

Purpose
- Suggest ASR decoding bias and KWS weight tweaks to improve wake-word robustness with minimal risk.

Behavior
- Emits watcher-compatible heartbeats at outgoing/cp10.lock
- Scans samples/wake_word/{positive,negative} for availability
- Optionally reads evaluation CSVs under logs/ (eval_wake_word*.csv) to infer common failure modes
- Writes recommendations to outgoing/whisperer/recommendations.{json,md}

Heuristics (safe defaults when data is limited)
- If many false negatives: increase phonetic weight slightly and lower detection threshold a notch
- If many false positives: decrease phonetic weight slightly and raise threshold a notch
- If balanced or unknown: prefer neutral tweaks and suggest running tools/eval_wake_word.py --mock

No external dependencies; pure stdlib. Does not edit config.yaml; outputs suggested deltas only.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "cp10.lock"
W_DIR = OUT / "whisperer"
REC_JSON = W_DIR / "recommendations.json"
REC_MD = W_DIR / "recommendations.md"
SAMPLES_POS = ROOT / "samples" / "wake_word" / "positive"
SAMPLES_NEG = ROOT / "samples" / "wake_word" / "negative"
LOGS = ROOT / "logs"
VERSION = "0.1.0"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "cp10",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _list_csvs(logs_dir: Path) -> List[Path]:
    if not logs_dir.exists():
        return []
    files = []
    for p in logs_dir.glob("eval_wake_word*.csv"):
        files.append(p)
    return sorted(files)


def _load_eval(csv_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(dict(r))
    except Exception:
        pass
    return rows


def _coerce_bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "t", "yes", "y"}:
            return True
        if s in {"0", "false", "f", "no", "n"}:
            return False
    return None


def _analyze_eval_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Try to infer truth/pred from common field names
    pos = neg = tp = tn = fp = fn = 0
    for r in rows:
        label = (r.get("label") or r.get("truth") or r.get("target") or "").strip().lower()
        pred = r.get("pred") if r.get("pred") is not None else r.get("detected")
        if pred is None:
            # try score threshold heuristic
            try:
                score = float(r.get("score") or r.get("prob") or 0.0)
                pred = score >= 0.5
            except Exception:
                pred = None
        pred_b = _coerce_bool(pred)
        is_pos = label in {"pos", "positive", "1", "true", "wake", "hit"}
        is_neg = label in {"neg", "negative", "0", "false", "nonwake", "miss"}
        if not (is_pos or is_neg):
            # skip ambiguous
            continue
        if is_pos:
            pos += 1
            if pred_b is True:
                tp += 1
            elif pred_b is False:
                fn += 1
        else:
            neg += 1
            if pred_b is False:
                tn += 1
            elif pred_b is True:
                fp += 1
    total = pos + neg
    prec = (tp / (tp + fp)) if (tp + fp) > 0 else None
    rec = (tp / (tp + fn)) if (tp + fn) > 0 else None
    f1 = ((2 * prec * rec) / (prec + rec)) if (prec and rec and (prec + rec) > 0) else None
    return {
        "n": total,
        "pos": pos,
        "neg": neg,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 3) if isinstance(prec, float) else None,
        "recall": round(rec, 3) if isinstance(rec, float) else None,
        "f1": round(f1, 3) if isinstance(f1, float) else None,
    }


def _suggest_from_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    # Default suggestions
    suggest = {
        "bias": {"initial_prompt_strength": "+0.1"},
        "kws": {"threshold": "+0.0", "weights": {"phonetic": "+0.0", "decoder": "+0.0", "levenshtein": "+0.0"}},
        "notes": [],
    }
    fn = int(stats.get("fn") or 0)
    fp = int(stats.get("fp") or 0)
    pos = int(stats.get("pos") or 0)
    neg = int(stats.get("neg") or 0)
    if pos + neg == 0:
        suggest["notes"].append("No labeled data found; run tools/eval_wake_word.py --mock to generate a baseline.")
        return suggest
    # Heuristics
    if fn > fp:
        # Too many misses: boost recall
        suggest["kws"]["threshold"] = "-0.05"
        suggest["kws"]["weights"]["phonetic"] = "+0.05"
        suggest["bias"]["initial_prompt_strength"] = "+0.1"
        suggest["notes"].append("More false negatives: lower threshold slightly, weight phonetics more, nudge bias up.")
    elif fp > fn:
        # Too many false alarms: boost precision
        suggest["kws"]["threshold"] = "+0.05"
        suggest["kws"]["weights"]["phonetic"] = "-0.05"
        suggest["bias"]["initial_prompt_strength"] = "+0.0"
        suggest["notes"].append("More false positives: raise threshold slightly and dial phonetics down.")
    else:
        suggest["notes"].append("Balanced errors: keep current threshold; consider a small +0.1 bias only if recall matters." )
    return suggest


def recommend() -> Dict[str, Any]:
    # Check samples availability
    samples = {
        "positive": SAMPLES_POS.exists() and any(SAMPLES_POS.glob("*.wav")),
        "negative": SAMPLES_NEG.exists() and any(SAMPLES_NEG.glob("*.wav")),
    }
    # Read latest evaluation if present
    csvs = _list_csvs(LOGS)
    stats = None
    src = None
    for p in reversed(csvs):
        rows = _load_eval(p)
        s = _analyze_eval_rows(rows)
        if s.get("n", 0) > 0:
            stats = s
            src = str(p.relative_to(ROOT))
            break
    if stats is None:
        stats = {"n": 0, "pos": 0, "neg": 0, "tp": 0, "tn": 0, "fp": 0, "fn": 0}
    suggest = _suggest_from_stats(stats)
    return {
        "samples": samples,
        "stats": stats,
        "source_csv": src,
        "suggest": suggest,
        "actions": [
            "If no data: run `python tools/eval_wake_word.py --mock --out logs/eval_wake_word_mock.csv`",
            "Apply small deltas only; re-evaluate after each change.",
        ],
    }


def write_recommendations(data: Dict[str, Any]) -> Dict[str, Any]:
    _write_json(REC_JSON, data)
    lines = ["# CP10 Whisperer Recommendations\n\n"]
    smp = data.get("samples", {})
    lines.append(f"- samples: positive={smp.get('positive')} negative={smp.get('negative')}\n")
    st = data.get("stats", {})
    lines.append(f"- stats: n={st.get('n')} tp={st.get('tp')} fp={st.get('fp')} fn={st.get('fn')} precision={st.get('precision')} recall={st.get('recall')} f1={st.get('f1')}\n")
    if data.get("source_csv"):
        lines.append(f"- source: {data.get('source_csv')}\n")
    lines.append("\n## Suggested deltas\n\n")
    sug = data.get("suggest", {})
    lines.append(f"- bias.initial_prompt_strength: {sug.get('bias',{}).get('initial_prompt_strength')}\n")
    kw = sug.get("kws", {})
    lines.append(f"- kws.threshold: {kw.get('threshold')}\n")
    w = kw.get("weights", {})
    lines.append(f"- kws.weights: phonetic {w.get('phonetic')}, decoder {w.get('decoder')}, levenshtein {w.get('levenshtein')}\n\n")
    notes = sug.get("notes", [])
    if notes:
        lines.append("Notes:\n")
        for n in notes:
            lines.append(f"- {n}\n")
    lines.append("\n## Next actions\n\n")
    for a in data.get("actions", []):
        lines.append(f"- {a}\n")
    _append_md(REC_MD, "".join(lines))
    return {"open_path": str(REC_MD.relative_to(ROOT)), "json": str(REC_JSON.relative_to(ROOT))}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CP10 Whisperer — suggest bias/KWS tweaks")
    ap.add_argument("--interval", type=float, default=20.0)
    ap.add_argument("--max-iters", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    i = 0
    while True:
        i += 1
        rec = recommend()
        paths = write_recommendations(rec)
        status = "observing"
        st = rec.get("stats", {})
        fp = int(st.get("fp") or 0)
        fn = int(st.get("fn") or 0)
        if st.get("n", 0) > 0:
            trend = "fp>fn" if fp > fn else ("fn>fp" if fn > fp else "balanced")
            message = f"cp6/cp7: KWS {trend}; see whisperer/recommendations.md"
        else:
            message = "cp7: awaiting eval data (mock ok)"
        _write_hb("analyze", status=status, extra={
            "status_message": message,
            "summary": {"n": rec.get("stats", {}).get("n"), "samples": rec.get("samples")},
            "open_path": paths.get("open_path"),
        })
        if not args.quiet:
            print(f"[CP10] cycle={i} -> {paths.get('open_path')}")
        if args.max_iters and i >= int(args.max_iters):
            break
        time.sleep(max(0.5, float(args.interval)))

    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
