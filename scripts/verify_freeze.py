#!/usr/bin/env python3
"""Independently verify a locally authorized original project freeze.
No raw leaves or private source files are exported or logged.
"""
import argparse, hashlib, json
from pathlib import Path

EXPECTED="9e4d4df8aa7a887ecc8b792a1d099832b584c16f81ea821897fcd437f6fd3a9a"
FOLDER="ASI-FRONTIER-9e4d4df8aa7a887e"

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def sha(b):
    return hashlib.sha256(b).hexdigest()

def file_sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1048576),b""):
            h.update(c)
    return h.hexdigest()

def root(leaves):
    if not leaves: raise ValueError("EMPTY_LEAF_SET")
    level=[bytes.fromhex(sha(b"\x00"+canonical(x))) for x in leaves]
    while len(level)>1:
        if len(level)%2: level.append(level[-1])
        level=[hashlib.sha256(b"\x01"+level[i]+level[i+1]).digest()
               for i in range(0,len(level),2)]
    return level[0].hex()

def verify(source_root, strict=True):
    source_root=Path(source_root)
    folder=source_root/"custody"/"project_freezes"/FOLDER
    manifest=json.loads((folder/"manifest.json").read_text())
    leaves=[json.loads(x) for x in (folder/"leaves.jsonl").read_text().splitlines() if x.strip()]
    assert manifest["schema"]=="asi.project.freeze.v1"
    assert len(leaves)==manifest["leaf_count"]==15,"LEAF_COUNT"
    assert [x["path"] for x in leaves]==manifest["leaf_order"],"LEAF_ORDER"
    computed=root(leaves)
    assert computed==manifest["root"]==EXPECTED,"ROOT_MISMATCH"
    verified_files=0
    for item in leaves:
        p=item["path"]
        if p=="PROJECT_CONTEXT":
            assert sha(canonical(item["context"]))==item["sha256"],"CONTEXT_INTEGRITY"
            assert item["context"]["parent"]["root"]==manifest["parent"]["root"]
        elif p=="FCG_EDGES":
            assert sha(canonical(item["edges"]))==item["sha256"],"GRAPH_INTEGRITY"
        else:
            path=source_root/p
            if not path.is_file():
                if strict: raise FileNotFoundError(path)
                continue
            assert path.stat().st_size==item["size_bytes"],"FILE_SIZE:"+p
            assert file_sha(path)==item["sha256"],"FILE_DIGEST:"+p
            verified_files+=1
    return dict(status="PASS" if verified_files==13 else "PARTIAL",
        computed_root=computed,original_leaf_count=len(leaves),
        independently_verified_files=verified_files,
        signature="NOT_SIGNED",mmr="NOT_COMPUTED",
        custody_only=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",required=True)
    p.add_argument("--strict",action="store_true")
    p.add_argument("--receipt")
    a=p.parse_args()
    out=verify(a.source_root,a.strict)
    if a.receipt:
        dest=Path(a.receipt)
        if dest.exists():raise SystemExit("REFUSE_OVERWRITE_RECEIPT")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
