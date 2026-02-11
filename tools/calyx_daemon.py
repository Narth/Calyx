#!/usr/bin/env python3
"""
Calyx Daemon: watches governance/intents/inbox and auto-executes low-risk intents.

Usage:
  python tools/calyx_daemon.py --once   # run a single polling cycle and exit
  python tools/calyx_daemon.py          # run continuously

Behavior:
 - Poll governance/intents/inbox/*.json
 - For each intent, call governance_gate.validate_intent()
 - If validation passes and auto-approved per policy, execute allowed action
 - Write a result file to governance/intents/outbox/<intent_id>.result.json
 - Append to logs/executor/exec_log.jsonl
 - Move processed intents to governance/intents/processed/
Security:
 - fs_read paths are constrained to repository root (no directory traversal).
 - Only implements fs_read and repo_grep for now.
"""
from __future__ import annotations
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "governance" / "intents" / "inbox"
OUTBOX = ROOT / "governance" / "intents" / "outbox"
PROCESSED = ROOT / "governance" / "intents" / "processed"
LOG_DIR = ROOT / "logs" / "executor"
LOG_DIR.mkdir(parents=True, exist_ok=True)
EXEC_LOG = LOG_DIR / "exec_log.jsonl"
import sys
# Ensure repo root is on sys.path so imports like 'tools.governance_gate' work
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.governance_gate import validate_intent, load_json  # load_json helper used below
from tools.agent_api import read_processed_index, update_processed_index, atomic_write_json
from calyx.compute.compute_stewardship import attach_default_contract, should_execute, compute_signature, record_outcome, estimate_cost
import os

APPROVAL_POLICY = load_json(ROOT / "governance" / "approval_policy.json")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def safe_resolve_repo_path(path_str: str) -> Path:
    """Resolve path and ensure it is under repository root."""
    # Reject absolute paths immediately
    candidate = Path(path_str)
    if candidate.is_absolute():
        raise ValueError("path_outside_repo")
    # Compose and resolve
    p = (ROOT / path_str).resolve()
    try:
        root_res = ROOT.resolve()
        # Use commonpath check to ensure p is within root
        if str(p).startswith(str(root_res)):
            return p
    except Exception:
        pass

    def _trace_decision(reason: str, extra: dict | None = None):
        """Append a deterministic decision trace entry to logs/executor/decision_trace.jsonl"""
        try:
            TR = LOG_DIR / 'decision_trace.jsonl'
            entry = {
                'ts': _now_iso(),
                'intent_id': intent_id,
                'action': intent.get('intent'),
                'reason': reason,
                'claimed': claimed,
            }
            if extra:
                entry.update(extra)
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with TR.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
    raise ValueError("path_outside_repo")


def run_fs_read(intent: Dict[str, Any]) -> Dict[str, Any]:
    payload = intent.get("payload", {})
    raw_path = payload.get("path")
    if not raw_path:
        return {"outcome": "error", "errors": ["missing path"], "outputs_summary": None}
    try:
        p = safe_resolve_repo_path(raw_path)
    except Exception:
        return {"outcome": "error", "errors": ["path_outside_repo"], "outputs_summary": None}
    if not p.exists():
        return {"outcome": "error", "errors": ["file_not_found"], "outputs_summary": None}
    try:
        max_bytes = int(intent.get('payload', {}).get('max_bytes', 65536))
        raw = p.read_bytes()
        if len(raw) > max_bytes:
            text = raw[:max_bytes].decode('utf-8', errors='ignore')
            truncated = True
        else:
            text = raw.decode('utf-8', errors='ignore')
            truncated = False
        snippet = "\n".join(text.splitlines()[:50])
        return {"outcome": "success", "errors": [], "outputs_summary": {"lines": len(text.splitlines()), "snippet": snippet, "path": str(p.relative_to(ROOT)), "truncated": truncated}}
    except Exception as e:
        return {"outcome": "error", "errors": [str(e)], "outputs_summary": None}


