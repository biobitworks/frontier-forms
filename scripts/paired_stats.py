#!/usr/bin/env python3
"""Paired statistical evaluation with explicit discovery/heldout claim ceiling.
No test is labeled PASS unless the selected partition and predeclared gates pass.
"""
import argparse, hashlib, json, math, random
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def read_records(path):
    records={}
    for line in Path(path).read_text().splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        key=r["row_key_sha256"]
        if key in records: raise ValueError(f"duplicate row key {key}")
        if r.get("status")!="EXECUTED" or not isinstance(r.get("correct"),bool):
            raise ValueError(f"missing or unscorable prediction for {key}")
        records[key]=r
    return records

def exact_mcnemar(b,c):
    """b = baseline-only correct; c = challenger-only correct."""
    n=b+c
    if not n:return 1.0
    k=min(b,c)
    # exact binomial two-sided p, stable for bounded sample sizes
    return min(1.,2.*sum(math.comb(n,i)*0.5**n for i in range(k+1)))

def pct(values,q):
    j=(len(values)-1)*q
    lo=int(j);hi=min(len(values)-1,lo+1)
    return values[lo]+(values[hi]-values[lo])*(j-lo)

def paired_bootstrap(rows,n_rep=10000,seed=20261102):
    """Stratified by task, paired case resampling, fixed deterministic RNG."""
    groups={}
    for r in rows: groups.setdefault(r["task"],[]).append(r)
    rand=random.Random(seed)
    diffs=[]
    for _ in range(n_rep):
        total=0
        for group in groups.values():
            for _ in group:
                v=group[rand.randrange(len(group))]
                total+=int(v["challenger_correct"])-int(v["baseline_correct"])
        diffs.append(total/len(rows))
    diffs.sort()
    return [pct(diffs,0.025),pct(diffs,0.975)]

def analyze(baseline,challenger, expected_keys=None, replicates=10000):
    a=read_records(baseline);c=read_records(challenger)
    if set(a)!=set(c): raise ValueError("paired IDs differ between models")
    if expected_keys is not None and set(a)!=set(expected_keys):
        raise ValueError("predictions do not match frozen partition keys")
    rows=[]
    for key in sorted(a):
        r=a[key];s=c[key]
        if r.get("task")!=s.get("task") or r.get("gold")!=s.get("gold"):
            raise ValueError(f"task/gold disagreement at {key}")
        rows.append(dict(key=key,task=r["task"],baseline_correct=r["correct"],challenger_correct=s["correct"]))
    if not rows: raise ValueError("empty paired sample")
    b=sum(r["baseline_correct"] and not r["challenger_correct"] for r in rows)
    c=sum(r["challenger_correct"] and not r["baseline_correct"] for r in rows)
    aok=sum(r["baseline_correct"] and r["challenger_correct"] for r in rows)
    fail=sum(not r["baseline_correct"] and not r["challenger_correct"] for r in rows)
    n=len(rows);delta=(c-b)/n
    ci=paired_bootstrap(rows,replicates)
    return {"n":n,"baseline_correct":aok+b,"challenger_correct":aok+c,
            "both_correct":aok,"both_wrong":fail,
            "baseline_only_correct":b,"challenger_only_correct":c,
            "delta_accuracy":delta,
            "mcnemar_exact_two_sided_p":exact_mcnemar(b,c),
            "paired_stratified_bootstrap_95pct_ci":ci,
            "bootstrap_replicates":replicates,
            "bootstrap_seed":20261102,
            "statistical_improvement":c>b and exact_mcnemar(b,c)<0.05 and ci[0]>0.0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True)
    p.add_argument("--challenger",required=True)
    p.add_argument("--split-manifest",required=True)
    p.add_argument("--partition",choices=["discovery","heldout","reserve"],default="discovery")
    p.add_argument("--out",required=True)
    p.add_argument("--replicates",type=int,default=10000)
    a=p.parse_args()
    split=json.loads(Path(a.split_manifest).read_text())
    ids=set()
    for task,buckets in split["task_partitions"].items():
        ids.update(buckets.get(a.partition,[]))
    result=analyze(a.baseline,a.challenger,ids,a.replicates)
    result.update({"partition":a.partition,"source_status":"PAIRWISE_MODEL_EVALUATION",
                   "baseline_result_sha256":sha(a.baseline),
                   "challenger_result_sha256":sha(a.challenger),
                   "split_manifest_sha256":sha(a.split_manifest),
                   "mcnemar_gate": "PASS" if result["mcnemar_exact_two_sided_p"]<0.05 and result["delta_accuracy"]>0 else "FAIL",
                   "bootstrap_gate": "PASS" if result["paired_stratified_bootstrap_95pct_ci"][0]>0 else "FAIL",
                   "independent_dataset_gate":"NOT_TESTED",
                   "claim_gate":"DISCOVERY_ONLY" if a.partition=="discovery" else "HOLD_PENDING_EXTERNAL_VALIDATION"})
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
