from __future__ import annotations

import json
import time
import subprocess
import pathlib
import hashlib
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


REPO_ROOT = pathlib.Path(r"C:\Calyx_Terminal").resolve()
RECEIPTS = REPO_ROOT / "cbo_hub" / "receipts" / "dev_harness.jsonl"

SANDBOX_IMAGE = "calyx-sandbox:dev"


app = FastAPI(title="Calyx Dev Harness", version="0.1")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write_receipt(obj: dict) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _jail_path(rel_path: str) -> pathlib.Path:
    p = (REPO_ROOT / rel_path).resolve()
    if not str(p).startswith(str(REPO_ROOT)):
        raise HTTPException(400, "Path escapes repo root.")
    return p

class RepoListReq(BaseModel):
    path: str = ""
    max_entries: int = 200

class RepoListResp(BaseModel):
    path: str
    entries: List[str]
    sha256: str

@app.post("/repo/list", response_model=RepoListResp)
def repo_list(req: RepoListReq):
    p = _jail_path(req.path or ".")
    if not p.exists() or not p.is_dir():
        raise HTTPException(404, "Directory not found.")
    entries = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        rel = str(child.relative_to(REPO_ROOT)).replace("\\", "/")
        entries.append(rel + ("/" if child.is_dir() else ""))
        if len(entries) >= req.max_entries:
            break
    out_sha = _sha256_bytes(("\n".join(entries)).encode("utf-8", errors="ignore"))
    _write_receipt({
        "ts_utc": _now_iso(),
        "tool": "repo_list",
        "path": req.path,
        "max_entries": req.max_entries,
        "out_sha256": out_sha,
    })
    return RepoListResp(path=req.path, entries=entries, sha256=out_sha)

# -------- Repo tools --------

class RepoReadReq(BaseModel):
    path: str
    start_line: int = 1
    end_line: int = 200


class RepoReadResp(BaseModel):
    path: str
    start_line: int
    end_line: int
    text: str
    sha256: str


@app.post("/repo/read", response_model=RepoReadResp)
def repo_read(req: RepoReadReq):
    p = _jail_path(req.path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found.")

    lines = p.read_text(encoding="utf-8", errors="replace").splitlines(True)
    s = max(req.start_line, 1) - 1
    e = min(req.end_line, len(lines))
    chunk = "".join(lines[s:e])

    out_sha = _sha256_bytes(chunk.encode("utf-8", errors="ignore"))
    _write_receipt({
        "ts_utc": _now_iso(),
        "tool": "repo_read",
        "path": req.path,
        "start_line": req.start_line,
        "end_line": req.end_line,
        "out_sha256": out_sha,
    })

    return RepoReadResp(
        path=req.path,
        start_line=req.start_line,
        end_line=req.end_line,
        text=chunk,
        sha256=out_sha
    )


class RepoSearchReq(BaseModel):
    query: str = Field(..., min_length=1)
    glob: Optional[str] = None
    max_hits: int = 200


class RepoSearchResp(BaseModel):
    query: str
    hits: List[str]
    sha256: str


@app.post("/repo/search", response_model=RepoSearchResp)
def repo_search(req: RepoSearchReq):
    cmd = ["rg", "--line-number", "--no-heading", req.query, str(REPO_ROOT)]
    if req.glob:
        cmd.extend(["--glob", req.glob])

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=25)
        text = out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        # rg returns exit code 1 when no matches; treat that as non-fatal
        text = e.output.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Search timed out.")

    hits = text.splitlines()[: req.max_hits]
    out_sha = _sha256_bytes(("\n".join(hits)).encode("utf-8", errors="ignore"))

    _write_receipt({
        "ts_utc": _now_iso(),
        "tool": "repo_search",
        "query": req.query,
        "glob": req.glob,
        "max_hits": req.max_hits,
        "out_sha256": out_sha,
    })

    return RepoSearchResp(query=req.query, hits=hits, sha256=out_sha)


class ApplyPatchReq(BaseModel):
    patch_unified_diff: str = Field(..., min_length=5)


class ApplyPatchResp(BaseModel):
    applied: bool
    patch_sha256: str
    message: str


@app.post("/repo/apply_patch", response_model=ApplyPatchResp)
def repo_apply_patch(req: ApplyPatchReq):
    patch_bytes = req.patch_unified_diff.encode("utf-8")
    patch_sha = _sha256_bytes(patch_bytes)

    try:
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "--"],
            cwd=str(REPO_ROOT),
            input=patch_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=25
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Patch apply timed out.")

    ok = (proc.returncode == 0)
    msg = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()

    _write_receipt({
        "ts_utc": _now_iso(),
        "tool": "repo_apply_patch",
        "patch_sha256": patch_sha,
        "applied": ok,
        "message": msg[:2000],
    })

    return ApplyPatchResp(applied=ok, patch_sha256=patch_sha, message=msg)


# -------- Docker exec tool --------

class ExecDockerReq(BaseModel):
    cmd: List[str] = Field(..., min_items=1)
    timeout_sec: int = 180
    network: bool = False  # default OFF


class ExecDockerResp(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    receipt_sha256: str


@app.post("/exec/docker", response_model=ExecDockerResp)
def exec_docker(req: ExecDockerReq):
    base = [
        "docker", "run", "--rm",
        "-v", f"{REPO_ROOT}:/workspace",
        "-w", "/workspace",
    ]

    if not req.network:
        base += ["--network", "none"]

    base += [SANDBOX_IMAGE] + req.cmd

    try:
        proc = subprocess.run(
            base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=req.timeout_sec
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Docker exec timed out.")

    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")

    receipt = {
        "ts_utc": _now_iso(),
        "tool": "exec_docker",
        "cmd": req.cmd,
        "timeout_sec": req.timeout_sec,
        "network": req.network,
        "exit_code": proc.returncode,
        "stdout_sha256": _sha256_bytes(stdout.encode("utf-8", errors="ignore")),
        "stderr_sha256": _sha256_bytes(stderr.encode("utf-8", errors="ignore")),
    }
    receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
    receipt["receipt_sha256"] = receipt_sha
    _write_receipt(receipt)

    # Keep outputs bounded
    return ExecDockerResp(
        exit_code=proc.returncode,
        stdout=stdout[-12000:],
        stderr=stderr[-12000:],
        receipt_sha256=receipt_sha
    )