def run_repo_grep(intent: Dict[str, Any]) -> Dict[str, Any]:
    # payload: { "pattern": "TODO", "file_ext": [".py", ".md"] }
    payload = intent.get("payload", {})
    pattern = payload.get("pattern")
    exts = payload.get("file_ext", [".py", ".md", ".txt", ".mdx"])
    if not pattern:
        return {"outcome": "error", "errors": ["missing pattern"], "outputs_summary": None}
    matches = []
    max_hits = int(payload.get('max_hits', 200))
    hits = 0
    for p in ROOT.rglob("*"):
        if hits >= max_hits:
            break
        if p.is_file() and any(p.name.endswith(ext) for ext in exts):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                if pattern in text:
                    # capture small preview
                    idx = text.find(pattern)
                    start = max(0, idx - 40)
                    preview = text[start:start+120].replace("\n", " ")
                    matches.append({"path": str(p.relative_to(ROOT)), "preview": preview})
                    hits += 1
            except Exception:
                continue
    return {"outcome": "success", "errors": [], "outputs_summary": {"matches": matches, "count": len(matches)}}


def run_fs_list(intent: Dict[str, Any]) -> Dict[str, Any]:
    payload = intent.get("payload", {})
    raw_path = payload.get("path", ".")
    max_items = int(payload.get("max_items", 200))
    try:
        p = safe_resolve_repo_path(raw_path)
    except Exception:
        return {"outcome": "error", "errors": ["path_outside_repo"], "outputs_summary": None}
    if not p.exists() or not p.is_dir():
        return {"outcome": "error", "errors": ["dir_not_found"], "outputs_summary": None}
    try:
        items = []
        for i, child in enumerate(sorted(p.iterdir()), start=1):
            if i > max_items:
                break
            items.append(child.name)
        return {"outcome": "success", "errors": [], "outputs_summary": {"items": items, "count": len(items), "path": str(p.relative_to(ROOT))}}
    except Exception as e:
        return {"outcome": "error", "errors": [str(e)], "outputs_summary": None}


