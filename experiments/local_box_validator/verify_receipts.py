#!/usr/bin/env python3
"""Independent stdlib readback of local vision experiment: no GPU/cloud needed."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
def canon(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def hfile(p):return sha(Path(p).read_bytes())
def merkle(leaves):
 nodes=[hashlib.sha256(b"FF_VISION_LEAF_V1\x00"+canon(x)).digest() for x in leaves]
 assert nodes
 while len(nodes)>1:
  nodes=[hashlib.sha256(b"FF_VISION_NODE_V1\x00"+nodes[i]+nodes[i+1]).digest()
         if i+1<len(nodes) else nodes[i] for i in range(0,len(nodes),2)]
 return nodes[0].hex()
def exact(b,c):
 n=b+c
 return 1. if n==0 else min(1.,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n)
def check(root,source,cohort,trainer):
 root=Path(root)
 full=json.loads((root/"run_report.json").read_bytes())
 pub=json.loads((root/"public_report.json").read_bytes())
 assert full["schema"]=="frontier_forms.local_vision_validator.v1"
 assert hfile(cohort)==full["source_manifest_sha256"]
 assert hfile(Path(source)/"GOLD_BOXES.json")==full["source_gold_boxes_sha256"]
 assert hfile(trainer)==full["trainer_code_sha256"]
 assert pub["fco_merkle_root"]==full["fco_merkle_root"]==merkle(full["fco_leaves"])
 assert pub["report_local_sha256"]==hfile(root/"run_report.json")
 expected={k:v for k,v in full.items() if k not in ("dataset_split_membership","results")}
 assert all(pub[k]==v for k,v in expected.items())
 split=full["dataset_split_membership"]
 train=set(split["train"]);val=set(split["validation"]);test=set(split["test"])
 assert not(train&val or train&test or val&test)
 assert len(test)==18 and len(val)==19
 gold=json.loads((Path(source)/"GOLD_BOXES.json").read_bytes())
 results={}
 for i,a in enumerate(full["results"]):
  b=pub["results"][i]
  assert b=={k:v for k,v in a.items() if k!="pages"},"PUBLIC_MISMATCH"
  assert len(a["pages"])==54
  name=a["arm"]
  if name=="CV_B0_contours":
   assert a["checkpoint_sha256"] is None
  else:
   weight=root/(name.replace("+","_")+".pkl")
   assert hfile(weight)==a["checkpoint_sha256"],"WEIGHTS_DRIFT:"+name
  assert full["fco_leaves"][i]["weight_sha256"]==a["checkpoint_sha256"]
  assert full["fco_leaves"][i]["result_sha256"]==sha(canon(a["pages"]))
  assert full["fco_leaves"][i]["n_images"]==54
  true_positive=false_positive=false_negative=0;success=[]
  used=set()
  for record in a["pages"]:
   key=(record["patient_id"],record["template"])
   assert key not in used
   used.add(key)
   assert record["patient_id"] in test
   img=next((x for x in gold.values() if x["image"]==record.get("image","") ),None)
   # Input image location is local-only; test screenshot SHA protects individual occurrence.
   assert record["tp"]>=0 and record["fn"]>=0 and record["fp"]>=0
   true_positive+=record["tp"];false_positive+=record["fp"];false_negative+=record["fn"]
   assert record["n_gold"]==record["tp"]+record["fn"]
   assert len(record["predicted"])==record["tp"]+record["fp"]
   for pred in record["predicted"]:
    x,y,x2,y2=pred["bbox"]
    assert 0<=x<x2<=900 and 0<=y<y2<=1200
    assert 0<=pred["score"]<=1
   assert record["full_page_success"]==(record["tp"]==record["n_gold"] and record["fp"]==0)
   success.append(bool(record["full_page_success"]))
  assert (true_positive,false_positive,false_negative)==(a["test_tp"],a["test_fp"],a["test_fn"])
  prec=true_positive/max(1,true_positive+false_positive)
  recall=true_positive/max(1,true_positive+false_negative)
  f1=2*true_positive/max(1,2*true_positive+false_positive+false_negative)
  assert math.isclose(a["precision"],prec,abs_tol=1e-10)
  assert math.isclose(a["recall"],recall,abs_tol=1e-10)
  assert math.isclose(a["f1"],f1,abs_tol=1e-10)
  assert sum(success)==a["full_page_successes"]
  p=a["paired_vs_cv_b0"];assert math.isclose(p["mcnemar_exact_descriptive"],exact(p["baseline_only"],p["challenger_only"]),abs_tol=1e-12)
  assert math.isclose(p["delta_full_page"],(p["challenger_only"]-p["baseline_only"])/54,abs_tol=1e-12)
  assert p["patient_cluster_bootstrap95"][0]<=p["patient_cluster_bootstrap95"][1]
  results[name]={"f1":round(f1,6),"n_page":54,"weight_sha256":a["checkpoint_sha256"],"full_page_pass":sum(success)}
 assert len(results)==8
 return {"state":"INDEPENDENT_READBACK_PASS","size":full["scale"],"n_train":full["n_train_patient"],"n_eval_patient":18,
    "source_manifest_sha256":full["source_manifest_sha256"],
    "fco_root":full["fco_merkle_root"],"public_sha256":hfile(root/"public_report.json"),"arms":results}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--source",required=True)
 p.add_argument("--cohort",required=True);p.add_argument("--trainer",required=True)
 a=p.parse_args();print(json.dumps(check(a.root,a.source,a.cohort,a.trainer),sort_keys=True))
if __name__=="__main__":main()
