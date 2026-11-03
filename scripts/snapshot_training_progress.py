#!/usr/bin/env python3
"""Append-only Frontier Forms training/ablation snapshot. Actual evidence, no training inference."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CANON = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
SHA = lambda x: hashlib.sha256(x).hexdigest()
def git(*args):
    return subprocess.check_output(["git", *args], cwd=R)
def read(p):
    return json.loads((R / p).read_text())
def exact_p(b, c):
    n=b+c
    if n==0:return 1.0
    return min(1.0, 2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n)
def merkle(items):
    if not items:raise ValueError("NO_LEAVES")
    a=[hashlib.sha256(b"\x00"+CANON(x)).digest() for x in items]
    while len(a)>1:
        a=[hashlib.sha256(b"\x01"+a[i]+(a[i+1] if i+1<len(a) else a[i])).digest() for i in range(0,len(a),2)]
    return a[0].hex()
def show(ref,path):
    return git("show",f"{ref}:{path}")
def subsource(ref,path):
    raw=show(ref,path)
    return {"git_commit":git("rev-parse",ref).decode().strip(),"path":path,"file_sha256":SHA(raw)}
def build(trainlog, outroot, pointer):
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    events=[]
    group=read("evidence/forms_arms/run_v1/FCG_ARMS_V1.json")
    cluster=read("evidence/PATIENT_CLUSTER_BOOTSTRAP_V1.json")
    cluster_map={(r["parent"],r["child"],r["split"]):r for r in cluster["rows"] if r["family"]=="module_arms"}
    nodes={n["arm"]:n for n in group["nodes"]}
    for name,n in nodes.items():
        path=R/"evidence/forms_arms/run_v1/predictions"/(name+".jsonl")
        raw=path.read_bytes()
        if SHA(raw)!=n["predictions_sha256"]:raise AssertionError("PREDICTIONS_SOURCE_MISMATCH:"+name)
    if merkle(sorted(n["output_root"] for n in nodes.values()))!=group["graph_root"]:
        # graph's root is constructed from hex digest bytes, not JSON leaves:
        level=[hashlib.sha256(b"\x00"+bytes.fromhex(s)).digest() for s in sorted(n["output_root"] for n in nodes.values())]
        while len(level)>1:
            level=[hashlib.sha256(b"\x01"+level[i]+(level[i+1] if i+1<len(level) else level[i])).digest()
                   for i in range(0,len(level),2)]
        if level[0].hex()!=group["graph_root"]:raise AssertionError("GRAPH_ROOT_MISMATCH")
    for e in group["edges"]:
        if e["kind"] not in ("addition_to_B0","lomo_restore","chain"):continue
        stat=e["test"];tab=stat["table"]
        p=exact_p(tab["baseline_only"],tab["challenger_only"])
        if abs(p-stat["p_mcnemar_exact_two_sided"])>1e-12:raise AssertionError("MCNEMAR_MISMATCH")
        if tab["n"]!=54:raise AssertionError("TEST_DENOMINATOR")
        pc=cluster_map.get((e["parent"],e["child"],"test"))
        if pc is None:raise AssertionError("CLUSTER_BOOTSTRAP_MISSING:"+str(e))
        events.append({"id":"FF-LOMO-"+e["parent"]+"-to-"+e["child"],"family":"fco_lomo",
            "status":"DISCOVERY_POSITIVE_NOT_PROMOTED" if stat["delta"]>0 and p<.05 and pc["ci_patient_cluster_95"][0]>0 else ("NEGATIVE_OR_TIE" if stat["delta"]<=0 else "UNSUPPORTED_POSITIVE"),
            "parent":e["parent"],"child":e["child"],"leaf":e["leaf"],"intervention":e["kind"],
            "model":"Deterministic FCO/FCG rules; neural weights unchanged",
            "model_weights_changed":False,"model_weights_sha256":None,
            "metric":"required_field_full_form_success","population":"18 synthetic patients; 54 forms; test split",
            "n":54,"delta":stat["delta"],"ci95_patient_cluster":pc["ci_patient_cluster_95"],
            "ci95_template_stratified":stat["ci_delta_bootstrap_stratified_95"],
            "mcnemar_p_two_sided":p,"paired_table":tab,
            "bootstrap_reps":10000,"source_graph_root":group["graph_root"],
            "source_file_sha256":SHA((R/"evidence/forms_arms/run_v1/FCG_ARMS_V1.json").read_bytes()),
            "replication":"NOT_TESTED; original test cases inspected before rules designed",
            "claim_ceiling":"synthetic discovery-only paired ablation"})
    detector=read("evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json")
    for e in detector["edges"]:
        if e["kind"] not in ("single_from_none","lomo_restore"):continue
        tab=e["recall_table"]
        p=exact_p(tab["baseline_only"],tab["challenger_only"])
        if abs(p-e["recall_gain_mcnemar_p"])>1e-10:raise AssertionError("DETECTOR_P_MISMATCH")
        events.append({"id":"FF-DETECTOR-"+e["parent"]+"-to-"+e["child"],"family":"detector_lomo",
           "status":"DISCOVERY_POSITIVE_NOT_PROMOTED" if e["recall_gain"]>0 and p<.05 else "NEGATIVE_OR_TIE",
           "parent":e["parent"],"child":e["child"],"leaf":e["leaf"],"intervention":e["kind"],
           "model":"Deterministic Merkle / Lean4 / FCO source-binding detectors","model_weights_changed":False,
           "model_weights_sha256":None,"metric":"synthetic_injected_error_instance_recall",
           "population":"702 injected error instances (not independent patients)","n":tab["n"],
           "delta":(tab["challenger_only"]-tab["baseline_only"])/tab["n"],"source_rounded_delta":e["recall_gain"],"ci95_patient_cluster":None,
           "ci95_error_type_stratified":e["recall_gain_ci95"],
           "mcnemar_p_two_sided":p,"paired_table":tab,
           "false_positive_cost":e["fp_cost"],"bootstrap_reps":10000,
           "source_graph_root":None,
           "source_file_sha256":SHA((R/"evidence/forms_detectors/run_v1/DETECTOR_RESULTS_V1.json").read_bytes()),
           "replication":"NOT_TESTED; error rules constructed with source passport; patient dependence not accounted for",
           "claim_ceiling":"synthetic detector discovery, not model training"})
    # Fixed source HEADs: do not turn independent architectures/sizes into longitudinal epochs.
    rf_ref="origin/feat/local-vision-box-validator-pi-audit-20261102"
    rf_src=subsource(rf_ref,"evidence/local_box_validator/registry.json")
    registry=json.loads(show(rf_ref,"evidence/local_box_validator/registry.json"))
    for x in registry["events"]:
        if not x["id"].startswith("FF-BOX-V2-"):continue
        obj=json.loads(show(rf_ref,"evidence/local_box_validator/"+x["file"]))
        full=next(a for a in obj["results"] if a["arm"]=="RF_geometry+shape+pixels")
        # Independent root replay uses the independent RF engine's declared newline canonicalization.
        canon_rf=lambda o: (json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        rf_level=[hashlib.sha256(b"FF_VISION_LEAF_V1\x00"+canon_rf(leaf)).digest() for leaf in obj["fco_leaves"]]
        while len(rf_level)>1:
            rf_level=[hashlib.sha256(b"FF_VISION_NODE_V1\x00"+rf_level[i]+rf_level[i+1]).digest()
                      if i+1<len(rf_level) else rf_level[i] for i in range(0,len(rf_level),2)]
        if rf_level[0].hex()!=obj["fco_merkle_root"] or obj["fco_merkle_root"]!=x["fco_merkle_root"]:
            raise AssertionError("INDEPENDENT_RF_ROOT_MISMATCH:"+x["id"])
        events.append({"id":"FF-RF-CROSSSECTION-"+x["id"],"family":"training_size_cross_section",
           "status":"NEGATIVE_NO_GAIN","parent":x["parent"],"child":x["id"],
           "model":"RandomForestClassifier 24 trees","model_weights_changed":True,
           "model_weights_sha256":x["model_checkpoint_sha256"],"train_patients":x["n_train_patients"],
           "eval_patients":x["n_eval_patients"],"metric":"bbox_f1","value":full["f1"],
           "control_value":1.0,"delta":full["f1"]-1.0,
           "ci95_patient_cluster":full["paired_vs_cv_b0"]["patient_cluster_bootstrap95"],
           "mcnemar_p_two_sided":full["paired_vs_cv_b0"]["mcnemar_exact_descriptive"],
           "n":full["n_test_images"],"source_root":x["fco_merkle_root"],
           "source_file_sha256":SHA(show(rf_ref,"evidence/local_box_validator/"+x["file"])),
           "source_ref":rf_src,"replication":"NOT_TESTED on unseen form template",
           "claim_ceiling":"cross-sectional distinct training-size runs, not one continuing checkpoint",
           "caveat":"McNemar treats 3 forms/patient as independent; patient-cluster CI is primary"})
    box_ref="origin/feat/local-vision-box-validator-20261102"
    boxpath="evidence/forms_box_validator/run_v3/summary.json"
    box=json.loads(show(box_ref,boxpath))
    events.append({"id":"FF-LOGISTIC-BBOX-CONTROL-20261102","family":"model_weight_comparison",
       "status":"NEGATIVE_NO_GAIN","parent":"CV-contour-control","child":"Logistic-regression-box-v1",
       "model":"CPU LogisticRegression (trained 3 blank forms)","model_weights_changed":True,
       "model_weights_sha256":box["weights_sha256"],
       "metric":"bbox_recall","value":box["learned_box_recall"],
       "control_value":box["baseline_box_recall"],"delta":box["learned_minus_baseline_recall"],
       "ci95_patient_cluster":box["paired_patient_bootstrap_95_ci"],
       "mcnemar_p_two_sided":box["mcnemar_exact_two_sided"],"n":box["n_field_boxes"],
       "source_root":box["prediction_root"],"source_ref":subsource(box_ref,boxpath),
       "replication":"NOT_TESTED on new layout",
       "claim_ceiling":"same template geometry, no weight superiority"})
    # Local trainer log: non-JSON lines preserved via file digest; no claim of weights until a real adapter exists.
    logpath=Path(trainlog).expanduser()
    if not logpath.is_file():raise FileNotFoundError(logpath)
    raw=logpath.read_bytes()
    samples=[]
    for line in raw.splitlines():
        try:v=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(v,dict) and "epoch" in v:
            samples.append(v)
    if not samples:raise AssertionError("NO_TRAINER_TELEMETRY")
    valid_losses=[s for s in samples if s.get("val_loss") is not None]
    adapter_dir=logpath.parent/"forms_sft_v1"/"adapter"
    checkpoints={p.name:SHA(p.read_bytes()) for p in sorted(adapter_dir.glob("*")) if p.is_file()} if adapter_dir.exists() else {}
    events.append({"id":"FF-QWEN05-LOCAL-SFT-SNAPSHOT-"+stamp,"family":"actual_training_snapshot",
       "status":"OBSERVED_BASELINE_ONLY" if len(valid_losses)==1 else "OBSERVED_TRAINING_NO_HELDOUT_PROMOTION",
       "parent":None,"child":"Qwen/Qwen2.5-0.5B-Instruct LoRA rank16",
       "model":"Qwen/Qwen2.5-0.5B-Instruct; LoRA rank16 lr0.0002","model_weights_changed":bool(checkpoints),
       "model_weights_sha256":checkpoints or None,
       "metric":"validation_completion_crossentropy_loss","n":380,
       "training_log_sha256":SHA(raw),"log_last_modified_utc":dt.datetime.fromtimestamp(logpath.stat().st_mtime,dt.timezone.utc).isoformat(),
       "observed_at_utc":now,"points":samples,
       "baseline_val_loss":valid_losses[0]["val_loss"],"latest_val_loss":valid_losses[-1]["val_loss"],
       "delta_val_loss":valid_losses[-1]["val_loss"]-valid_losses[0]["val_loss"] if len(valid_losses)>1 else None,
       "heldout_accuracy":None,"paired_mcnemar_p":None,
       "ci95_patient_cluster":None,
       "replication":"NOT_TESTED","claim_ceiling":"training telemetry; no frozen held-out paired accuracy gain",
       "warning":"Epoch labels lack timestamps; observed_at is snapshot collection time, not training-step time"})
    events.append({"id":"FF-VITA-DAISY-ABSTRACT-ONLY","family":"methodology_only",
        "status":"NOT_COMPUTED","parent":None,"child":"Vita-DAISY-inspired admission map",
        "model":"No shared checkpoint, no shared training job","model_weights_changed":False,"model_weights_sha256":None,
        "metric":"DAISY-specific_gain","delta":None,"ci95_patient_cluster":None,"mcnemar_p_two_sided":None,
        "source_root":None,"replication":"NOT_TESTED",
        "claim_ceiling":"abstraction only: freeze → challenge → replicate → admit; do not join program roots"})
    # Family-wise Holm correction: controls multiplicity across observed single-leaf edges.
    for family in ("fco_lomo","detector_lomo"):
        subset=sorted([e for e in events if e["family"]==family],key=lambda r:r["mcnemar_p_two_sided"])
        running=0.0
        for rank,e in enumerate(subset):
            running=max(running,(len(subset)-rank)*e["mcnemar_p_two_sided"])
            e["holm_adjusted_p"]=min(1.0,running)
            e["hypothesis_family_n"]=len(subset)
            e["familywise_method"]="Holm-Bonferroni exact paired McNemar"
            # Statistical significance is insufficient for any scientific promotion.
            e["promoted"]=False
    prev=None
    if pointer.exists():
        prev=json.loads(pointer.read_text())
        if prev.get("root"):
            previous_dir=R/prev["source_snapshot"]
            assert previous_dir.is_dir() and (previous_dir/"manifest.json").is_file(),"PREDECESSOR_NOT_FOUND"
            assert json.loads((previous_dir/"manifest.json").read_text())["root"]==prev["root"],"PREDECESSOR_ROOT_MISMATCH"
    manifest={"schema":"frontier-forms.training-progress-snapshot.v1","timestamp_utc":now,
       "program_id":"frontier-forms","source_cohort_root":group["dataset_root"],
       "predecessor_snapshot_root":prev["root"] if prev else None,
       "predecessor_snapshot_path":prev["source_snapshot"] if prev else None,
       "fco_ablation_graph_root":group["graph_root"],
       "source_code_commit":git("rev-parse","HEAD").decode().strip(),
       "event_count":len(events),"root_scheme":"SHA256(0x00||canonical_json_event); SHA256(0x01||left||right), duplicate-last",
       "weights_vs_mechanism_separate":True,"multiple_testing":"Holm adjustment separately for FCO and synthetic detector families",
       "vita_daisy_scope":"ABSTRACTION_ONLY_SEPARATE_LANE",
       "root":merkle(events),"signed":"NOT_SIGNED",
       "scientific_status":"DISCOVERY_ONLY; no live model training gain admitted"}
    sub=outroot/("OBS-"+stamp+"-"+manifest["root"][:12])
    sub.mkdir(parents=True,exist_ok=False)
    (sub/"events.jsonl").write_bytes(b"".join(CANON(e)+b"\n" for e in events))
    manifest["events_file_sha256"]=SHA((sub/"events.jsonl").read_bytes())
    (sub/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    view={"schema":"frontier-forms.training-progress-view.v1","source_snapshot":sub.relative_to(R).as_posix(),
          "root":manifest["root"],"observed_at_utc":now,"events":events,
          "claim_ceiling":manifest["scientific_status"]}
    pointer.parent.mkdir(parents=True,exist_ok=True)
    pointer.write_text(json.dumps(view,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"new_snapshot":sub.relative_to(R).as_posix(),"root":manifest["root"],
      "events":len(events),"training_points":len(samples),"validation_loss_points":len(valid_losses),
      "adapter_files":len(checkpoints)},indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--training-log",required=True)
    ap.add_argument("--out-root",type=Path,default=R/"evidence/training_progress")
    ap.add_argument("--pointer",type=Path,default=R/"dashboard/training_progress_latest.json")
    a=ap.parse_args()
    build(a.training_log,a.out_root,a.pointer)
