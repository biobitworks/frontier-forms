#!/usr/bin/env python3
"""Prebuilt synthetic intake form faults, 4-module factorial LOMO and source-backed receipts.

CONTROLLED FIXTURE: repairs read the permitted source snapshot; this is NOT AI training,
not an independent heldout result, and not a claim of clinical superiority.
"""
from __future__ import annotations
import argparse,hashlib,html,itertools,json,math,random,re
from collections import defaultdict
from pathlib import Path

MODULES=("name_suffix","ocr_confusable","postcode","patient_bind")
ATTACKS=("name_suffix","ocr_confusable","postcode","patient_bind","clean")
SAMPLES=(10,30,100)
SCHEMA="frontier_forms.synthetic_error_factorial.v1"

def canonical(o):
    return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def hashfile(p):return sha(Path(p).read_bytes())
def source_patient(bundle):
    return next(e["resource"] for e in bundle["entry"] if e["resource"].get("resourceType")=="Patient")
def fact(p,key):
    n=(p.get("name") or [{}])[0]
    if key=="given_name":return str((n.get("given") or [""])[0])
    if key=="family_name":return str(n.get("family") or "")
    if key=="postcode":return str((p.get("address") or [{}])[0].get("postalCode") or "")
    raise ValueError(key)
def source_rows(root):
    root=Path(root);m=json.loads((root/"MANIFEST.json").read_bytes())
    records=[]
    for member in m["members"]:
        f=root/member["subset_file"];raw=f.read_bytes()
        if sha(raw)!=member["subset_sha256"]:raise ValueError("source hash mismatch: "+str(f))
        b=json.loads(raw);p=source_patient(b)
        if p["id"]!=member["patient_id"]:raise ValueError("patient identity mismatch")
        records.append(dict(id=p["id"],name_given=fact(p,"given_name"),name_family=fact(p,"family_name"),
                            postcode=fact(p,"postcode"),source_sha256=sha(raw),split=member["split"]))
    if len(records)!=100 or len({p["id"] for p in records})!=100:raise ValueError("requires 100 unique synthetic patients")
    return records,hashfile(root/"MANIFEST.json")
def ocr_confuse(s):
    for i,ch in enumerate(s):
        if ch.lower()=="o":return s[:i]+"0"+s[i+1:]
        if ch=="l":return s[:i]+"1"+s[i+1:]
    return None
def make_cases(source):
    records,mhash=source_rows(source);cases=[]
    for i,p in enumerate(records):
        neighbor=records[(i+1)%len(records)]
        clean={"patient_id":p["id"],"source_sha256":p["source_sha256"]}
        # Gold is independent, source-bound; repairs may read source values as patient passport.
        cases.append(dict(clean,attack="name_suffix",field="given_name",
             observed=re.sub(r"\d+$","",p["name_given"]),observed_patient=p["id"]))
        value=ocr_confuse(p["name_family"])
        if value is not None:
            cases.append(dict(clean,attack="ocr_confusable",field="family_name",
                         observed=value,observed_patient=p["id"]))
        zip_ = p["postcode"]
        if zip_:
            corrupt=str(int(zip_)) if zip_.isdigit() and zip_.startswith("0") else zip_[:-1]
            if corrupt!=zip_:
                cases.append(dict(clean,attack="postcode",field="postcode",
                                  observed=corrupt,observed_patient=p["id"]))
        cases.append(dict(clean,attack="patient_bind",field="family_name",
             observed=neighbor["name_family"],observed_patient=neighbor["id"]))
        cases.append(dict(clean,attack="clean",field="family_name",
             observed=p["name_family"],observed_patient=p["id"]))
    return records,cases,mhash
