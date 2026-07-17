"""
WO_DOC_HYGIENE_DEPRECATION_GATES_V1/V2 — Parse doc status, registry as canonical truth.
V2: Registry is authoritative; in-doc headers secondary; mismatch emits audit.doc.status.mismatch.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_REGISTRY_CACHE: dict | None = None


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter from markdown. Returns dict of key: value."""
    out: dict[str, str] = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return out
    for line in m.group(1).splitlines():
        line = line.strip()
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _load_registry(repo_root: Path) -> dict:
    """Load DOC_STATUS_REGISTRY.json. Returns {} if missing or invalid. Cached."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    p = repo_root / "docs" / "DOC_STATUS_REGISTRY.json"
    try:
        if p.exists() and p.is_file():
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            _REGISTRY_CACHE = data.get("docs", {})
        else:
            _REGISTRY_CACHE = {}
    except Exception:
        _REGISTRY_CACHE = {}
    return _REGISTRY_CACHE


def _path_to_registry_key(path: Path, repo_root: Path) -> str:
    """Convert path to registry key (forward slashes, relative to repo)."""
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _emit_doc_status_event(event: str, msg: str, data: dict) -> None:
    """Emit to event ledger. Never throws."""
    try:
        from calyx.kernel.event_ledger import emit as _le
        _le(level="WARN" if "mismatch" in event or "unknown" in event else "INFO", component="doc_status", event=event, msg=msg, data=data)
    except Exception:
        pass


def _find_repo_root(path: Path) -> Path:
    """Find repo root (directory containing docs/) by walking up from path."""
    p = path.resolve()
    for _ in range(10):
        if (p / "docs").exists():
            return p
        if p == p.parent:
            break
        p = p.parent
    return path.parent


def get_doc_status(path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """
    Read doc and return status metadata. WO_DOC_HYGIENE_V2: Registry is canonical.
    Returns: {status, owner, last_reviewed_utc, superseded_by, doctrine_scope, sha256, has_valid_header,
              from_registry, status_unknown, status_mismatch}
    """
    _root = repo_root if repo_root is not None else _find_repo_root(path)

    result: dict[str, Any] = {
        "status": None,
        "owner": None,
        "last_reviewed_utc": None,
        "superseded_by": None,
        "doctrine_scope": None,
        "sha256": "",
        "has_valid_header": False,
        "from_registry": False,
        "status_unknown": False,
        "status_mismatch": False,
        "header_status": None,
    }
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        result["sha256"] = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        fm = _parse_frontmatter(content)
        header_status = fm.get("status")
        result["owner"] = fm.get("owner")
        result["last_reviewed_utc"] = fm.get("last_reviewed_utc")
        result["superseded_by"] = fm.get("superseded_by")
        result["doctrine_scope"] = fm.get("doctrine_scope")
        result["has_valid_header"] = header_status in ("active", "deprecated", "archived")

        registry = _load_registry(_root)
        key = _path_to_registry_key(path, _root)
        reg_entry = registry.get(key)

        if reg_entry:
            result["from_registry"] = True
            result["status"] = reg_entry.get("status")
            if not result["owner"]:
                result["owner"] = reg_entry.get("owner")
            if not result["last_reviewed_utc"]:
                result["last_reviewed_utc"] = reg_entry.get("last_reviewed_utc")
            if not result["superseded_by"] and reg_entry.get("superseded_by"):
                result["superseded_by"] = reg_entry.get("superseded_by")
            if not result["doctrine_scope"] and reg_entry.get("doctrine_scope"):
                result["doctrine_scope"] = reg_entry.get("doctrine_scope")
            # Mismatch: header says X, registry says Y
            result["header_status"] = header_status
            if header_status and result["status"] and header_status != result["status"]:
                result["status_mismatch"] = True
                _emit_doc_status_event("audit.doc.status.mismatch", f"Header vs registry: {key}", {
                    "path": key,
                    "header_status": header_status,
                    "registry_status": result["status"],
                })
        else:
            # Not in registry: use header if valid, else unknown
            result["header_status"] = header_status
            result["status"] = header_status if result["has_valid_header"] else None
            if not result["status"]:
                result["status_unknown"] = True
                _emit_doc_status_event("audit.doc.status.unknown", f"Doc not in registry: {key}", {"path": key})
    except Exception:
        pass
    return result


def is_deprecated_or_archived(path: Path, repo_root: Path | None = None) -> bool:
    """
    True if doc has status deprecated or archived. WO_DOC_HYGIENE_V2: Registry canonical.
    If registry missing or doc not in registry → default exclude (treat as deprecated for safety).
    """
    st = get_doc_status(path, repo_root)
    status = st.get("status")
    if status in ("deprecated", "archived"):
        return True
    if st.get("status_unknown"):
        return True  # Defensive: unknown → exclude deprecated
    return False


def should_include_in_repo_search(path: Path, query_lower: str, override_requested: bool) -> tuple[bool, str]:
    """
    Whether to include this doc in repo_search results. WO_DOC_HYGIENE_V2: Override only via explicit token.
    Returns (include, reason). Override must be explicit INCLUDE_DEPRECATED_DOCS=TRUE, not heuristic.
    """
    st = get_doc_status(path)
    status = st.get("status")
    if status not in ("deprecated", "archived"):
        return True, ""
    if override_requested:
        return True, "deprecated"
    return False, "deprecated"


def validate_ops_docs(repo_root: Path) -> list[str]:
    """
    Validate all docs under docs/operations and docs/planning.
    WO_DOC_HYGIENE_V2: Registry canonical; mismatch fails preflight.
    Returns list of error messages. Empty = pass.
    """
    errors: list[str] = []
    registry = _load_registry(repo_root)
    if not registry:
        errors.append("docs/DOC_STATUS_REGISTRY.json missing or invalid; doc status unknown")
        return errors

    for sub in ("operations", "planning"):
        d = repo_root / "docs" / sub
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            rel = str(p.relative_to(repo_root)).replace("\\", "/")
            st = get_doc_status(p, repo_root)
            if st.get("status_mismatch"):
                errors.append(f"{rel}: status mismatch (header={st.get('header_status')} vs registry={st.get('status')})")
            if not st["has_valid_header"] and rel not in registry:
                errors.append(f"{rel}: missing or invalid status header (required: status: active|deprecated|archived)")
            elif st["status"] == "deprecated" and not st.get("superseded_by"):
                errors.append(f"{rel}: deprecated but missing superseded_by")
    return errors
