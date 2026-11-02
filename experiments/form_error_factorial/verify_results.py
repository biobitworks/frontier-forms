#!/usr/bin/env python3
"""Independent readback of FCG synthetic challenge leaves, roots and statistical receipts."""
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
def raw(o):return (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
def h(b):return hashlib.sha256(b).digest()
def root_and_leaf_hashes(leaves):
 nodes=[h(b"FF_ERROR_LEAF_V1\x00"+raw(x)) for x in leaves]
 if not nodes:raise ValueError("NO_LEAVES")
 leaf=[x.hex() for x in nodes]
 while len(nodes)>1:
  next=[]
  for i in range(0,len(nodes),2):
   if i+1==len(nodes):next.append(nodes[i])
   else:next.append(h(b"FF_ERROR_NODE_V1\x00"+nodes[i]+nodes[i+1]))
  nodes=next
 return leaf,nodes[0].hex()
def exact_p(b,c):
 n=b+c
 return 1. if n==0 else min(1.,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n)
def verify(folder,source):
 folder=Path(folder)
 cases=json.loads((folder/"challenge_cases.json").read_bytes())
 report=json.loads((folder/"report.json").read_bytes())
 assert report["schema"]=="frontier_forms.synthetic_error_factorial.v1"
 assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==report["source_manifest_sha256"]
 leaves=[{"index":i,"patient":r["patient_id"],"attack":r["attack"],"field":r["field"],
           "observed_sha256":hashlib.sha256(r["observed"].encode()).hexdigest(),"source_sha256":r["source_sha256"]}
          for i,r in enumerate(cases)]
 hashes,root=root_and_leaf_hashes(leaves)
 assert hashes==report["challenge_leaf_hashes"],"LEAF_MISMATCH"
 assert root==report["challenge_root"],"ROOT_MISMATCH"
 assert len(leaves)==report["n_fault_cases"],"CASE_COUNT"
 counts=Counter(x["attack"] for x in cases)
 assert len(report["results"])==16 and len({x["arm"] for x in report["results"]})==16
 for arm in report["results"]:
  assert arm["n_cases"]==len(cases)
  assert 0<=arm["accuracy"]<=1
  for attack,m in arm["attack_strata"].items():
   assert m["n"]==counts[attack]
   delta=m["vs_B0"]
   assert math.isclose(delta["case_level_mcnemar_p"],exact_p(delta["baseline_only"],delta["challenger_only"]),abs_tol=1e-10)
   assert math.isclose(delta["delta"],(delta["challenger_only"]-delta["baseline_only"])/m["n"],abs_tol=1e-10)
  for key in ("vs_B0","vs_full"):
   m=arm[key]
   assert math.isclose(m["delta"],(m["challenger_only"]-m["baseline_only"])/len(cases),abs_tol=1e-10)
   assert math.isclose(m["case_level_mcnemar_p"],exact_p(m["baseline_only"],m["challenger_only"]),abs_tol=1e-10)
   assert m["bootstrap_cluster_patient_ci95"][0]<=m["bootstrap_cluster_patient_ci95"][1]
 assert report["AUROC"].startswith("NOT_COMPUTED")
 return {"state":"INDEPENDENT_READBACK_PASS","n_patients":report["n_patient"],
  "n_cases":len(cases),"n_arms":len(report["results"]),"challenge_root":root,
  "report_sha256":hashlib.sha256((folder/"report.json").read_bytes()).hexdigest()}
def main():
 p=argparse.ArgumentParser();p.add_argument("folder");p.add_argument("source_manifest")
 args=p.parse_args();print(json.dumps(verify(args.folder,args.source_manifest),sort_keys=True))
if __name__=="__main__":main()
