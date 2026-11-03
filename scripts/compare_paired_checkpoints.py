#!/usr/bin/env python3
"""Compare frozen paired field-form answers across actual model weights or one FCG leaf.

A new checkpoint is NOT an accuracy gain until paired scores share identical cases,
oracle, parser, form rendering, infer config, patient-disjoint provenance and
an independent untouched evaluation. This script performs the paired statistics,
not the claim promotion.
"""
import argparse, hashlib, json, math, random
from collections import defaultdict
from pathlib import Path

CANON=lambda x:json.dumps(x,sort_keys=True,separators=(",",":")).encode()
SHA=lambda b:hashlib.sha256(b).hexdigest()
def exact(b,c):
 n=b+c
 return min(1.0,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n) if n else 1.
def data(p,split):
 r=[json.loads(x) for x in Path(p).read_text().splitlines() if x]
 r=[x for x in r if x["split"]==split]
 d={x["case_digest_sha256"]:x for x in r}
 if not d or len(r)!=len(d):raise AssertionError("EMPTY_OR_DUPLICATE_CASES")
 return d
def compare(bpath,cpath,out,base_model_hash,child_model_hash,base_fcg,child_fcg,split,source_root):
 a=data(bpath,split);b=data(cpath,split)
 if a.keys()!=b.keys():raise AssertionError("CASE_SET_DIFFERS")
 if not source_root:raise AssertionError("MISSING_FROZEN_SOURCE_ROOT")
 for k in a:
  if a[k]["patient_id"]!=b[k]["patient_id"] or a[k]["template_key"]!=b[k]["template_key"]:
   raise AssertionError("PATIENT_OR_TEMPLATE_CHANGED")
 for value in (base_model_hash,child_model_hash):
  if value!="NOT_APPLICABLE" and (len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value)):
   raise AssertionError("INVALID_WEIGHT_SHA256")
 base=set(filter(None,base_fcg.split(",")));child=set(filter(None,child_fcg.split(",")))
 changed=sorted(base^child)
 weights=base_model_hash!=child_model_hash
 if weights and changed:classification="CONFOUNDED_MODEL_AND_FCG"
 elif weights:classification="WEIGHTS_ONLY_SUBJECT_TO_IDENTICAL_HARNESS"
 elif len(changed)==1:classification="SINGLE_FCG_LEAF"
 elif not changed:classification="NO_INTERVENTION"
 else:classification="MULTIPLE_FCG_LEAVES_CONFOUNDED"
 rows=[(a[k],b[k]) for k in sorted(a)]
 b_only=sum(bool(x["required_fields_correct"]) and not bool(y["required_fields_correct"]) for x,y in rows)
 c_only=sum(bool(y["required_fields_correct"]) and not bool(x["required_fields_correct"]) for x,y in rows)
 bypatient=defaultdict(list)
 for x,y in rows:
  bypatient[x["patient_id"]].append((int(bool(x["required_fields_correct"])),int(bool(y["required_fields_correct"]))))
 pids=sorted(bypatient)
 rand=random.Random(20261102)
 boots=[]
 for _ in range(10000):
  sample=[pids[rand.randrange(len(pids))] for _ in pids]
  vals=[(u,v) for pid in sample for u,v in bypatient[pid]]
  boots.append(sum(v-u for u,v in vals)/len(vals))
 boots.sort()
 ci=[boots[int(.025*len(boots))],boots[int(.975*len(boots))]]
 paired={"matched_cases":len(rows),"matched_patients":len(bypatient),
    "baseline_only":b_only,"challenger_only":c_only,
    "both_correct":sum(x["required_fields_correct"] and y["required_fields_correct"] for x,y in rows),
    "both_wrong":sum(not x["required_fields_correct"] and not y["required_fields_correct"] for x,y in rows)}
 assert sum(paired[k] for k in ("baseline_only","challenger_only","both_correct","both_wrong"))==len(rows)
 record={"schema":"frontier-forms.paired-checkpoint-gate.v1","baseline_prediction_file_sha256":SHA(Path(bpath).read_bytes()),
         "challenger_prediction_file_sha256":SHA(Path(cpath).read_bytes()),
         "frozen_cohort_root":source_root,"split":split,
         "base_model_weights_sha256":base_model_hash,"child_model_weights_sha256":child_model_hash,
         "base_fcg_leaves":sorted(base),"child_fcg_leaves":sorted(child),
         "changed_leaves":changed,"weight_change":weights,
         "weight_model_identity":"NOT_APPLICABLE: deterministic FCO arms" if not weights and base_model_hash=="NOT_APPLICABLE" else "CHECKPOINT_BYTES_IDENTIFIED_ONLY",
         "intervention":classification,
         "paired":paired,"delta":(c_only-b_only)/len(rows),
         "mcnemar_exact_two_sided":exact(b_only,c_only),"patient_cluster_bootstrap95":ci,
         "bootstrap_reps":10000,"seed":20261102,
         "matched_oracle_sha256":"NOT_COMPUTED: form case digests only; independent oracle digest to be provided",
         "identical_harness_proof":"NOT_TESTED: add pinned prompts/parser/inference/model settings",
         "independent_untouched_replication":"NOT_TESTED",
         "claim":"DISCOVERY_ONLY_NO_CAUSAL_PROMOTION"}
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise FileExistsError("APPEND_ONLY_OUTPUT_COLLISION "+str(out))
 out.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
 print(json.dumps({"intervention":classification,"delta":record["delta"],"mcnemar_p":record["mcnemar_exact_two_sided"],
                   "patient_ci":ci,"n":len(rows)}))
 return record
if __name__=="__main__":
 ap=argparse.ArgumentParser()
 for flag in ("baseline","challenger","out","baseline-model-hash","challenger-model-hash","baseline-fcg","challenger-fcg","source-root"):
  ap.add_argument("--"+flag,required=True)
 ap.add_argument("--split",default="test")
 a=ap.parse_args()
 compare(a.baseline,a.challenger,a.out,a.baseline_model_hash,a.challenger_model_hash,a.baseline_fcg,a.challenger_fcg,a.split,a.source_root)