def log_exec(record: Dict[str, Any]):
    try:
        with EXEC_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def process_intent_file(p: Path):
    # Read file atomically: assume only .json finalized files are in inbox
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception as e:
        # could not read; move to quarantine
        Q = ROOT / 'governance' / 'intents' / 'quarantine'
        Q.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(Q / p.name))
        # write outbox result indicating invalid_json
        OUTBOX.mkdir(parents=True, exist_ok=True)
        intent_id = p.stem
        result_path = OUTBOX / f"{intent_id}.result.json"
        result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "executed": False, "result": {"outcome": "validation_failed", "errors": ["invalid_json"], "outputs_summary": None}}
        try:
            result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        # log
        log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "outcome": "validation_failed", "errors": ["invalid_json"]})
        return
    try:
        intent = json.loads(raw)
    except Exception:
        # invalid JSON: quarantine and record
        Q = ROOT / 'governance' / 'intents' / 'quarantine'
        Q.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(Q / p.name))
        OUTBOX.mkdir(parents=True, exist_ok=True)
        intent_id = p.stem
        result_path = OUTBOX / f"{intent_id}.result.json"
        result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "executed": False, "result": {"outcome": "validation_failed", "errors": ["invalid_json"], "outputs_summary": None}}
        try:
            result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "outcome": "validation_failed", "errors": ["invalid_json"]})
        return

    gate_result = validate_intent(intent)
    intent_id = intent.get("intent_id") or (p.stem)

    # If this file has been claimed/moved into the processing directory by
    # run_once(), treat it as the canonical claimant and relax pre-checks that
    # would otherwise skip execution due to rapid reservation semantics.
    try:
        claimed = (p.parent.name == 'processing')
    except Exception:
        claimed = False

    def _debug_decision(reason: str):
        try:
            PI = LOG_DIR / 'processed_intents.json'
            pi = {}
            if PI.exists():
                try:
                    pi = json.loads(PI.read_text(encoding='utf-8'))
                except Exception:
                    pi = {}
            outb = OUTBOX / f"{intent_id}.result.json"
            out_exists = outb.exists()
            log_exec({
                'timestamp': _now_iso(),
                'intent_id': intent_id,
                'action': intent.get('intent'),
                'phase': 'decision',
                'reason': reason,
                'claimed': claimed,
                'processed_index': pi,
                'outbox_exists': out_exists
            })
        except Exception:
            pass

    # Note: dedup and reservation is handled by run_once() which groups and reserves
    # intent_ids. Avoid pre-emptive skipping here based solely on processed index to
    # prevent races between reservation and processing. We will still perform
    # lock and outbox checks below prior to execution.
    # Extra pre-execution guard: if processed index or lock indicates completion, skip
    try:
        LOCKS = LOG_DIR / 'locks'
        lock_file = LOCKS / f"{intent_id}.lock"
        PROCESSED_INDEX = LOG_DIR / 'processed_intents.json'
        if lock_file.exists():
            # A lock may have been created by run_once() as a reservation. Only
            # treat this as a duplicate skip if the processed index shows a
            # final state (not 'reserved' or 'processing'). Otherwise continue.
            try:
                if PROCESSED_INDEX.exists():
                    try:
                        idx = read_processed_index()
                    except Exception:
                        idx = {}
                    state = idx.get(intent_id)
                    if state and state not in ("reserved", "processing"):
                        OUTBOX.mkdir(parents=True, exist_ok=True)
                        rp = OUTBOX / f"{intent_id}.result.json"
                        payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
                        try:
                            atomic_write_json(rp, payload)
                        except Exception:
                            pass
                        log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "outcome": "skipped_duplicate_lock_precheck", "errors": []})
                        try:
                            PROCESSED.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(p), str(PROCESSED / p.name))
                        except Exception:
                            try: p.unlink()
                            except Exception: pass
                        return
                # otherwise assume reservation lock created by caller and proceed
            except Exception:
                pass
        if PROCESSED_INDEX.exists():
            try:
                idx = read_processed_index()
                if intent_id in idx and idx.get(intent_id) != 'reserved' and idx.get(intent_id) != 'processing':
                    OUTBOX.mkdir(parents=True, exist_ok=True)
                    rp = OUTBOX / f"{intent_id}.result.json"
                    payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
                    try:
                        _debug_decision('skipped_duplicate_lock_precheck')
                        _trace_decision('skipped_duplicate_lock_precheck')
                        atomic_write_json(rp, payload)
                    except Exception:
                        pass
                    log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "outcome": "skipped_duplicate_index_precheck", "errors": []})
                    try:
                        PROCESSED.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(p), str(PROCESSED / p.name))
                    except Exception:
                        try: p.unlink()
                        except Exception: pass
                    return
            except Exception:
                pass
    except Exception:
        pass
    # normalize action name for matching (canonical)
    action_raw = intent.get('intent')
    action_norm = (action_raw or '').strip()
    action_norm_l = action_norm.lower()

    # If an outbox result already exists and is final (not 'processing'), treat this as duplicate and skip executing
    try:
        OUTBOX.mkdir(parents=True, exist_ok=True)
        existing = OUTBOX / f"{intent_id}.result.json"
        if existing.exists() and not claimed:
            try:
                ex = json.loads(existing.read_text(encoding='utf-8'))
                outcome = ex.get('result', {}).get('outcome')
                if outcome and outcome != 'processing':
                    # If existing outbox is final, prefer it only if it's newer than
                    # the inbox file; otherwise allow reprocessing and overwrite.
                    try:
                        inbox_mtime = p.stat().st_mtime
                        outbox_mtime = existing.stat().st_mtime
                        if outbox_mtime >= inbox_mtime:
                            # write skipped_duplicate to ensure idempotent observable outcome
                            result_path = OUTBOX / f"{intent_id}.result.json"
                            result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
                            try:
                                _debug_decision('skipped_duplicate_existing_outbox')
                                _trace_decision('skipped_duplicate_existing_outbox')
                                atomic_write_json(result_path, result_payload)
                            except Exception:
                                pass
                            log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "outcome": "skipped_duplicate_existing_outbox", "errors": []})
                            PROCESSED.mkdir(parents=True, exist_ok=True)
                            try:
                                shutil.move(str(p), str(PROCESSED / p.name))
                            except Exception:
                                try: p.unlink()
                                except Exception: pass
                            return
                        # else: outbox is older than this inbox submission; continue and overwrite
                    except Exception:
                        # on any error comparing times, be conservative and do not skip
                        pass
            except Exception:
                pass
    except Exception:
        pass
    # Dedup reservation is handled by run_once() when claiming the file; do not
    # create or treat the presence of a locks/<intent_id>.lock here as a reason
    # to skip processing. This avoids false 'skipped_duplicate' outcomes when
    # run_once reserves intents prior to calling process_intent_file().

    # processing lock path to avoid races
    PROCESSING_LOCK = LOG_DIR / f'processing_{intent_id}.lock'
    try:
        if PROCESSING_LOCK.exists():
            # duplicate or already processing
            OUTBOX.mkdir(parents=True, exist_ok=True)
            result_path = OUTBOX / f"{intent_id}.result.json"
            result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
            try:
                _debug_decision('skipped_duplicate_processing_lock')
                _trace_decision('skipped_duplicate_processing_lock')
                result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
            log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "outcome": "skipped_duplicate", "errors": []})
            # move file to processed to avoid reprocessing
            PROCESSED.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(p), str(PROCESSED / p.name))
            except Exception:
                try: p.unlink()
                except Exception: pass
            return
        else:
            # create lock
            try:
                PROCESSING_LOCK.parent.mkdir(parents=True, exist_ok=True)
                PROCESSING_LOCK.write_text(_now_iso(), encoding='utf-8')
            except Exception:
                pass
            # create an outbox placeholder immediately to prevent rapid duplicates
            try:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                placeholder = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "processing", "errors": [], "outputs_summary": None}}
                (OUTBOX / f"{intent_id}.result.json").write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
            # create an outbox placeholder immediately to prevent rapid duplicates
            try:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                placeholder = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "processing", "errors": [], "outputs_summary": None}}
                (OUTBOX / f"{intent_id}.result.json").write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
    except Exception:
        # safeguard outer processing critical section
        pass
    result_record = {
        "timestamp": _now_iso(),
        "intent_id": intent_id,
        "action": intent.get("intent"),
        "validation_result": gate_result.get("validation_result"),
        "validation_failures": gate_result.get("failures", []),
        "auto_approved": gate_result.get("auto_approved", False)
    }

    # Idempotence: check processed intents store
    PROCESSED_INDEX = LOG_DIR / 'processed_intents.json'
    processed = {}
    try:
        if PROCESSED_INDEX.exists():
            processed = json.loads(PROCESSED_INDEX.read_text(encoding='utf-8'))
    except Exception:
        processed = {}
    if intent_id in processed and not claimed:
        # Only treat as duplicate if processed index indicates a final state.
        state = processed.get(intent_id)
        if state not in ("reserved", "processing"):
            # write outbox skipped_duplicate and log
            OUTBOX.mkdir(parents=True, exist_ok=True)
            result_path = OUTBOX / f"{intent_id}.result.json"
            result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
            try:
                _debug_decision('skipped_duplicate_processed_index')
                _trace_decision('skipped_duplicate_processed_index')
                atomic_write_json(result_path, result_payload)
            except Exception:
                pass
            log_exec({"timestamp": _now_iso(), "intent_id": intent_id, "action": intent.get('intent'), "outcome": "skipped_duplicate", "errors": []})
            # move file to processed to avoid reprocessing
            PROCESSED.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(p), str(PROCESSED / p.name))
            except Exception:
                try: p.unlink()
                except Exception: pass
            return

    # Reserve intent id as processing to avoid races: write processed index with 'processing'
    try:
        processed[intent_id] = 'processing'
        # atomic write
        tmp = PROCESSED_INDEX.with_suffix('.tmp')
        tmp.write_text(json.dumps(processed, indent=2), encoding='utf-8')
        tmp.replace(PROCESSED_INDEX)
    except Exception:
        pass

    # Default: requires approval if gate says so
    requires_approval_final = gate_result.get("requires_approval_final", True)
    auto_approved = gate_result.get("auto_approved", False)

    executed = False
    exec_out = {"outcome": "validation_failed", "errors": gate_result.get("failures", []), "outputs_summary": None}

    # Execute with robust exception handling and guaranteed result write
    if gate_result.get("validation_result") == "pass":
        # Attach/ensure compute contract and enforce stewardship before execution
        intent = attach_default_contract(intent)
        state_snapshot = {}
        allow, reason, next_eligible = should_execute(intent, state_snapshot)
        if not allow:
            exec_out = {"outcome": reason or "not_allowed", "errors": [], "outputs_summary": None}
            executed = False
            # write result and logs below in normal flow
        elif auto_approved or (not requires_approval_final and intent.get("requires_approval") == False):
            # Pre-execution re-check: avoid racing duplicates by re-checking processed index and outbox
            for _retry in range(5):
                try:
                    PROCESSED_INDEX = LOG_DIR / 'processed_intents.json'
                    if PROCESSED_INDEX.exists():
                        try:
                            proc_check = json.loads(PROCESSED_INDEX.read_text(encoding='utf-8'))
                        except Exception:
                            proc_check = {}
                        v = proc_check.get(intent_id)
                        if v and v not in ('reserved', 'processing'):
                            exec_out = {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}
                            executed = False
                            break
                    # check outbox final result
                    existing_out = OUTBOX / f"{intent_id}.result.json"
                    if existing_out.exists():
                        try:
                            ex = json.loads(existing_out.read_text(encoding='utf-8'))
                            outcome = ex.get('result', {}).get('outcome')
                            if outcome and outcome != 'processing':
                                exec_out = {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}
                                executed = False
                                break
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(0.05)

            try:
                if action_norm_l == "fs_read":
                    exec_out = run_fs_read(intent)
                    executed = True
                elif action_norm_l == "repo_grep":
                    exec_out = run_repo_grep(intent)
                    executed = True
                elif action_norm_l == "fs_list":
                    exec_out = run_fs_list(intent)
                    executed = True
                else:
                    exec_out = {"outcome": "error", "errors": [f"unsupported_action_for_daemon:{action_norm_l}"], "outputs_summary": None}
            except Exception as e:
                exec_out = {"outcome": "error", "errors": [str(e)], "outputs_summary": None}
            # record compute stewardship outcome
            try:
                sig = compute_signature(intent)
                usage = estimate_cost(intent)
                # simple state delta heuristic: exec_out.success == success -> state_changed True
                state_changed = (exec_out.get('outcome') == 'success')
                record_outcome(intent, sig, usage, exec_out.get('outcome'), state_changed, next_eligible)
            except Exception:
                pass
        else:
            exec_out = {"outcome": "pending_approval", "errors": [], "outputs_summary": None}

    # write result to outbox
    OUTBOX.mkdir(parents=True, exist_ok=True)
    result_path = OUTBOX / f"{intent_id}.result.json"
    try:
        result_payload = {
            "timestamp": _now_iso(),
            "intent_id": intent_id,
            "action": intent.get("intent"),
            "executed": executed,
            "result": exec_out
        }
        # atomic write: write to temp file then replace
        tmp = result_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # use os.replace to be atomic on Windows
        import os as _os
        _os.replace(str(tmp), str(result_path))
    except Exception:
        pass

    # append to executor log
    log_entry = {
        "timestamp": _now_iso(),
        "intent_id": intent_id,
        "action": intent.get("intent"),
        "outcome": exec_out.get("outcome"),
        "errors": exec_out.get("errors", []),
        "auto_approved": auto_approved
    }
    log_exec(log_entry)

    # record processed intent id for idempotence
    try:
        # mark as completed (atomic write)
        PROCESSED_INDEX = LOG_DIR / 'processed_intents.json'
        proc = {}
        if PROCESSED_INDEX.exists():
            try:
                proc = json.loads(PROCESSED_INDEX.read_text(encoding='utf-8'))
            except Exception:
                proc = {}
        proc[intent_id] = _now_iso()
        tmp = PROCESSED_INDEX.with_suffix('.tmp')
        tmp.write_text(json.dumps(proc, indent=2), encoding='utf-8')
        tmp.replace(PROCESSED_INDEX)
    except Exception:
        pass
    # remove processing lock
    try:
        if PROCESSING_LOCK.exists():
            PROCESSING_LOCK.unlink()
    except Exception:
        pass

    # move intent to processed
    PROCESSED.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(p), str(PROCESSED / p.name))
    except Exception:
        try:
            p.unlink()
        except Exception:
            pass


