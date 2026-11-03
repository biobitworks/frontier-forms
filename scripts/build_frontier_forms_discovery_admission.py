#!/usr/bin/env python3
"""Read-only observation/discovery admission; fail closed for scientific promotion.
Runs NO model, data transformation, statistics resampling, or Merkle computation.
Source byte SHA256 provides identity, not scientific truth.
"""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/admission/FF_DISCOVERY_AND_NOVELTY_V1.json'
FILES={
 'fcar':'evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json',
 'freeze':'data/forms_cohort_v1/GENERATION.json',
 'baseline':'evidence/baseline/BASELINE_V1.json',
 'm0':'evidence/forms_model/M0-zeroshot/summary.json',
 'ocr':'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json',
 'ocr_source':'evidence/redteam/trained_gain/trained_gain_summary.json',
 'bbox':'evidence/forms_bbox/LOCAL_BBOX_D1_D2_AUDIT_20261102.json',
 'logit':'evidence/forms_box_validator/run_v3/summary.json',
 'progress':'dashboard/training_progress_latest.json',
 'yolo_full':'evidence/redteam/detector/full/final_receipt.json',
 'yolo_no_scan':'evidence/redteam/detector/no_scan/final_receipt.json',
 'synform2':'evidence/redteam/synform2/manifest.json',
 'synform2_err':'evidence/redteam/synform2_err/manifest.json',
 'hosted':'evidence/governance/OUTCOMES_AND_PROMOTIONS_20261102_V2.json',
 'judge':'docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json',
}
SOURCE_PARENT_MAIN = '900dae04a99d58792cb216f03f02aab6c0315fdd'
SOURCE_SHA256_PINS = {'baseline': '21431b03cd46041180984f6bdc2aad2d7642f0d47fb14c5ddb15fbf746a77382', 'bbox': '8e20aa92da0122d4523082db4d9805637109a6bf097a02feacda5b30d7b80948', 'fcar': '05e8ebff7d482b4c3790ef50daf07bcb0491801b18f0abd55d9eb7ded0273279', 'freeze': 'ca8d699f5638732b9a722360045e1ab25ee552570303dc2b27e8b25840b60297', 'hosted': 'b129f660892ec97df40aa1ac12bc516bd16dfa4a306a88b1ab15db2a253fc0fa', 'judge': '69e93af7d46fbc370aaa85c6262d2454c3891a6a2b962f7e89c918ce4da29dbb', 'logit': '5ba8d2f543e6713ba5b65449c958a364c732750309ff1e8922213d323ba83d11', 'm0': '601c78b880af66e1fe01c330e0d226464302d2dbadf7b580c0d3b64898925b5c', 'ocr': 'ae50de6661b53db271aef0168cdd434743bc29f55137b865db590df4dd2112f0', 'ocr_source': '59924f66cc38ad33c2a365c16fe21846996b9258a72be007a2ee4f638cbd9348', 'progress': '22013d1b675d0544a5d27bd317d4f16e69c5d030a5676347b1d4d154f87158b1', 'synform2': '6f7ba4560a9c348908278dade1b546673693df5f17468f2a953091305dae6589', 'synform2_err': '6c10d024b1451f348de7c443a8e6b3d097891417af3043234bf1fab66a95975c', 'yolo_full': '179c66c3292d3a934d8486cb9be88d9feb9fa25e9788b13cb7def43ea55e6c02', 'yolo_no_scan': 'd12fe3bf81c45c4ac991d4086c4ef22b77dcc20ec3fa9680b7b67e26aefbf543'}

def checked_inputs():
 data={};metadata={}
 for k,path in FILES.items():
  raw=(ROOT/path).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256_PINS[k]:
   raise AssertionError("SOURCE_BYTES_CHANGED_USE_APPEND_ONLY_SUCCESSOR: "+path)
  data[k]=json.loads(raw)
  metadata[k]={'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
               'scope':'exact file identity only; not accuracy, replication or independent scientific admission'}
 return data,metadata
def evidence_row(key,label,kind,source,state,claim,limits,method='STANDARD_METHOD',owner='MIXED'):
 return {'id':key,'label':label,'kind':kind,'source_keys':source,'evidence_state':state,
         'claim_ceiling':claim,'limits':limits,'classification':method,'work_lane':owner,
         'scientific_admitted':False}
