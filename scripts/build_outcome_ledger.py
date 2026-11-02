#!/usr/bin/env python3
"""Build exact-byte index of existing Frontier Forms evidence; no data/model transfer."""
import hashlib,json,subprocess
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parents[1]
OUT=R/"evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json"
PREDECESSOR=R/"evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102.json"
BENCH="bench/charts/live_metrics.json"
POINTER="dashboard/training_progress_latest.json"
FIGURE="docs/figures/accomplishment_heatmap.json"
GATE="evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json"
FREEZE="evidence/forms_b0/B0_FREEZE_V1.json"
def raw(o):return (json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def source(p):return (R/p).read_bytes()
def data(p):return json.loads(source(p))
def cmd(*args):return subprocess.check_output(["git",*args],cwd=R)
def merkle(v):
 a=[hashlib.sha256(b"FF_GOV_LEAF_V1\x00"+raw(x)).digest() for x in v]
 if not a:raise ValueError("EMPTY_INDEX")
 while len(a)>1:
  a=[hashlib.sha256(b"FF_GOV_NODE_V1\x00"+a[i]+a[i+1]).digest() if i+1<len(a) else a[i] for i in range(0,len(a),2)]
 return a[0].hex()
def build():
 commit=cmd("rev-parse","HEAD").decode().strip()
 point,fig,gate,freeze=map(data,[POINTER,FIGURE,GATE,FREEZE])
 bench=data(BENCH)
 if bench.get("classification")!="SYNTHETIC_AGGREGATE_METRICS_ONLY":raise ValueError("UNCLASSIFIED_BENCH_DATA")
 if not PREDECESSOR.is_file():raise ValueError("MISSING_PREDECESSOR_LEDGER")
 predecessor=json.loads(PREDECESSOR.read_bytes())
 if predecessor.get("parent_main_commit")==commit:raise ValueError("SUCCESSOR_PARENT_MUST_CHANGE")
 snap=point["source_snapshot"]
 manifest=data(snap+"/manifest.json")
 if (gate["admit"]["state"]!="HOLD_NO_INDEPENDENT_PI_ADMISSION" or
  gate["admit"]["clinical_or_model_superiority_supported"] is not False):
  raise ValueError("SCIENTIFIC_ADMISSION_NOT_HOLD")
 if not (manifest["root"]==point["root"]==gate["source_snapshot_root"]):
  raise ValueError("SOURCE_ROOT_MISMATCH")
 if not (freeze["lane"]=="frontier-forms" and gate["program_id"]=="frontier-forms" and
  freeze["dataset"]["subset_cohort_root"]==manifest["source_cohort_root"]):
  raise ValueError("CROSS_PROGRAM_OR_DATASET_MISMATCH")
 events=point["events"]
 if len(events)!=manifest["event_count"] or len(set(x["id"] for x in events))!=len(events):raise ValueError("EVENT_COUNT_OR_DUPLICATE")
 methods=[x for x in events if x["family"]=="methodology_only"]
 if len(methods)!=1 or methods[0]["id"]!="FF-VITA-DAISY-ABSTRACT-ONLY":raise ValueError("DAISY_METHOD_NOT_PRESENT")
 m=methods[0]
 if m["status"]!="NOT_COMPUTED" or any(m.get(k) is not None for k in ("delta","model_weights_sha256","source_root","mcnemar_p_two_sided","ci95_patient_cluster")):
  raise ValueError("DAISY_MEASUREMENT_CONTAMINATION")
 if any(x.get("promoted") is True or x["status"] in ("ADMITTED","SUPPORTED","PROMOTED","SUPPORTED_GAIN") for x in events):
  raise ValueError("UNSUPPORTED_PROMOTION")
 rows=[]
 allowed=("id","family","status","parent","child","leaf","metric","value","control_value","delta","delta_val_loss","n","train_patients","eval_patients","model","model_weights_changed","model_weights_sha256","mcnemar_p_two_sided","holm_adjusted_p","ci95_patient_cluster","ci95_error_type_stratified","paired_table","replication","claim_ceiling","source_root","source_graph_root","false_positive_cost")
 for i,event in enumerate(events):
  row={k:event.get(k) for k in allowed}
  row.update(event_index=i,source_event_sha256=sha(raw(event)),scientific_promotion="NOT_ADMITTED",
             source_pointer=POINTER,source_event_path=snap+"/events.jsonl")
  rows.append(row)
 refs=[s.decode() for s in cmd("ls-files","-z").split(b"\x00") if s]
 roots=("data/","evidence/","dashboard/","docs/figures/","bench/")
 inventory=[]
 for name in sorted(refs):
  if name.startswith(roots) and Path(name).suffix.lower() in (".json",".jsonl") and R.joinpath(name).is_file() and R.joinpath(name)!=OUT:
   b=source(name)
   inventory.append({"path":name,"sha256":sha(b),"size_bytes":len(b)})
 source_paths=[POINTER,FIGURE,GATE,FREEZE,BENCH,snap+"/events.jsonl",snap+"/manifest.json","docs/architecture/DAISY_METHOD_TRANSFER_BOUNDARY_20261102.md"]
 runs=bench["runs"]
 if len(runs)!=48:raise ValueError("INCOMPLETE_HOSTED_BENCH_SNAPSHOT")
 pairs={}
 for x in runs:
  k=(x["model"],x["case"],x["form"],x["repeat"])
  by=pairs.setdefault(k,{})
  if x["arm"] in by:raise ValueError("DUPLICATE_HOSTED_ARM")
  by[x["arm"]]=x
 if len(pairs)!=24 or any(set(x)!={"pi+browser-tools","frontier-tools"} for x in pairs.values()):
  raise ValueError("UNPAIRED_HOSTED_BENCHMARK")
 paired=[]
 for k,v in sorted(pairs.items()):
  a,b=v["pi+browser-tools"],v["frontier-tools"]
  paired.append({"model":k[0],"case":k[1],"form":k[2],"repeat":k[3],
   "field_accuracy_delta":b["correct"]/b["fields"]-a["correct"]/a["fields"],
   "fields_correct_delta":b["correct"]-a["correct"],
   "elapsed_seconds_delta":b["seconds"]-a["seconds"],
   "full_form_delta":int(bool(b["full_form"]))-int(bool(a["full_form"])),
   "quality_regressed":b["correct"]<a["correct"],
   "tool_is_faster":b["seconds"]<a["seconds"],
   "claim_ceiling":"teammate hosted synthetic pilot, not local training or heldout admission"})
 runfields=("model","arm","case","form","repeat","correct","fields","wrong","missed",
            "failed","timed_out","full_form","seconds","cost_usd","cached",
            "fabricated","unsafe","unknown","unknown_flagged","unknown_held",
            "local_receipt_sha256","submitted")
 synthetic_runs=[{k:x.get(k) for k in runfields} for x in runs]
 summary=Counter(x["status"] for x in events)
 group=Counter(x["family"] for x in events)
 return {
  "schema":"frontier_forms.outcome_promotion_inventory.v2","program_id":"frontier-forms",
  "parent_main_commit":commit,"source_snapshot_root":point["root"],
  "predecessor":{"path":str(PREDECESSOR.relative_to(R)),"file_sha256":sha(PREDECESSOR.read_bytes()),"main_commit":predecessor["parent_main_commit"],"inventory_root":predecessor["inventory_sha256_merkle_root"]},
  "claim_ceiling":"SYNTHETIC_DISCOVERY; positive != scientific admitted",
  "source_sha256":{p:sha(source(p)) for p in source_paths},
  "freeze":{"id":freeze["freeze_id"],"state":freeze["state"],"n_patients":freeze["dataset"]["n_patients"],"cohort":freeze["dataset"]["id"],"cohort_root":freeze["dataset"]["subset_cohort_root"]},
  "admission":{"status":gate["admit"]["state"],"scientifically_supported_promotions":0,
    "prospective_replication":gate["replicate"]["independent_prospective_replication"],
    "daisy_methodology_only":True,"daisy_weights_imported":False,"daisy_performance_imported":False},
  "evidence_counts":{"total":len(events),"by_status":dict(sorted(summary.items())),"by_family":dict(sorted(group.items()))},
  "scientific_events":rows,
  "teammate_hosted_benchmark":{"source":BENCH,"source_sha256":sha(source(BENCH)),
    "identity":"TEAMMATE_HOSTED_PILOT_SEPARATE_FROM_LOCAL_FORM_TRAINING",
    "model_weights_sha256":None,"model_revision":"UNKNOWN",
    "status":"OBSERVED_SYNTHETIC_AGGREGATES_NO_SCIENTIFIC_ADMISSION",
    "n_runs":len(synthetic_runs),"n_matched_pairs":len(paired),
    "n_quality_regressions":sum(x["quality_regressed"] for x in paired),
    "n_faster_tool_pairs":sum(x["tool_is_faster"] for x in paired),
    "paired_observations":paired,"run_metrics":synthetic_runs,
    "limitations":["Hosted teammate lane, separate from private local training",
       "Reported single-run metrics not blinded heldout scientific improvement",
       "Speed and field correctness assessed jointly; some tool arms lose quality",
       "Model weights and revision not pinned in public aggregate; UNKNOWN",
       "Receipt hash identifies local artifact, not independent content review"]},
  "engineering_promotion":{"state":"COMMITTED_TO_MAIN","source_commit":commit,
    "caveat":"Engineering source integration is not scientific admission or runtime deployment"},
  "judge_workstreams":[{"name":w["name"],"prs_as_reported":w.get("prs"),
    "stage_states":dict(zip(fig["stages"],w["states"])),
    "source_note":w.get("note")} for w in fig["workstreams"]],
  "index_scope":"Every Git-tracked JSON or JSONL under data/evidence/dashboard/docs/figures/bench; identities only, not source contents",
  "inventory":inventory,"inventory_count":len(inventory),
  "inventory_sha256_merkle_root":merkle(inventory),
  "inventory_merkle_recipe":"SHA256('FF_GOV_LEAF_V1'+NUL+sorted canonical JSON+LF); SHA256('FF_GOV_NODE_V1'+NUL+raw left+raw right); odd carry",
  "limits":["Historical derived records only; no model inference or new clinical claim","No FHIR patient content, raw PDF, image or weight binaries copied","No prospective unseen-layout confirmation","Source main can advance, requiring a successor ledger","DAISY method abstract only; NOT_COMPUTED is not a zero-value observation"]
 }
if __name__=="__main__":
 obj=build();b=raw(obj);OUT.parent.mkdir(parents=True,exist_ok=True)
 if OUT.exists() and OUT.read_bytes()!=b:raise SystemExit("IMMUTABLE_COLLISION")
 if not OUT.exists():OUT.write_bytes(b)
 print(json.dumps({"state":"EXECUTED_READBACK","parent":obj["parent_main_commit"],"events":obj["evidence_counts"],
  "files":obj["inventory_count"],"root":obj["inventory_sha256_merkle_root"],"file_sha256":sha(b)},sort_keys=True))
