#!/usr/bin/env python3
"""
CBO Mailbox Poller
- Watches /outgoing/User1/ for new operator letters
- Writes immediate auto-ack markdown responses with latency metadata
- Persists lightweight state to avoid duplicate acknowledgments
"""
from __future__ import annotations

import argparse
import json
import os
import textwrap
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
MAILBOX_DIR = ROOT / "outgoing" / "User1"
STATE_FILE = ROOT / "state" / "mailbox_poller_state.json"
LOG_FILE = ROOT / "logs" / "mailbox_poller.log"
CHAT_CONTEXT = ROOT / "outgoing" / "User1" / "chat_context_summary.md"
MAILBOX_MODEL_ID = os.environ.get("CALYX_MAILBOX_LLM", "tinyllama-1.1b-chat-q5_k_m")


class LLMResponder:
    """Local LLM wrapper to craft CBO replies."""

    def __init__(self) -> None:
        self.llm_handle = None
        self.model_id: Optional[str] = None
        self.model_name: Optional[str] = None
        self.model_loaded = False

    def _load_model(self) -> bool:
        if self.model_loaded and self.llm_handle:
            return True
        try:
            from llama_cpp import Llama
        except ImportError:
            return False

        manifest_path = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"
        if not manifest_path.exists():
            return False

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        models = manifest.get("models") or []
        target = next((m for m in models if m.get("id") == MAILBOX_MODEL_ID), None)
        if not target:
            target = next((m for m in models if m.get("role") == "general"), None)
        if not target and models:
            target = models[0]
        if not target:
            return False

        model_path = ROOT / target.get("filename", "")
        if not model_path.exists():
            return False

        try:
            try:
                from tools.gpu_utils import get_gpu_layer_count

                gpu_layers = get_gpu_layer_count()
            except Exception:
                gpu_layers = 0

            kwargs = {
                "model_path": str(model_path),
                "n_ctx": 2048,
                "temperature": 0.4,
                "top_p": 0.9,
                "repeat_penalty": 1.05,
                "verbose": False,
            }
            if gpu_layers and gpu_layers > 0:
                kwargs["n_gpu_layers"] = gpu_layers

            from llama_cpp import Llama  # type: ignore  # noqa: E402

            _log(f"Loading LLM from {model_path} (gpu_layers={kwargs.get('n_gpu_layers', 0)})")
            self.llm_handle = Llama(**kwargs)
            self.model_loaded = True
            self.model_id = target.get("id")
            self.model_name = Path(target.get("filename", "")).name
            return True
        except Exception as exc:
            _log(f"LLM load failed: {exc!r}")
            _log(traceback.format_exc().strip())
            self.llm_handle = None
            self.model_loaded = False
            return False

    def _read_snippet(self, path: Path, limit: int = 1200) -> str:
        if not path.exists():
            return ""
        try:
            data = path.read_text(encoding="utf-8")
        except Exception:
            return ""
        return data[:limit]

    def _system_context(self) -> str:
        parts: List[str] = []
        summary = self._read_snippet(CHAT_CONTEXT, limit=900)
        if summary:
            parts.append("Operator briefing:\n" + summary)

        agii_path = ROOT / "reports" / "agii_report_latest.md"
        agii = self._read_snippet(agii_path, limit=400)
        if agii:
            parts.append("Latest AGII report excerpt:\n" + agii)

        intercept_dir = ROOT / "reports" / "intercepts"
        recent_logs: List[Path] = sorted(intercept_dir.glob("*.json"))[-1:]
        if recent_logs:
            for p in recent_logs:
                try:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                reasons = rec.get("decision", {}).get("reasons") or []
                snippet = "; ".join(reasons)[:200]
                parts.append(
                    f"Intercept log {p.name}: allow={rec.get('decision', {}).get('allow')} "
                    f"severity={rec.get('decision', {}).get('severity')} reasons={snippet}"
                )

        load_mode = ROOT / "state" / "load_mode.json"
        if load_mode.exists():
            try:
                lm = json.loads(load_mode.read_text(encoding="utf-8"))
                parts.append(f"Load mode: {lm.get('mode')} ({lm.get('notes', '')})")
            except Exception:
                pass

        return "\n\n".join(parts[-6:])

    def _history_context(self, history: List[Dict[str, str]]) -> str:
        if not history:
            return "No prior mailbox conversation."
        lines: List[str] = []
        for item in history[-4:]:
            letter = (item.get("letter") or "").strip()
            resp = (item.get("response") or "").strip()
            ts = item.get("ts")
            if letter:
                lines.append(f"[Operator {ts}] {letter}")
            if resp:
                lines.append(f"[CBO {ts}] {resp}")
        return "\n".join(lines[-12:])

    def generate_reply(
        self, letter: Letter, history: List[Dict[str, str]]
    ) -> Dict[str, str]:
        context = self._system_context()
        convo = self._history_context(history)
        prompt = f"""You are Calyx Bridge Overseer (CBO), the disciplined overseer of Station Calyx.

System context:
{context}

Mailbox conversation history:
{convo}

Operator letter received at {datetime.fromtimestamp(letter.mtime, tz=timezone.utc).isoformat()}:
{letter.body}

Respond in markdown with concise sections (Status/Plan/Acks when relevant). Stay factual, reference current intercept + sandbox plans, and always confirm actionable next steps."""
        prompt += "\n\nUse this template:\n## Status\n## Interceptor & Sandbox\n## Next Steps\n"

        if len(prompt) > 3500:
            prompt = prompt[-3500:]

        if self._load_model() and self.llm_handle:
            try:
                result = self.llm_handle(
                    prompt,
                    max_tokens=400,
                    stop=["Operator:", "User1>", "\n\nOperator"],
                )
                text = (
                    result.get("choices", [{}])[0].get("text", "").strip()
                    if isinstance(result, dict)
                    else ""
                )
                if text:
                    return {
                        "text": text,
                        "model_id": self.model_id or "unknown_model",
                        "mode": "llm",
                    }
                _log("LLM produced empty output; falling back.")
            except Exception as exc:
                _log(f"LLM inference failed: {exc}")

        fallback = (
            "Unable to use the LLM at this moment. Receipt acknowledged; "
            "interceptor + sandbox work continues and a detailed follow-up will arrive shortly."
        )
        return {
            "text": fallback,
            "model_id": "fallback-template",
            "mode": "fallback",
        }


