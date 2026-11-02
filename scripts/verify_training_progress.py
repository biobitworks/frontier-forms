#!/usr/bin/env python3
"""Independent Python standard-library replay of frozen statistical snapshot."""
import hashlib,json,sys,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def hash_tree(events):
    lv=[hashlib.sha256(b"\x00"+CANON(e)).digest() for e in events]
    assert lv,"EMPTY_EVENTS"
    while len(lv)>1:
        out=[]
        for i in range(0,len(lv),2):
            r=lv[i+1] if i+1<len(lv) else lv[i]
            out.append(hashlib.sha256(b"\x01"+lv[i]+r).digest())
        lv=out
    return lv[0].hex()
def mcn(b,c):
    n=b+c
    return min(1.,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n) if n else 1.
def verify(path):
    directory=Path(path)
    mf=json.loads((directory/"manifest.json").read_text())
    raw=(directory/"events.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==mf["events_file_sha256"],"EVENTS_BYTES_CHANGED"
    events=[json.loads(x) for x in raw.splitlines()]
    assert len(events)==mf["event_count"],"EVENT_COUNT_CHANGED"
    assert hash_tree(events)==mf["root"],"MERKLE_ROOT_CHANGED"
    assert mf["signed"]=="NOT_SIGNED","UNEXPECTED_SIGNATURE_CLAIM"
    for family in ("fco_lomo","detector_lomo"):
        group=sorted([x for x in events if x["family"]==family],key=lambda x:x["mcnemar_p_two_sided"])
        if all("holm_adjusted_p" in x for x in group):
            prev=0.
            for i,x in enumerate(group):
                prev=max(prev,(len(group)-i)*x["mcnemar_p_two_sided"])
                assert abs(x["holm_adjusted_p"]-min(1.,prev))<1e-10,"HOLM_MISMATCH"
                assert x["promoted"] is False,"UNSUPPORTED_PROMOTION"
    for e in events:
        if e.get("paired_table"):
            t=e["paired_table"]
            assert t["n"]==t["baseline_only"]+t["both_correct"]+t["both_wrong"]+t["challenger_only"],"TABLE_N_MISMATCH"
            assert abs(mcn(t["baseline_only"],t["challenger_only"])-e["mcnemar_p_two_sided"])<1e-10,"P_MISMATCH"
            tol=0.00005 if e["family"]=="detector_lomo" and "source_rounded_delta" not in e else 1e-10
            assert abs((t["challenger_only"]-t["baseline_only"])/t["n"]-e["delta"])<tol,"DELTA_MISMATCH"
        if e["family"]=="actual_training_snapshot":
            vals=[x for x in e["points"] if "val_loss" in x]
            if len(vals)==1:
                assert e["delta_val_loss"] is None and e["heldout_accuracy"] is None,"INVENTED_GAIN"
                assert e["model_weights_sha256"] is None,"INVENTED_WEIGHT_SHA"
        if e["family"]=="methodology_only":
            assert e["delta"] is None and e["status"]=="NOT_COMPUTED","CROSS_PROGRAM_CONTAMINATION"
    return {"root":mf["root"],"event_count":len(events),"paired_tables_verified":sum(bool(e.get("paired_table")) for e in events)}
if __name__=="__main__":
    latest=json.loads((ROOT/"dashboard/training_progress_latest.json").read_text())
    path=ROOT/latest["source_snapshot"]
    result=verify(path)
    assert latest["root"]==result["root"],"DASHBOARD_ROOT_MISMATCH"
    assert latest["events"]==[json.loads(s) for s in (path/"events.jsonl").read_text().splitlines()],"DASHBOARD_EVENTS_MISMATCH"
    print(json.dumps(result,indent=2))