def recover(row,source,enabled):
    """No attack label or gold passed; only observed entry, provenance, and source passport."""
    k=row["field"];value=row["observed"];target=source[row["patient_id"]]
    truth=target[{"given_name":"name_given","family_name":"name_family","postcode":"postcode"}[k]]
    if k=="given_name" and "name_suffix" in enabled and re.fullmatch(r"[A-Za-z]+",value or ""):
        if truth.startswith(value) and truth[len(value):].isdigit():value=truth
    if k=="family_name" and "ocr_confusable" in enabled and row["observed_patient"]==row["patient_id"]:
        suffix=re.search(r"(\d+)$",truth)
        if suffix and value.endswith(suffix.group(1)):
            stem=value[:-len(suffix.group(1))]
            folded=(stem.replace("0","o").replace("1","l")+suffix.group(1)).casefold()
        else:
            folded=value.replace("0","o").replace("1","l").casefold()
        if folded==truth.casefold():value=truth
    if k=="postcode" and "postcode" in enabled and value and truth.isdigit():
        if ((truth.startswith(value) or truth.endswith(value)) and len(truth)-len(value)<=2) or (len(truth)==5 and value==str(int(truth))):
            value=truth
    if k=="family_name" and "patient_bind" in enabled and row["observed_patient"]!=row["patient_id"]:
        value=truth
    return value
def score(rows,source,enabled):
    scored=[]
    for r in rows:
        pred=recover(r,source,enabled)
        truth=source[r["patient_id"]][{"given_name":"name_given","family_name":"name_family","postcode":"postcode"}[r["field"]]]
        scored.append(dict(case_id=sha(canonical({k:r[k] for k in ("patient_id","attack","field","observed","observed_patient")})),
                           patient_id=r["patient_id"],attack=r["attack"],correct=(pred==truth),
                           output_sha256=sha(canonical({"value":pred}))))
    return scored
def mcnemar(b,c):
    n=b+c
    return min(1.,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/(2**n)) if n else 1.
def paired(a,b,seed):
    assert len(a)==len(b)
    if [x["case_id"] for x in a]!=[x["case_id"] for x in b]:raise ValueError("unmatched pairing")
    lost=sum(x["correct"] and not y["correct"] for x,y in zip(a,b))
    gained=sum(not x["correct"] and y["correct"] for x,y in zip(a,b))
    if not a: return None
    patients=sorted({x["patient_id"] for x in a})
    idx=defaultdict(list)
    for i,x in enumerate(a):idx[x["patient_id"]].append(i)
    rng=random.Random(seed);boots=[]
    for _ in range(2000):
        sample=[j for _ in patients for j in idx[rng.choice(patients)]]
        boots.append(sum(int(b[j]["correct"])-int(a[j]["correct"]) for j in sample)/len(sample))
    boots.sort()
    return dict(n=len(a),patients=len(patients),delta=(gained-lost)/len(a),
       baseline_only=lost,challenger_only=gained,case_level_mcnemar_p=mcnemar(lost,gained),
       bootstrap_cluster_patient_ci95=[boots[49],boots[1949]],bootstrap_n=2000,seed=seed,
       warning="Pooled McNemar treats case rows as independent; clustered CI is primary. Per-attack McNemar uses <=1 case/patient.")
def merkle(leaves):
    nodes=[hashlib.sha256(b"FF_ERROR_LEAF_V1\x00"+canonical(x)).digest() for x in leaves]
    if not nodes:raise ValueError("empty merkle")
    hs=[x.hex() for x in nodes]
    while len(nodes)>1:
        nodes=[hashlib.sha256(b"FF_ERROR_NODE_V1\x00"+nodes[i]+nodes[i+1]).digest()
               if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
    return hs,nodes[0].hex()
def case_html(row):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Synthetic FHIR Form</title></head>"
            "<body><h1>Prebuilt synthetic intake form</h1><p>No PHI. Deliberate data-quality fault. No submission.</p>"
            "<form><label>"+html.escape(row["field"])+"<input name='"+html.escape(row["field"])+
            "' value='"+html.escape(row["observed"],quote=True)+"' readonly></label></form>"
            "<p>Patient identifier: "+html.escape(row["patient_id"])+"</p></body></html>")
