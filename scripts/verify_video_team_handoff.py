#!/usr/bin/env python3
"""Verify actual exact bytes and declared root of the Frontier Forms video handoff.

Offline, read-only, no inference/training, no APIs, no patient-data export.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/"evidence/governance/VIDEO_TEAM_HANDOFF_RECEIPT_20261102.json"
def canonical(x:object)->bytes:
    return (json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()
def root_from(leaves:list[dict])->str:
    nodes=[hashlib.sha256(b"FF_VIDEO_HANDOFF_LEAF_V1\x00"+canonical(x)).digest() for x in leaves]
    if not nodes:raise ValueError("EMPTY_LEAF_SET")
    while len(nodes)>1:
        nodes=[hashlib.sha256(b"FF_VIDEO_HANDOFF_NODE_V1\x00"+nodes[i]+nodes[i+1]).digest()
            if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
    return nodes[0].hex()
def verify(root:Path=ROOT,receipt:Path=RECEIPT)->dict:
    d=json.loads(receipt.read_bytes())
    if d.get("program_id")!="frontier-forms":raise ValueError("WRONG_PROGRAM")
    if d.get("evidence_admission",{}).get("scientific_model_superiority")!="HOLD_NOT_PROMOTED":
        raise ValueError("UNSUPPORTED_SCIENTIFIC_PROMOTION")
    if d.get("competition_submission_verified") is not False:raise ValueError("FALSE_SUBMISSION_CLAIM")
    if d.get("no_new_training_or_inference") is not True:raise ValueError("UNSUPPORTED_EXECUTION_CLAIM")
    leaves=d["file_leaves"]
    if len(set(x["path"] for x in leaves))!=len(leaves):raise ValueError("DUPLICATE_FILE_LEAF")
    for x in leaves:
        p=root/x["path"]
        if not p.is_file():raise ValueError("MISSING_FILE:"+x["path"])
        blob=p.read_bytes()
        if sha(blob)!=x["sha256"] or len(blob)!=x["bytes"]:
            raise ValueError("FILE_BYTE_DRIFT:"+x["path"])
    actual=root_from(leaves)
    if actual!=d["file_root_sha256"]:raise ValueError("INVALID_ROOT")
    return {"state":"PASS_EXACT_BYTES","program_id":d["program_id"],
            "file_count":len(leaves),"root":actual,
            "receipt_sha256":sha(receipt.read_bytes()),
            "scientific_admission":d["evidence_admission"]["scientific_model_superiority"]}
if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