RESPONDER = LLMResponder()


@dataclass
class Letter:
    path: Path
    body: str
    mtime: float
    first_line: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dirs() -> None:
    MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _log(message: str) -> None:
    timestamp = _utc_now().isoformat()
    line = f"[{timestamp}] {message}"
    print(line)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:
        pass


def _load_state() -> Dict[str, object]:
    if not STATE_FILE.exists():
        return {"processed": {}, "initialized_ts": _utc_now().timestamp(), "history": []}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if "processed" not in data or not isinstance(data["processed"], dict):
            data["processed"] = {}
        if "initialized_ts" not in data:
            data["initialized_ts"] = _utc_now().timestamp()
        if "history" not in data or not isinstance(data["history"], list):
            data["history"] = []
        return data
    except Exception:
        return {"processed": {}, "initialized_ts": _utc_now().timestamp(), "history": []}


def _save_state(state: Dict[str, object]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as exc:
        _log(f"Failed to persist state: {exc}")


def _summarize(body: str, width: int = 260) -> str:
    compact = " ".join(body.split())
    if not compact:
        return "(no body text)"
    return textwrap.shorten(compact, width=width, placeholder="…")


def _normalize_stem(name: str) -> str:
    sanitized = []
    for ch in name.lower():
        if ch.isalnum() or ch in ("-", "_"):
            sanitized.append(ch)
        else:
            sanitized.append("-")
    return "".join(sanitized).strip("-") or "letter"


def _looks_like_operator_letter(text: str) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        return lower.startswith("user1>") or lower.startswith("cgpt>")
    return False


def _gather_letters(state: Dict[str, object], include_existing: bool) -> List[Letter]:
    processed = state.get("processed", {})
    baseline = 0.0 if include_existing else float(state.get("initialized_ts", 0.0))
    letters: List[Letter] = []
    for path in sorted(p for p in MAILBOX_DIR.iterdir() if p.is_file()):
        if path.name.lower().startswith(("cbo_", "station_", "auto_ack_", "intercept_", "cbo-auto")):
            continue
        try:
            body = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            continue
        if not body or not _looks_like_operator_letter(body):
            continue
        mtime = path.stat().st_mtime
        prev = processed.get(path.name, {})
        prev_mtime = prev.get("mtime")
        if prev_mtime is not None and mtime <= float(prev_mtime):
            continue
        if not include_existing and baseline and mtime < baseline:
            continue
        first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        letters.append(Letter(path=path, body=body, mtime=mtime, first_line=first_line))
    return letters


def _write_response(
    letter: Letter,
    detection_ts: datetime,
    interval_s: float,
    reply_text: str,
    model_id: str,
    mode: str,
) -> Path:
    response_ts = _utc_now()
    letter_ts = datetime.fromtimestamp(letter.mtime, tz=timezone.utc)
    latency_detect = max(0.0, (detection_ts - letter_ts).total_seconds())
    response_latency = max(0.0, (response_ts - detection_ts).total_seconds())
    snippet = _summarize(letter.body)
    resp_name = f"CBO_response_{response_ts.strftime('%Y%m%d-%H%M%S')}_{_normalize_stem(letter.path.stem)}.md"
    resp_path = MAILBOX_DIR / resp_name
    content = f"""# Station Calyx - CBO Response

**Letter:** `{letter.path.name}`
**Model:** {model_id}
**Mode:** {mode}
**Detected (UTC):** {detection_ts.isoformat()}
**Responded (UTC):** {response_ts.isoformat()}
**Detection latency:** {latency_detect:.1f}s
**Response latency:** {response_latency:.1f}s

> {letter.first_line}

**Letter summary:** {snippet}

---

## CBO Reply

{reply_text.strip()}

---
_Auto-response generated by `tools/mailbox_poller.py` (interval {interval_s:.1f}s)._"""
    resp_path.write_text(content, encoding="utf-8")
    return resp_path


def process_cycle(state: Dict[str, object], interval_s: float, include_existing: bool) -> int:
    state.setdefault("processed", {})
    detection_ts = _utc_now()
    letters = _gather_letters(state, include_existing=include_existing)
    processed = 0
    for letter in letters:
        reply = RESPONDER.generate_reply(letter, state.get("history", []))
        resp_path = _write_response(
            letter,
            detection_ts,
            interval_s,
            reply_text=reply["text"],
            model_id=reply["model_id"],
            mode=reply["mode"],
        )
        processed += 1
        state["processed"][letter.path.name] = {
            "mtime": letter.mtime,
            "response_path": str(resp_path.relative_to(ROOT)),
            "model_id": reply["model_id"],
            "mode": reply["mode"],
            "responded_ts": _utc_now().isoformat(),
        }
        history = state.setdefault("history", [])
        history.append(
            {
                "ts": detection_ts.isoformat(),
                "letter": letter.body,
                "response": reply["text"],
            }
        )
        if len(history) > 10:
            del history[:-10]
        _log(f"Responded to {letter.path.name} -> {resp_path.name} ({reply['mode']})")
    state["last_cycle_ts"] = detection_ts.isoformat()
    _save_state(state)
    return processed


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor /outgoing/User1 for new letters.")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds (default 2s)")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Process a single cycle then exit",
    )
    parser.add_argument(
        "--process-existing",
        action="store_true",
        help="Process all matching letters regardless of initial timestamp gate",
    )
    args = parser.parse_args()

    _ensure_dirs()
    state = _load_state()
    include_existing = bool(args.process_existing or not STATE_FILE.exists())

    import sys

    _log(
        f"Mailbox poller start (interval={args.interval:.1f}s, include_existing={include_existing}) "
        f"[python={sys.version.split()[0]}]"
    )

    try:
        while True:
            processed = process_cycle(state, args.interval, include_existing=include_existing)
            include_existing = False
            if args.run_once:
                break
            time.sleep(max(0.5, args.interval))
    except KeyboardInterrupt:
        _log("Mailbox poller interrupted by user")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
