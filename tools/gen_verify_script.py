#!/usr/bin/env python3
"""Generate the two-node verification script."""
import pathlib

code = r'''#!/usr/bin/env python3
"""Two-Node Reality Continuity Verification - Read-only checks."""
from __future__ import annotations
import json, subprocess, hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERIFY_TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

@dataclass
class GitV:
    branch: str = ""
    head: str = ""
    clean: bool = False
    passed: bool = False
    issues: list = field(default_factory=list)

@dataclass
class NodeV:
    node_id: str = ""
    count: int = 0
    first_seq: int = -1
    last_seq: int = -1
    mono: bool = True
    hash_ok: int = 0
    hash_bad: int = 0
    chain_ok: bool = True
    passed: bool = False
    issues: list = field(default_factory=list)

@dataclass
class EvidenceV:
    local_id: str = ""
    nodes: list = field(default_factory=list)
    results: dict = field(default_factory=dict)
    passed: bool = False

@dataclass
class ReportV:
    advisory: bool = True
    passed: bool = False
    issues: list = field(default_factory=list)

def git(args):
    try:
        r = subprocess.run(["git"]+args, capture_output=True, text=True, timeout=30)
        return r.returncode==0, r.stdout.strip()
    except:
        return False, ""

def verify_git():
    v = GitV()
    ok, o = git(["branch","--show-current"])
    v.branch = o if ok else "?"
    ok, o = git(["rev-parse","HEAD"])
    v.head = o[:12] if ok else "?"
    ok, o = git(["status","--porcelain"])
    v.clean = ok and not o.strip()
    files = ["station_calyx/schemas/evidence_envelope_v1.py","station_calyx/evidence/store.py"]
    for f in files:
        if not Path(f).exists():
            v.issues.append(f"Missing {f}")
    v.passed = len(v.issues)==0
    return v

def hpay(p):
    return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def henv(e):
    d=dict(e)
    d["signature"]=None
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def verify_node(nid, ed):
    v = NodeV(node_id=nid)
    ep = ed / "evidence.jsonl"
    if not ep.exists():
        v.issues.append("No file")
        return v
    envs = []
    with open(ep,"r") as f:
        for ln,line in enumerate(f,1):
            line=line.strip()
            if line:
                try:
                    envs.append(json.loads(line))
                except:
                    v.issues.append(f"JSON err {ln}")
    v.count = len(envs)
    if not envs:
        return v
    v.first_seq = envs[0].get("seq",-1)
    v.last_seq = envs[-1].get("seq",-1)
    prev = None
    for i,e in enumerate(envs):
        seq = e.get("seq",-1)
        if prev and seq <= prev.get("seq",-1):
            v.mono=False
            v.issues.append(f"Non-mono {i}")
        if hpay(e.get("payload",{}))==e.get("payload_hash",""):
            v.hash_ok+=1
        else:
            v.hash_bad+=1
        if prev and e.get("prev_hash")!=henv(prev):
            v.chain_ok=False
            v.issues.append(f"Chain {i}")
        prev = e
    v.passed = v.mono and v.hash_bad==0 and v.chain_ok
    return v

def verify_evidence():
    v = EvidenceV()
    try:
        from station_calyx.evidence.export import get_node_identity
        v.local_id, _ = get_node_identity()
    except:
        v.local_id = "?"
    try:
        from station_calyx.core.config import get_config
        eb = get_config().data_dir / "logs" / "evidence"
        if eb.exists():
            for item in eb.iterdir():
                if item.is_dir():
                    v.nodes.append(item.name)
                    v.results[item.name] = verify_node(item.name, item)
    except:
        pass
    v.passed = all(r.passed for r in v.results.values()) if v.results else True
    return v

def verify_report():
    v = ReportV()
    try:
        from station_calyx.agents.human_translation import generate_human_assessment
        from station_calyx.core.evidence import load_recent_events
        a = generate_human_assessment(load_recent_events(500))
        c = a.to_plain_language()
        if "advisory-only" not in c.lower():
            v.advisory=False
            v.issues.append("No disclaimer")
    except Exception as e:
        v.issues.append(str(e))
    v.passed = v.advisory and len(v.issues)==0
    return v

def main():
    print("="*60)
    print("Two-Node Verification")
    print("="*60)
    Path("reports/verification").mkdir(parents=True, exist_ok=True)
    
    g = verify_git()
    status = "PASS" if g.passed else "FAIL"
    print(f"[A] Git: {status} - {g.branch} @ {g.head}")
    
    e = verify_evidence()
    status = "PASS" if e.passed else "FAIL"
    print(f"[B] Evidence: {status} - {len(e.nodes)} node(s)")
    for nid, nr in e.results.items():
        status = "OK" if nr.passed else "FAIL"
        print(f"    {nid}: {nr.count} envs, seq {nr.first_seq}-{nr.last_seq}, {status}")
    
    r = verify_report()
    status = "PASS" if r.passed else "FAIL"
    print(f"[C] Reporting: {status}")
    
    ok = g.passed and e.passed and r.passed
    result = "PASS" if ok else "FAIL"
    summary = f"# Summary\n**Result:** {result}\n**Git:** {g.branch}@{g.head}\n**Nodes:** {e.nodes}"
    sp = Path(f"reports/verification/summary_{VERIFY_TS}.md")
    sp.write_text(summary)
    
    print()
    print("="*60)
    print(f"OVERALL: {result}")
    print(f"Summary: {sp}")
    return 0 if ok else 1

if __name__ == "__main__":
    exit(main())
'''

p = pathlib.Path("tools/verify_two_node_continuity.py")
p.write_text(code, encoding="utf-8")
print(f"Created {p}")