def build(data,metadata):
 b=data['baseline'];m=data['m0']['metrics']['overall'];f=data['fcar']
 o=data['ocr'];a={x['arm']:x for x in o['arms']}
 trained=data['ocr_source']['comparisons_vs_A0']
 logit=data['logit'];bbox=data['bbox'];pr=data['progress']
 assert b['arms']['A0_pre_harness']['test']['forms_succeeded']==18
 assert b['arms']['A1_fcg_harness']['test']['forms_succeeded']==30
 assert b['arms']['A0_pre_harness']['test']['forms']==54
 assert m['forms']==92 and m['full_form_success_required']==0
 assert m['outcomes']['correct']==381 and m['fields']==920
 assert data['synform2']['cases']==111 and data['synform2_err']['cases']==23
 assert a['A1']['challenger_all7']==22 and a['A1']['baseline_all7']==14
 assert a['A1']['p_holm_3_comparisons']==0.0234375
 assert a['A1']['status']=='NOT_PROMOTED_EXTERNAL_REPLICATION_PENDING'
 assert a['A2']['status'].startswith('NULL') and a['A3']['status'].startswith('NULL')
 assert 'HOLD' in f['admit']['state'] and f['replicate']['independent_prospective_replication']=='NOT_TESTED'
 assert logit['learned_minus_baseline_recall']==0.0
 assert bbox['D1']['metrics']['recall_iou50']<bbox['D2']['metrics']['recall_iou50']
 assert trained['A1']['decision'].startswith('PROMOTE_DISCOVERY')
 assert data['hosted']['teammate_hosted_benchmark']['n_runs']==48
 assert data['hosted']['teammate_hosted_benchmark']['n_quality_regressions']==3
 progress_events=pr['events']
 assert len(progress_events)==24 and all(e.get('promoted') is not True for e in progress_events)
 rows=[
 evidence_row('FF-DATA-SYNTHEA','100 synthetic Synthea FHIR subset patients','DATA',['freeze','baseline'],
 'ADMITTED_SYNTHETIC_TEST_ASSET','Pinned local synthetic benchmark, train/validation/test 63/19/18',
 'Not real clinical records, Epic sandbox population or 100 independent replications.',
 'STANDARD_DATA_GENERATION','CLAUDE'),
 evidence_row('FF-DATA-SYNFORM2','111-case SYNFORM2 / 222 synthetic images','DATA',['synform2'],
 'ADMITTED_SYNTHETIC_TEST_ASSET','Form image evaluation asset',
 'Private oracle not exported; independent new-template clinical validation NOT_TESTED.','PROJECT_SPECIFIC_SYNTHETIC_FIXTURE','CLAUDE'),
 evidence_row('FF-DATA-SYNFORM2-ERR','23-case / 230-image planted-error derivative','DATA',['synform2_err'],
 'ADMITTED_SYNTHETIC_CHALLENGE','Known implanted error benchmark for source-binding and detection',
 'Planted keys remain private and causal estimates depend on fixture design.','PROJECT_SPECIFIC_SYNTHETIC_FIXTURE','CLAUDE'),
 evidence_row('FF-BASE-B0','B0 deterministic baseline 18/54 full forms','BASELINE',['baseline'],
 'OBSERVED','18/54 test forms required fields complete; no neural weights',
 'No cross-cohort guarantee.','STANDARD_DETERMINISTIC_BASELINE','CLAUDE'),
 evidence_row('FF-BASE-M0','Local zero-shot Qwen2.5-0.5B 0/92 full forms','BASELINE',['m0'],
 'OBSERVED_NEGATIVE','381/920 fields; 0/92 complete forms on validation+test',
 'Nontrivial model swap is not improvement; M1 fine-tuned successor not established.','STANDARD_ZERO_SHOT_INFERENCE','CLAUDE'),
 evidence_row('FF-FCO-01','Source-bound FCO/FCG L1+L3 harness +22.22 pp','DISCOVERY',['baseline','progress','fcar'],
 'OBSERVED_DISCOVERY_POSITIVE_NOT_ADMITTED','18/54 to 30/54 forms, deterministic modules, same weights',
 'Rules built after baseline errors exposed; not preregistered independent cohort replication.','PROJECT_SPECIFIC_INTEGRATION','CLAUDE'),
 evidence_row('FF-OCR-01','Learned OCR post-correction +17.39 pp','DISCOVERY',['ocr','ocr_source','fcar'],
 'PROMOTE_DISCOVERY_ONLY_NOT_SCIENTIFIC','A0 14/46 to A1 22/46 complete seven-field images; Holm p 0.0234375',
 '23 synthetic cases paired across clean/scan; preregistration timing and new cohort unverified. Correction table learned, not Qwen weight training.','STANDARD_FITTED_POSTPROCESSING_APPLIED_TO_PROJECT','CLAUDE'),
 evidence_row('FF-CROP-A2A3','YOLO crops A2=9/46, A3=15/46','NEGATIVE_OR_NULL',['ocr','ocr_source'],
 'NULL_NOT_PROMOTED','Compared with A0 14/46; confidence intervals include zero',
 'Failure to improve complete-form accuracy; do not use mAP alone to claim model gain.','STANDARD_TRAINED_DETECTOR','CLAUDE'),
 evidence_row('FF-BBOX-LOGIT','Trained logistic vs deterministic contour 540/540 tie','NEGATIVE_OR_NULL',['logit'],
 'NEGATIVE_NO_GAIN','Learned-versus-contour recall delta 0; paired McNemar p=1',
 'Training on three blank layouts does not prove generalization.','STANDARD_TRAINED_CLASSIFIER','CHATGPT_INDEPENDENT'),
 evidence_row('FF-BBOX-D1D2','D1 bad, D2 post-hoc exploratory','NEGATIVE_OR_NULL',['bbox'],
 'NEGATIVE_D1_EXPLORATORY_D2','D1 recall 13.06%; D2 recall 95.56% with 65.65% precision',
 'Post-hoc candidate classifier, 180 false positives, no new-template test.','STANDARD_NEURAL_BOX_CLASSIFICATION','CHATGPT_INDEPENDENT'),
 evidence_row('FF-YOLO-LOMO','YOLO full/no-scan 30-epoch training and control','NEGATIVE_OR_NULL',['yolo_full','yolo_no_scan','judge'],
 'EXECUTED_NO_SCIENTIFIC_PROMOTION','Full 315/322 fields vs no-scan 316/322; epoch GAIN/LOSS/NEUTRAL logged',
 'Merklized training ledger establishes recorded byte lineage, not performance benefit.','PROJECT_SPECIFIC_LEDGER_ON_STANDARD_TRAINING','CLAUDE'),
 evidence_row('FF-HOSTED-PILOT','Teammate 48 hosted benchmark runs','PILOT',['hosted'],
 'SEPARATE_REPORTED_PILOT','24 matched pairs; 23 faster tool pairs, 3 quality regressions',
 'Hosted weights/revision unknown; do not attribute to local Qwen or clinical model improvement.','STANDARD_MODEL_COMPARISON','TEAMMATE'),
 evidence_row('FF-ADMISSION-FCAR','Scientific admission and independent replication','ADMISSION',['fcar','ocr','judge'],
 'HOLD_NO_INDEPENDENT_PI_ADMISSION','Synthetic benchmark assets and discovery claims retained with source identities',
 'Prospective replication, interop/clinical tests and independent PI signoff NOT_TESTED.','PROJECT_SPECIFIC_ADMISSION_GATE','CHATGPT_INDEPENDENT'),
 ]
 # A candidate integration can be distinctive within the repository without being globally novel.
 novelty=[
 {'feature':'Use Synthea FHIR/HTML forms, PDF creation, Apple OCR, Qwen, YOLO/LoRA',
  'baseline':'Established tooling, standard supervised, zero-shot and transfer learning',
  'our_contribution':'Integrated local synthetic form loopback and separate model/OCR arms',
  'novelty_level':'STANDARD_COMPONENTS_PROJECT_INTEGRATION',
  'prior_art':'NOT_REVIEWED','effect':'Descriptive system integration; no new training algorithm claimed',
  'evidence':['freeze','m0','ocr','yolo_full']},
 {'feature':'Source-bound FCO/FCG action gate L1 evidence-abstain, L2 unit checks, L3 source binding',
  'baseline':'Deterministic validation/error handling and paired rule ablations are known',
  'our_contribution':'Per-field source-grounded conditional correction with explicit abstention, provenance and LOMO edges',
  'novelty_level':'PROJECT_SPECIFIC_DESIGN_CANDIDATE',
  'prior_art':'NOT_REVIEWED','effect':'Discovery +22.22 pp on exposed synthetic test; neural weights UNCHANGED',
  'evidence':['baseline','progress']},
 {'feature':'Merkle/Lean/FCO LOMO × local model training epoch lineage',
  'baseline':'Merkle integrity, formal constraints, test ablation and model checkpointing are established',
  'our_contribution':'Joined source leaves, constraints, trained model epoch receipts, negative/hold decisions and audit replay',
  'novelty_level':'PROJECT_SPECIFIC_EVIDENCE_ARCHITECTURE',
  'prior_art':'NOT_REVIEWED','effect':'Inspectability of experimental process, not proof of causal superiority',
  'evidence':['judge','yolo_full','yolo_no_scan','fcar']},
 {'feature':'Learned OCR correction from synthetic training split',
  'baseline':'Fitted text normalization / postprocessing is a standard method, not fine-tuning LLM neural weights',
  'our_contribution':'Same-case paired clean/scan evaluation with three arms and separate null controls',
  'novelty_level':'STANDARD_METHOD_NEW_OBSERVED_LOCAL_RESULT',
  'prior_art':'NOT_REVIEWED','effect':'A1 discovery +17.39 pp; NOT_PROMOTED_EXTERNAL_REPLICATION_PENDING',
  'evidence':['ocr','ocr_source']},
 {'feature':'Negative results preserved beside positive findings',
  'baseline':'Rigorous research practice, not novel as a scientific method',
  'our_contribution':'Append-only outcomes linked to distinct PRs, source-byte identities and admission states',
  'novelty_level':'PROJECT_SPECIFIC_WORKFLOW_INTEGRATION',
  'prior_art':'NOT_REVIEWED','effect':'Prevents claims of promotion from just Git merges or model training',
  'evidence':['progress','hosted','judge']},
 ]
 assert not any(r['scientific_admitted'] for r in rows)
 return {'schema':'frontier_forms.observation_discovery_novelty.v1',
  'parent_commit':'POPULATED_FROM_GIT_AT_WRITE_TIME', # replaced in main; not Merkle
  'scope':'SYNTHETIC_ONLY_LOCAL_AND_SEPARATE_HOSTED_PILOT',
  'gate_policy':'Data accepted as synthetic benchmark assets and observations; conditional discovery evidence retained; NO independent scientific, clinical or external novelty admission.',
  'source_files_sha256':metadata,
  'admission_rows':rows,
  'novelty_matrix':novelty,
  'scientific_admission':'HOLD_NO_INDEPENDENT_PI_ADMISSION',
  'discovery_positive_count':2,
  'discovery_ocr_internal_label':'PROMOTE_DISCOVERY',
  'discovery_ocr_independent_status':a['A1']['status'],
  'model_weight_gain':'NOT_COMPUTED_FOR_QUALIFYING_FINE_TUNE',
  'true_external_novelty':'UNKNOWN_PRIOR_ART_NOT_REVIEWED',
  'independent_replication':'NOT_TESTED',
  'vithia_daisy_cross_program_transfer':'NONE',
  'new_merkle_root':'NOT_COMPUTED',
  'status_taxonomy':'PROPOSED IMPLEMENTED EXECUTED OBSERVED SUPPORTED FAILED NULL NEGATIVE DEFERRED NOT_TESTED UNKNOWN NOT_COMPUTED'}
def main():
 data,meta=checked_inputs()
 out=build(data,meta)
 import subprocess
 out['parent_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print('PASS',len(out['admission_rows']),'evidence rows',len(out['novelty_matrix']),'comparison rows; NO scientific override')
if __name__=='__main__':main()
