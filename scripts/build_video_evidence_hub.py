#!/usr/bin/env python3
"""Frozen Frontier Forms video evidence manifest — read-only source extraction.

No model execution, no remote calls, no new statistical inference or promotions.
Scans only committed synthetic aggregate evidence, never exports patient inputs.
"""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"docs/judges/VIDEO_EVIDENCE_MANIFEST_20261102.json"
SOURCE_FILES=[
"docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json",
"docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json",
"docs/judges/PROMOTION_AND_NEGATIVE_RESULTS_V2_20261102.json",
"evidence/redteam/trained_gain/trained_gain_summary.json",
"evidence/forms_model/M0-zeroshot/summary.json",
"evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json",
"evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json",
"docs/judges/FRONTIER_FORMS_GANTT_EVIDENCE_V2_20261102.json",
"docs/figures/accomplishment_heatmap.json",
"bench/charts/live_metrics.json"
]
def canon(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def read(path):return json.loads((ROOT/path).read_bytes())
def url(path):return "https://github.com/biobitworks/frontier-forms/blob/main/"+path
def pr(n):return "https://github.com/biobitworks/frontier-forms/pull/"+str(n)
def assertclose(a,b):return abs(a-b)<1e-9
def build():
 base=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip()
 sources=[{"path":p,"sha256":digest((ROOT/p).read_bytes()),"byte_count":(ROOT/p).stat().st_size,
           "url":url(p)} for p in SOURCE_FILES]
 j=read(SOURCE_FILES[0]);ocr=read(SOURCE_FILES[1]);prom=read(SOURCE_FILES[2])
 gain=read(SOURCE_FILES[3]);m0=read(SOURCE_FILES[4]);gate=read(SOURCE_FILES[5]);gov=read(SOURCE_FILES[6]);gantt=read(SOURCE_FILES[7]);fig=read(SOURCE_FILES[8]);hosted=read(SOURCE_FILES[9])
 assert j["outcome_event_root"]==ocr["predecessor_judge_outcome_root"]
 assert gate["admit"]["clinical_or_model_superiority_supported"] is False
 assert prom["scientifically_replicated_promotions"]==0
 assert ocr["scientific_admission"].startswith("HOLD")
 assert len(j["fco"]["rows"])==12
 assert len(j["yolo_training"])==2
 assert len(hosted["runs"])==48
 arms={a["arm"]:a for a in ocr["arms"]}
 assert assertclose(arms["A1"]["delta_all7"],8/46)
 assert assertclose(arms["A2"]["delta_all7"],-5/46)
 assert arms["A1"]["p_holm_3_comparisons"]<0.05
 assert arms["A2"]["p_holm_3_comparisons"]>=0.05
 # This research-evidence admission does not change FCAR scientific admission.
 cases=[
  {"id":"FF-FCO-L1L3","lane":"shared","title":"Source-bound FCO/FCG L1 × L3 transformation",
   "baseline":"Frozen B0","challenger":"B0 + L1 + L3","n_cases":54,"baseline_correct":18,"challenger_correct":30,
   "delta":12/54,"unit":"complete-form success","mcnemar_p":0.00048828125,"holm_p":0.005859375,
   "patient_bootstrap_ci95":[0.07407407407407407,0.37037037037037035],
   "finding":"DISCOVERY_POSITIVE","evidence_admission":"ADMITTED_DISCOVERY_RECORD","scientific_admission":"HOLD",
   "mechanism":"Source-bound field retrieval plus filtering; neural weights unchanged",
   "why":"Independent source evidence and filtering make more deterministic answers usable without unsupported fills",
   "limitation":"Modules designed after B0 error inspection; no untouched prospective replication",
   "model_or_weight":"Deterministic FCO/FCG; neural weights unchanged","source_path":SOURCE_FILES[0],
   "pr":[10,17,64],"root_ref":"outcome_event_root"},
  {"id":"FF-OCR-A1","lane":"claude","title":"Learned OCR post-correction",
   "baseline":"A0 native-page OCR plus rules","challenger":"A1 learned text correction",
   "n_cases":46,"baseline_correct":14,"challenger_correct":22,"delta":arms["A1"]["delta_all7"],
   "unit":"all-seven-fields complete form","mcnemar_p":arms["A1"]["mcnemar_exact"],
   "holm_p":arms["A1"]["p_holm_3_comparisons"],"patient_bootstrap_ci95":arms["A1"]["patient_cluster_bootstrap95"],
   "finding":"DISCOVERY_POSITIVE","evidence_admission":"ADMITTED_DISCOVERY_RECORD","scientific_admission":"HOLD",
   "mechanism":"Train-only OCR text correction; not Qwen neural-weight fine-tuning",
   "why":"Corrects synthetic reading/transcription errors while keeping source text trackable",
   "limitation":"Preregistration timing and prospective replication not independently verified; 23 synthetic cases yield 46 clean/scan images",
   "model_or_weight":"Learned OCR correction parameters; neural checkpoint digest NOT_APPLICABLE",
   "source_path":SOURCE_FILES[1],"pr":[51,58,61,63,64],"root_ref":"ocr_event_root"},
  {"id":"FF-OCR-A2","lane":"claude","title":"YOLO detector crops before OCR",
   "baseline":"A0 native-page OCR plus rules","challenger":"A2 YOLOv8n crops then OCR",
   "n_cases":46,"baseline_correct":14,"challenger_correct":9,"delta":arms["A2"]["delta_all7"],
   "unit":"all-seven-fields complete form","mcnemar_p":arms["A2"]["mcnemar_exact"],
   "holm_p":arms["A2"]["p_holm_3_comparisons"],"patient_bootstrap_ci95":arms["A2"]["patient_cluster_bootstrap95"],
   "finding":"NEGATIVE_NULL","evidence_admission":"ADMITTED_NEGATIVE_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Trained YOLOv8n field-region crops; distinct from OCR correction",
   "why":"Crops disrupted useful text context; increasing model count did not guarantee better reading",
   "limitation":"Null after multiplicity correction; crop effect not proven generalizable",
   "model_or_weight":"YOLOv8n epoch weights recorded in training source; bytes not independently rehashed in audit",
   "source_path":SOURCE_FILES[1],"pr":[51,63,64],"root_ref":"ocr_event_root"},
  {"id":"FF-OCR-A3","lane":"claude","title":"YOLO crops plus learned correction",
   "baseline":"A0 native-page OCR plus rules","challenger":"A3 cropped OCR + correction",
   "n_cases":46,"baseline_correct":14,"challenger_correct":15,"delta":arms["A3"]["delta_all7"],
   "unit":"all-seven-fields complete form","mcnemar_p":arms["A3"]["mcnemar_exact"],
   "holm_p":arms["A3"]["p_holm_3_comparisons"],"patient_bootstrap_ci95":arms["A3"]["patient_cluster_bootstrap95"],
   "finding":"NULL","evidence_admission":"ADMITTED_NULL_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Combines crop detector with learned OCR correction",
   "why":"The correction did not reliably recover loss introduced by cropping",
   "limitation":"No statistically established improvement",
   "model_or_weight":"YOLOv8n + learned correction, same evaluated synthetic cases",
   "source_path":SOURCE_FILES[1],"pr":[51,63,64],"root_ref":"ocr_event_root"},
  {"id":"FF-BOX-LOGISTIC","lane":"chatgpt","title":"Learned logistic bbox validator versus OpenCV",
   "baseline":"OpenCV field contour detector","challenger":"Local logistic regression field box validator",
   "n_cases":540,"baseline_correct":540,"challenger_correct":540,"delta":0,
   "unit":"box localization","mcnemar_p":1,"holm_p":None,"patient_bootstrap_ci95":[0,0],
   "finding":"NEGATIVE_NO_GAIN","evidence_admission":"ADMITTED_NEGATIVE_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Trained geometric classifier independent of text parser",
   "why":"Deterministic OpenCV was already at ceiling; no value from more complex box model on existing layout",
   "limitation":"Known layouts; box accuracy distinct from field-answer accuracy",
   "model_or_weight":j["vision_models"]["learned_logistic"]["weights_sha256"],
   "source_path":SOURCE_FILES[0],"pr":[14,64],"root_ref":"outcome_event_root"},
  {"id":"FF-RF-63","lane":"chatgpt","title":"Random Forest geometry / shape / pixel LOMO",
   "baseline":"OpenCV box candidate control","challenger":"Locally trained RF, 63 synthetic patients",
   "n_cases":54,"baseline_correct":54,"challenger_correct":34,
   "delta":(34-54)/54,"unit":"complete-page box localization",
   "mcnemar_p":None,"holm_p":None,"patient_bootstrap_ci95":[-0.5185185,-0.2222222],
   "finding":"NEGATIVE_NO_GAIN","evidence_admission":"ADMITTED_NEGATIVE_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Eight geometry/shape/pixel feature masks, 10/30/63 training-size arms",
   "why":"Shape-only matched OpenCV; extra pixel features hurt thresholded F1",
   "limitation":"Discovery and layout overlap; 54 pages from 18 patients",
   "model_or_weight":j["vision_models"]["random_forest"][-1]["weights_sha256"],
   "source_path":SOURCE_FILES[0],"pr":[15,64],"root_ref":"outcome_event_root"},
  {"id":"FF-M0-QWEN","lane":"claude","title":"Untrained Qwen 0.5B field-answer baseline",
   "baseline":"Frozen deterministic B0","challenger":"M0 zero-shot Qwen2.5-0.5B",
   "n_cases":92,"baseline_correct":37,"challenger_correct":0,"delta":-37/92,
   "unit":"complete-form paired successes across validation+test","mcnemar_p":None,"holm_p":None,"patient_bootstrap_ci95":None,
   "finding":"NEGATIVE_NO_GAIN","evidence_admission":"ADMITTED_NEGATIVE_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Actual local model answers, no fine-tuning, MPS on MacBook Pro",
   "why":"Demonstrates model-only guesses do not replace source-bound deterministic retrieval",
   "limitation":"Baseline has its own split counts; no SFT gain claim, no imported model binary",
   "model_or_weight":"qwen2.5:0.5b untrained; runtime checkpoint digest not bound here",
   "source_path":SOURCE_FILES[4],"pr":[62],"root_ref":None},
  {"id":"FF-APPLE-BOX-CONTEXT","lane":"chatgpt","title":"Diagnostic boxes inserted before OCR",
   "baseline":"Clean Apple Vision OCR","challenger":"Bounding boxes drawn before OCR",
   "n_cases":70,"baseline_correct":58,"challenger_correct":0,"delta":-58/70,
   "unit":"exact OCR field transcription","mcnemar_p":None,"holm_p":None,"patient_bootstrap_ci95":None,
   "finding":"NEGATIVE_NO_GAIN","evidence_admission":"ADMITTED_NEGATIVE_RECORD","scientific_admission":"NOT_PROMOTED",
   "mechanism":"Image annotation versus unmodified native raster",
   "why":"Visualization overlays altered pixels; draw boxes after reading rather than before",
   "limitation":"Measured diagnostic preprocessing, not neural weight-training effect",
   "model_or_weight":"Apple Vision native OCR, framework-provided; no weight digest",
   "source_path":SOURCE_FILES[0],"pr":[22,64],"root_ref":"outcome_event_root"}
 ]
 assert gov["admission"]["scientifically_supported_promotions"]==0
 for c in cases:
  if c["scientific_admission"] not in ("HOLD","NOT_PROMOTED"):raise ValueError("PROMOTION_WITHOUT_PROSPECTIVE_REPLICATION")
  if c["source_path"] not in SOURCE_FILES:raise ValueError("SOURCE_ABSENT")
  c["source_url"]=url(c["source_path"])
  c["pr_urls"]=[pr(n) for n in c["pr"]]
  c["source_file_sha256"]=next(x["sha256"] for x in sources if x["path"]==c["source_path"])
  c["record_schema"]="frontier_forms.video_case.v1"
 groups=[]
 for entry in j["yolo_training"]:
  epochs=entry.get("epochs",[])
  groups.append({"source":SOURCE_FILES[0],"model":"YOLOv8n local training","source_lane":"Claude Code / local",
    "run_name":entry.get("lane") or entry.get("name") or "separate scan arm",
    "best_checkpoint_sha256_recorded":entry.get("best_weights_sha256"),
    "n_epochs":len(epochs),"epochs":[{"epoch":e.get("epoch"),"state":e.get("state"),
      "dev_fields_ok":e.get("dev_fields_ok"),"dev_fields_total":e.get("dev_fields_total"),
      "gain_vs_prev":e.get("gain_vs_prev"),"weights_sha256":e.get("weights_sha256"),
      "model_weight_file_local":e.get("model_weight_file_local"),
      "admission":e.get("admission")} for e in epochs],
    "scope":"epoch dev results; weights reported, not independently rehashed in this audit",
    "source_url":url(SOURCE_FILES[0])})
 if any(len(g["epochs"])!=30 for g in groups):raise ValueError("INCOMPLETE_YOLO_EPOCHS")
 output={
 "schema":"frontier_forms.video_storyboard_manifest.v1",
 "program_id":"frontier-forms","parent_git_sha":base,
 "source_classification":"MITRE Synthea synthetic FHIR (patient fixtures) + separately labeled teammate synthetic hosted pilot",
 "open_epic_role":"FHIR interoperability and local form schema only; NOT production Epic writeback",
 "scientific_admission":"HOLD_NO_INDEPENDENT_PI_ADMISSION",
 "scientific_superiority_promotions":0,"operational_discovery_promotions":prom["discovery_promotions"],
 "evidence_admission_policy":{"DATA_ADMITTED":"Committed synthetic-source receipt with immutable byte identity and program boundary; does not itself certify rights or medical truth",
  "DISCOVERY_ADMITTED":"Execution-based observed contrast retained with matched-case statistics and limitations; not a scientific promotion",
  "NEGATIVE_OR_NULL_ADMITTED":"Observed negative/null result preserved as genuine research evidence, with exact source reference",
  "SCIENTIFIC_PROMOTION":"REQUIRES prospective independent cohort/form replication and human PI authorization; not satisfied"},
 "results":cases,
 "yolo_epoch_groups":groups,
 "roots":[
 {"title":"Synthetic source cohort root","root":gate["freeze"]["subset_cohort_root"],"scope":"100 distinct source patient occurrences; root from prior computed freeze","source":url(SOURCE_FILES[5])},
 {"title":"Independent judge 82-event outcome root","root":j["outcome_event_root"],"scope":"82 outcome-event leaves, existing prior computation; not recomputed by video generator","source":url(SOURCE_FILES[0])},
 {"title":"OCR correction statistical successor root","root":ocr["ocr_event_root"],"scope":"Independent reanalysis of 3 arms; successor linked to judge outcome root","source":url(SOURCE_FILES[1])},
 {"title":"Governance V2 file-inventory Merkle root","root":gov["inventory_sha256_merkle_root"],"scope":"521 source JSON/JSONL identity leaves, from prior ledger; not model gain","source":url(SOURCE_FILES[6])}],
 "hardware":[
 {"name":"magicSTUDIObox","class":"LOCAL_PRIVATE","cpu":"Apple Silicon, 10 CPU cores","memory":"32 GiB unified memory (previous device readback)","evidence":"Apple Vision, 3B vision inference, local RF training, verification and HTML dashboard","limits":"No NVIDIA/CUDA GPU claim; test server listens on 127.0.0.1"},
 {"name":"magicPRObox","class":"LOCAL_PRIVATE","cpu":"Apple Silicon, 8 CPU cores","memory":"16 GiB unified memory (previous device readback)","evidence":"Claude SWE, Qwen2.5-0.5B zero-shot MPS inference and local form training lane","limits":"No private source data sent to hosted inference by this lane"},
 {"name":"PostgreSQL / Supabase","class":"SERVERLESS_TEAM_REPORTED","cpu":"Not applicable","memory":"Not verified","evidence":"Teammate reports 100 synthetic imports and operational schema","limits":"Independent live database parity/readback NOT_TESTED; not source of admission"},
 {"name":"Fireworks hosted synthetic benchmark","class":"HOSTED_TEAMMATE","cpu":"Remote hosted API","memory":"Unknown","evidence":"48 synthetic aggregate runs and 24 matched pairs in existing teammate benchmark","limits":"Not our local training or a proven model generalization gain"}
 ],
 "hosted_benchmark":{"n_runs":len(hosted["runs"]),"n_pairs":gov["teammate_hosted_benchmark"]["n_matched_pairs"],
   "n_faster_tool_pairs":gov["teammate_hosted_benchmark"]["n_faster_tool_pairs"],
   "n_quality_regressions":gov["teammate_hosted_benchmark"]["n_quality_regressions"],
   "source":url(SOURCE_FILES[9]),"attribution":"Teammate hosted synthetic aggregate only"},
 "workflow":[
 {"step":"01 FREEZE","claim":"Synthea patient FHIR R4 → SHA-bound frozen subset, 63/19/18 patients, B0 and oracle","gate":"RECORDED_PENDING_PI_REVIEW","source":url(SOURCE_FILES[5])},
 {"step":"02 TRANSFORM","claim":"Read FHIR patient passport → stable typed fields, source refs, UNKNOWN/ABSTAIN, FCO events","gate":"IMPLEMENTED_DISCOVERY","source":url(SOURCE_FILES[0])},
 {"step":"03 CHALLENGE","claim":"B0 vs L1-L3 vs combinations and LOMO; Apple OCR/YOLO/Qwen independent arms","gate":"EXECUTED_DISCOVERY","source":url(SOURCE_FILES[0])},
 {"step":"04 MEASURE","claim":"Paired McNemar, Holm, patient-cluster bootstrap, per-result source/leaf hashes","gate":"VERIFIED_EXISTING_RECEIPTS","source":url(SOURCE_FILES[1])},
 {"step":"05 REPLICATE","claim":"Locked, unseen patient and form family with independently frozen gold oracle","gate":"NOT_TESTED","source":url(SOURCE_FILES[5])},
 {"step":"06 ADMIT","claim":"Admit data and discovery records as research; withhold scientific superiority","gate":"HOLD_NO_INDEPENDENT_PI_ADMISSION","source":url(SOURCE_FILES[5])}
 ],
 "agent_lanes":[
 {"agent":"ChatGPT · PI/PM independent audit","code":"CHATGPT","role":"Cyan: independently challenges assumptions, computes/verifies paired uncertainty and roots, retains negative results and promotion firewall",
  "delivered":["FCO/LOMO scientific review and source receipt checks","Local box-detection challengers and 10/30/63 training-size ablations","Independent Apple OCR and patient-cluster reanalysis","Merkle/FCAR evidence gate and data-quality boundary","82-event outcome ledger, judge figures and negative preservation"],
  "source_prs":[14,15,18,49,60,64],"cannot_claim":"Source model-training success or Claude's original demo assets as independently authored"},
 {"agent":"Claude Code · SWE/PM implementation","code":"CLAUDE","role":"Amber: creates test server, frozen workflows, training scripts, forms, vision/OCR challengers and live demo assets",
  "delivered":["100-patient synthetic Synthea cohort / frozen B0 / local form server","Paired FCO/FCG module execution and LOMO variants","YOLOv8n 30+30 epoch trained detector logs and learned OCR correction","Actual local zero-shot Qwen field-answer baseline","Original figures, synthetic screenshot/PDF demo and heatmaps"],
  "source_prs":[10,51,57,58,62,63,65],"cannot_claim":"Independently admitted clinical generalization or ChatGPT's independent verification as Claude's own"},
 {"agent":"Teammates · API/serverless integration","code":"TEAM","role":"Violet: synthetic hosted benchmark, database integration and sponsor-specific connectors, not private local model training",
  "delivered":["PostgreSQL/Supabase operational schema and reported 100 synthetic import","48-run synthetic hosted-model pilot with paired time/quality comparisons","GitHub PR and Actions integration surface"],
  "source_prs":[4,23,26,59],"cannot_claim":"Verified local/private EHR source parity or prospective model superiority"}
 ],
 "sponsor_next":[
 {"target":"NVIDIA","state":"PROPOSED_NOT_EXECUTED_THIS_LANE","task":"Run exact frozen synthetic form benchmark on an authorized NVIDIA GPU; save device/driver/CUDA/GPU memory, checkpoint bytes, Nsight trace, per-field outputs and energy/runtime receipts. Compare against unchanged Apple Silicon arm.","owner":"NVIDIA hardware owner / teammate","proof":"CUDA hardware readback + matched-case paired outputs + source hashes; do not claim NVIDIA GPU use now","reference":"https://docs.nvidia.com/nsight-systems/AnalysisGuide/index.html"},
 {"target":"Fireworks","state":"TEAMMATE_SYNTHETIC_PILOT_ONLY","task":"Pin frontier endpoint/version and task-time/cost; run on approved synthetic-only matched forms, record raw JSON answer hashes, paired frontier baseline + custom open model, no private source exports.","owner":"Fireworks API teammate","proof":"Endpoint IDs, auth-safe request receipts, output digests, matched cases, McNemar/cluster CI, errors/cost","reference":"https://docs.fireworks.ai/"},
 {"target":"Microsoft / GitHub","state":"CI_IN_USE; ATTESTATIONS_PROPOSED","task":"Attach signed artifact attestations for released JSON evidence manifests, verify commit/CI provenance, lock required checks, split local synth-only evidence ingestion from hosted API job permissions.","owner":"GitHub Actions / DevOps teammate","proof":"Signed attestation verification receipt + exact subject digest; independent FCAR gate PASS","reference":"https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations"}
 ],
 "presentation":{"github_root":"https://github.com/biobitworks/frontier-forms","notion_page":"PENDING_CREATE",
  "entry_html":"docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html",
  "entry_markdown":"docs/judges/VIDEO_START_HERE_20261102.md",
  "demo_launcher":"python3 -m http.server 8787 --bind 127.0.0.1",
  "demo_url_local":"http://127.0.0.1:8787/docs/judges/VIDEO_EVIDENCE_STORYBOARD_20261102.html",
  "github_pages":"NOT_CONFIGURED_OR_UNVERIFIED"},
 "source_receipts":sources,
 "assertion":"The presentation admits valid synthetic data/discovery evidence for research review; it does not independently certify original source rights or overwrite the Frontier Forms scientific admission HOLD."}
 return output
def main():
 d=build();out=canon(d);DEST.parent.mkdir(parents=True,exist_ok=True)
 if DEST.exists() and DEST.read_bytes()!=out:raise ValueError("IMMUTABLE_VIDEO_MANIFEST_DRIFT")
 if not DEST.exists():DEST.write_bytes(out)
 print(json.dumps({"state":"BUILT","base":d["parent_git_sha"],"sources":len(d["source_receipts"]),
 "cases":len(d["results"]),"epochs":sum(len(x["epochs"]) for x in d["yolo_epoch_groups"]),
 "no_scientific_promotions":d["scientific_superiority_promotions"]==0,"sha256":digest(out)}))
if __name__=="__main__":main()