def run_once():
    INBOX.mkdir(parents=True, exist_ok=True)
    LOCKS = LOG_DIR / 'locks'
    LOCKS.mkdir(parents=True, exist_ok=True)

    # group inbox files by canonical intent_id (read JSON content when possible)
    groups = {}
    for p in sorted(INBOX.glob("*.json")):
        intent_id = p.stem
        try:
            raw = p.read_text(encoding='utf-8')
            data = json.loads(raw)
            intent_id = data.get('intent_id') or intent_id
        except Exception:
            # malformed: move to quarantine and write validation_failed outbox
            Q = ROOT / 'governance' / 'intents' / 'quarantine'
            Q.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(p), str(Q / p.name))
            except Exception:
                try: p.unlink()
                except Exception: pass
            OUTBOX.mkdir(parents=True, exist_ok=True)
            result_path = OUTBOX / f"{p.stem}.result.json"
            result_payload = {"timestamp": _now_iso(), "intent_id": f"file:{p.stem}", "action": None, "executed": False, "result": {"outcome": "validation_failed", "errors": ["invalid_json"], "source_file": p.name, "outputs_summary": None}}
            try:
                result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
            log_exec({"timestamp": _now_iso(), "intent_id": f"file:{p.stem}", "action": None, "outcome": "validation_failed", "errors": ["invalid_json"]})
            continue
        groups.setdefault(intent_id, []).append(p)

    # process one file per intent_id deterministically and mark duplicates
    for intent_id, plist in groups.items():
        # choose earliest-written file (by modification time) to deterministically select the first submission
        try:
            first = min(plist, key=lambda p: p.stat().st_mtime)
        except Exception:
            first = sorted(plist)[0]
        lock_path = LOCKS / f"{intent_id}.lock"
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, _now_iso().encode('utf-8'))
            finally:
                os.close(fd)

            # persist reservation
            try:
                PROCESSED_INDEX = LOG_DIR / 'processed_intents.json'
                proc = {}
                if PROCESSED_INDEX.exists():
                    try:
                        proc = json.loads(PROCESSED_INDEX.read_text(encoding='utf-8'))
                    except Exception:
                        proc = {}
                proc[intent_id] = 'reserved'
                tmp = PROCESSED_INDEX.with_suffix('.tmp')
                tmp.write_text(json.dumps(proc, indent=2), encoding='utf-8')
                tmp.replace(PROCESSED_INDEX)
            except Exception:
                pass

            # claim file by moving it to processing directory atomically
            PROC_DIR = ROOT / 'governance' / 'intents' / 'processing'
            PROC_DIR.mkdir(parents=True, exist_ok=True)
            dest = PROC_DIR / first.name
            try:
                os.replace(str(first), str(dest))
            except Exception:
                try:
                    shutil.move(str(first), str(dest))
                except Exception:
                    pass

            # write placeholder outbox
            try:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                result_path = OUTBOX / f"{intent_id}.result.json"
                placeholder = {"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "executed": False, "result": {"outcome": "processing", "errors": [], "outputs_summary": None}}
                tmp_r = result_path.with_suffix('.tmp')
                tmp_r.write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding='utf-8')
                os.replace(str(tmp_r), str(result_path))
            except Exception:
                pass

            # process the claimed file
            try:
                process_intent_file(dest)
            except Exception:
                try:
                    PROCESSED.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest), str(PROCESSED / dest.name))
                except Exception:
                    try: dest.unlink()
                    except Exception: pass
            else:
                # Ensure processed index records final timestamp for this intent_id
                try:
                    update_processed_index(intent_id, _now_iso())
                except Exception:
                    pass
            # mark any other inbox files with same intent_id as skipped duplicates
            for dup in plist:
                if dup == first:
                    continue
                try:
                    OUTBOX.mkdir(parents=True, exist_ok=True)
                    result_path = OUTBOX / f"{intent_id}.result.json"
                    result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
                    tmp = result_path.with_suffix('.tmp')
                    tmp.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
                    os.replace(str(tmp), str(result_path))
                except Exception:
                    pass
                try:
                    PROCESSED.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dup), str(PROCESSED / dup.name))
                except Exception:
                    try: dup.unlink()
                    except Exception: pass

        except Exception:
            # lock exists or creation failed; mark all files as skipped_duplicate
            for dup in plist:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                result_path = OUTBOX / f"{intent_id}.result.json"
                try:
                    result_payload = {"timestamp": _now_iso(), "intent_id": intent_id, "action": None, "executed": False, "result": {"outcome": "skipped_duplicate", "errors": [], "outputs_summary": None}}
                    tmp = result_path.with_suffix('.tmp')
                    tmp.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding='utf-8')
                    os.replace(str(tmp), str(result_path))
                except Exception:
                    pass
                try:
                    PROCESSED.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dup), str(PROCESSED / dup.name))
                except Exception:
                    try: dup.unlink()
                    except Exception: pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--poll", type=float, default=1.0, help="Poll interval in seconds (0.5-2.0 recommended)")
    args = parser.parse_args()

    if args.once:
        run_once()
        print("Daemon: ran one cycle")
        return

    print("Calyx Daemon: starting loop (CTRL-C to stop)")
    try:
        while True:
            run_once()
            time.sleep(max(0.5, min(2.0, float(args.poll))))
    except KeyboardInterrupt:
        print("Calyx Daemon: exiting")

if __name__ == "__main__":
    main()
