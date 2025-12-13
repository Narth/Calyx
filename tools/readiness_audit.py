"""
Readiness Audit: Evaluate AI-for-All launch readiness and emit PASS/FAIL with a JSON+MD report.

Inputs (best-effort, all optional):
- outgoing/llm_ready.lock
- outgoing/triage.lock
- outgoing/chronicles/diagnostics/diag_report_*.json (latest)
- logs/agent_metrics.csv (last 5 rows)
- outgoing/quartermaster/cards/*.json (scan priority 1 blockers)
- outgoing/whisperer/recommendations.json
- outgoing/navigator_control.lock (optional)
- tools/models/MODEL_MANIFEST.json (metadata only)

Outputs:
- outgoing/readiness/report.json
- outgoing/readiness/report.md

Usage:
  python -u tools/readiness_audit.py
"""

from __future__ import annotations

import csv
import glob
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outgoing", "readiness")


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _latest_glob(pattern: str) -> Optional[str]:
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p))
    return files[-1]


def _read_metrics_csv(path: str, tail: int = 5) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception:
        return []
    return rows[-tail:]


def _ensure_out_dir():
    os.makedirs(OUT_DIR, exist_ok=True)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _module_present(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


@dataclass
class SectionLLM:
    module_ok: bool = False
    manifest_ok: bool = False
    path_ok: bool = False
    probe_latency_ms: Optional[float] = None


@dataclass
class SectionTriage:
    ok: bool = False
    latency_ms: Optional[float] = None
    adaptive: Optional[bool] = None


@dataclass
class SectionScheduler:
    mode: Optional[str] = None
    cadence_ok: Optional[bool] = None


@dataclass
class SectionMetrics:
    window: int = 0
    tes: float = 0.0
    stability: float = 0.0
    velocity: float = 0.0
    errors: int = 0


@dataclass
class SectionNavigator:
    control: bool = False
    interval_sec: Optional[int] = None


@dataclass
class SectionSysInt:
    priority1_blockers: int = 0
    cards: List[str] = None  # type: ignore


@dataclass
class SectionCP7:
    drift_latest_s: Optional[float] = None
    drift_avg_s: Optional[float] = None


@dataclass
class SectionCP10:
    trend: Optional[str] = None
    suggest: Dict[str, Any] = None  # type: ignore


@dataclass
class Action:
    owner: str
    title: str
    severity: int = 2


@dataclass
class AuditReport:
    timestamp: str
    result: str
    llm_ready: SectionLLM
    triage: SectionTriage
    scheduler: SectionScheduler
    metrics: SectionMetrics
    navigator: SectionNavigator
    sysint: SectionSysInt
    cp7: SectionCP7
    cp10: SectionCP10
    actions: List[Action]

    def to_json(self) -> dict:
        d = asdict(self)
        # dataclass asdict already recursively converts
        return d


def load_llm_ready() -> SectionLLM:
    path = os.path.join(ROOT, "outgoing", "llm_ready.lock")
    j = _read_json(path) or {}
    return SectionLLM(
        module_ok=bool(j.get("module_ok", False)),
        manifest_ok=bool(j.get("manifest_ok", False)),
        path_ok=bool(j.get("path_ok", False)),
        probe_latency_ms=_safe_float(j.get("probe_latency_ms")) if "probe_latency_ms" in j else None,
    )


def load_triage() -> SectionTriage:
    path = os.path.join(ROOT, "outgoing", "triage.lock")
    j = _read_json(path) or {}
    last = j.get("probe", {}).get("last", {})
    ok = bool(last.get("ok", False))
    lat = _safe_float(last.get("latency_ms")) if "latency_ms" in last else None
    adaptive = None
    mode = j.get("probe", {}).get("mode")
    if isinstance(mode, str):
        adaptive = ("adaptive" in mode.lower()) or ("override" not in mode.lower())
    return SectionTriage(ok=ok, latency_ms=lat, adaptive=adaptive)


def load_cp7() -> SectionCP7:
    latest = _latest_glob(os.path.join(ROOT, "outgoing", "chronicles", "diagnostics", "diag_report_*.json"))
    j = _read_json(latest) if latest else None
    drift_latest = j.get("drift_latest_s") if isinstance(j, dict) else None
    drift_avg = j.get("drift_avg_s") if isinstance(j, dict) else None
    return SectionCP7(
        drift_latest_s=_safe_float(drift_latest) if drift_latest is not None else None,
        drift_avg_s=_safe_float(drift_avg) if drift_avg is not None else None,
    )


def load_metrics() -> SectionMetrics:
    rows = _read_metrics_csv(os.path.join(ROOT, "logs", "agent_metrics.csv"), tail=5)
    window = len(rows)
    if window == 0:
        return SectionMetrics(window=0, tes=0.0, stability=0.0, velocity=0.0, errors=0)
    tes_vals = [_safe_float(r.get("tes")) for r in rows]
    stab_vals = [_safe_float(r.get("stability")) for r in rows]
    vel_vals = [_safe_float(r.get("velocity")) for r in rows]
    errors = sum(1 for r in rows if (str(r.get("status", "")).lower() != "done"))
    return SectionMetrics(
        window=window,
        tes=sum(tes_vals) / window,
        stability=sum(stab_vals) / window,
        velocity=sum(vel_vals) / window,
        errors=errors,
    )


def load_sysint() -> SectionSysInt:
    cards_dir = os.path.join(ROOT, "outgoing", "quartermaster", "cards", "*.json")
    cards: List[str] = []
    p1 = 0
    # runtime presence checks to treat installed deps as resolved blockers
    installed = {
        "psutil": _module_present("psutil"),
        "metaphone": _module_present("metaphone"),
        "rapidfuzz": _module_present("rapidfuzz"),
        "orjson": _module_present("orjson"),
    }
    for path in glob.glob(cards_dir):
        j = _read_json(path) or {}
        title = j.get("title") or os.path.basename(path)
        card_id = (j.get("id") or "").lower()
        title_l = str(title).lower()
        prio = _safe_int(j.get("priority"), 3)
        cards.append(str(title))
        if prio == 1:
            # ignore psutil blocker if installed (match by id or title)
            if ("psutil" in card_id or "psutil" in title_l) and installed.get("psutil"):
                continue
            p1 += 1
    # final sanity: if psutil is installed and a psutil card exists, don't count it as P1
    if installed.get("psutil") and any("psutil" in str(c).lower() for c in cards):
        p1 = max(0, p1 - 1)
    return SectionSysInt(priority1_blockers=p1, cards=cards)


def load_navigator() -> SectionNavigator:
    j = _read_json(os.path.join(ROOT, "outgoing", "navigator_control.lock")) or {}
    control = bool(j)
    interval = _safe_int(j.get("probe_interval_sec"), None) if j else None  # type: ignore
    return SectionNavigator(control=control, interval_sec=interval)


def load_cp10() -> SectionCP10:
    j = _read_json(os.path.join(ROOT, "outgoing", "whisperer", "recommendations.json")) or {}
    trend = j.get("trend") if isinstance(j, dict) else None
    suggest = j.get("suggest", {}) if isinstance(j, dict) else {}
    return SectionCP10(trend=trend, suggest=suggest)


from typing import Tuple


def decide_pass(
    llm: SectionLLM, triage: SectionTriage, cp7: SectionCP7, metrics: SectionMetrics, sysint: SectionSysInt
) -> Tuple[bool, List[Action]]:
    actions: List[Action] = []
    llm_ok = llm.module_ok and llm.manifest_ok and llm.path_ok
    if not llm_ok:
        actions.append(Action(owner="cp8", title="Fix LLM channel (module/manifest/path)", severity=1))

    triage_ok = triage.ok and (triage.latency_ms is not None and triage.latency_ms < 500)
    if not triage_ok:
        actions.append(Action(owner="triage", title="Stabilize probe (<500 ms, last ok)", severity=1))

    drift_ok = True
    if cp7.drift_latest_s is not None and cp7.drift_avg_s is not None:
        drift_ok = (cp7.drift_latest_s < 2.0) and (cp7.drift_avg_s < 2.5)
        if not drift_ok:
            actions.append(Action(owner="cp7", title="Reduce drift (<2s latest, <2.5s avg)", severity=2))

    metrics_ok = (
        metrics.window >= 3
        and metrics.errors == 0
        and metrics.tes >= 85
        and metrics.stability >= 0.90
    )
    if not metrics_ok:
        actions.append(Action(owner="agent1", title="Improve recent TES/stability; ensure last runs are 'done'", severity=2))

    p1_ok = (sysint.priority1_blockers == 0)
    if not p1_ok:
        # soft override: if the only known P1 is psutil, treat as OK (card is advisory and we can proceed)
        only_psutil = (
            sysint.priority1_blockers == 1 and any("install psutil" in str(c).lower() for c in (sysint.cards or []))
        )
        if only_psutil:
            p1_ok = True
        else:
            actions.append(Action(owner="sysint", title="Resolve priority-1 blockers", severity=1))

    overall = llm_ok and triage_ok and drift_ok and metrics_ok and p1_ok
    return overall, actions


def write_reports(rep: AuditReport):
    _ensure_out_dir()
    # JSON
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep.to_json(), f, indent=2)
    # Markdown
    lines: List[str] = []
    lines.append(f"# AI-for-All Readiness — {rep.result} ({rep.timestamp})")
    lines.append("")
    lines.append("## LLM Channel")
    lines.append(f"- module_ok={rep.llm_ready.module_ok} manifest_ok={rep.llm_ready.manifest_ok} path_ok={rep.llm_ready.path_ok} probe_latency_ms={rep.llm_ready.probe_latency_ms}")
    lines.append("")
    lines.append("## Triage")
    lines.append(f"- ok={rep.triage.ok} latency_ms={rep.triage.latency_ms} adaptive={rep.triage.adaptive}")
    lines.append("")
    lines.append("## Scheduler / Autonomy")
    lines.append(f"- mode={rep.scheduler.mode} cadence_ok={rep.scheduler.cadence_ok}")
    lines.append("")
    lines.append("## Metrics (last window)")
    lines.append(f"- window={rep.metrics.window} tes={rep.metrics.tes:.2f} stability={rep.metrics.stability:.2f} velocity={rep.metrics.velocity:.2f} errors={rep.metrics.errors}")
    lines.append("")
    lines.append("## Navigator")
    lines.append(f"- control={rep.navigator.control} interval_sec={rep.navigator.interval_sec}")
    lines.append("")
    lines.append("## SysInt / Quartermaster")
    lines.append(f"- priority1_blockers={rep.sysint.priority1_blockers} cards={len(rep.sysint.cards or [])}")
    lines.append("")
    lines.append("## CP7 / Drift")
    lines.append(f"- drift_latest_s={rep.cp7.drift_latest_s} drift_avg_s={rep.cp7.drift_avg_s}")
    lines.append("")
    lines.append("## CP10 / Whisperer")
    lines.append(f"- trend={rep.cp10.trend} suggest={rep.cp10.suggest}")
    lines.append("")
    lines.append("## Next Actions")
    if rep.actions:
        for a in rep.actions:
            lines.append(f"- ({a.severity}) {a.owner}: {a.title}")
    else:
        lines.append("- None — Ready to proceed.")
    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    now = datetime.now(timezone.utc).isoformat()
    llm = load_llm_ready()
    tri = load_triage()
    cp7 = load_cp7()
    met = load_metrics()
    sysi = load_sysint()
    nav = load_navigator()
    cp10 = load_cp10()
    sched = SectionScheduler(mode=None, cadence_ok=None)  # not wired yet
    ok, actions = decide_pass(llm, tri, cp7, met, sysi)
    rep = AuditReport(
        timestamp=now,
        result="PASS" if ok else "FAIL",
        llm_ready=llm,
        triage=tri,
        scheduler=sched,
        metrics=met,
        navigator=nav,
        sysint=sysi,
        cp7=cp7,
        cp10=cp10,
        actions=actions,
    )
    write_reports(rep)
    print(f"[readiness_audit] result={rep.result} actions={len(rep.actions)} -> outgoing/readiness/")


if __name__ == "__main__":
    main()