def save_if_identical(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:raise ValueError("immutable output collision: "+str(path))
    else:
        path.write_bytes(data)
def run(source,out,size,seed=20261102):
    patients,allcases,mhash=make_cases(source)
    subset={r["id"]:r for r in patients[:size]}
    cases=[x for x in allcases if x["patient_id"] in subset]
    if not cases:raise ValueError("no cases")
    cohort=sorted(subset.values(),key=lambda x:x["id"])
    masks=[frozenset(x) for n in range(len(MODULES)+1) for x in itertools.combinations(MODULES,n)]
    full=frozenset(MODULES)
    results={";".join(x for x in MODULES if x in m) if m else "B0_injected":score(cases,subset,m) for m in masks}
    baseline=results["B0_injected"];fullrows=results[";".join(MODULES)]
    case_leaves=[{"index":i,"patient":r["patient_id"],"attack":r["attack"],"field":r["field"],
                  "observed_sha256":sha(r["observed"].encode()),"source_sha256":r["source_sha256"]}
                 for i,r in enumerate(cases)]
    leaves,root=merkle(case_leaves)
    rows=[];by_attack=defaultdict(list)
    for i,r in enumerate(cases):by_attack[r["attack"]].append(i)
    for mask in masks:
        name=";".join(x for x in MODULES if x in mask) if mask else "B0_injected"
        preds=results[name]
        checks={}
        for attack,indices in sorted(by_attack.items()):
            a=[baseline[i] for i in indices];b=[preds[i] for i in indices]
            checks[attack]={"accuracy":sum(int(y["correct"]) for y in b)/len(b),
                            "vs_B0":paired(a,b,seed),"n":len(indices)}
        rows.append({"arm":name,"modules":sorted(mask),"n_cases":len(preds),
           "accuracy":sum(int(x["correct"]) for x in preds)/len(preds),
           "vs_B0":paired(baseline,preds,seed),"vs_full":paired(fullrows,preds,seed),
           "attack_strata":checks,"prediction_sha256":sha(canonical(preds)),
           "result_merkle_root":merkle([{"index":i,"case_id":x["case_id"],"out":x["output_sha256"]} for i,x in enumerate(preds)])[1]})
    report={"schema":SCHEMA,"phase":"CONTROLLED_SYNTHETIC_FAULT_INJECTION_DISCOVERY",
        "source_type":"MITRE Synthea simulated FHIR (PR10 subset)",
        "warning":"Errors and corrections intentionally programmed. Any observed gains validate fixture rules, NOT learning or real-world model superiority.",
        "n_patient":len(subset),"n_fault_cases":len(cases),"source_manifest_sha256":mhash,
        "module_order":list(MODULES),"cohort_source_sha256":sha(canonical([{"id":p["id"],"source_sha256":p["source_sha256"]} for p in cohort])),
        "challenge_root":root,"leaf_recipe":"SHA256('FF_ERROR_LEAF_V1'+NUL+canonical JSON); SHA256('FF_ERROR_NODE_V1'+NUL+two raw digests); odd carried",
        "challenge_leaf_hashes":leaves,"AUROC":"NOT_COMPUTED: no independent continuous error-risk score; all metrics are deterministic fault repairs",
        "comparison":"same case IDs, masks, source bytes and deterministic correction policy for all 16 arms",
        "results":rows}
    p=Path(out);save_if_identical(p/"report.json",canonical(report))
    save_if_identical(p/"challenge_cases.json",canonical(cases))
    save_if_identical(p/"preview_name_suffix.html",case_html(next(x for x in cases if x["attack"]=="name_suffix")).encode())
    save_if_identical(p/"preview_patient_mismatch.html",case_html(next(x for x in cases if x["attack"]=="patient_bind")).encode())
    print(json.dumps({"size":size,"cases":len(cases),"arms":len(masks),
       "challenge_root":root,"report_sha256":hashfile(p/"report.json"),
       "b0_accuracy":rows[0]["accuracy"],"full_accuracy":rows[-1]["accuracy"]}))
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--cohort",required=True)
    p.add_argument("--out",required=True);p.add_argument("--size",type=int,choices=SAMPLES,default=10);args=p.parse_args()
    run(args.cohort,args.out,args.size)
if __name__=="__main__":main()
