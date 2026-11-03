#!/usr/bin/env python3
"""Create/independently replay an immutable discovery/data-admission evidence successor.

Data admission means a frozen observation is accepted into the *evidence index*.
Scientific admission is governed independently by FCAR and remains HOLD.
This script does not run, retrain, rescore or promote model experiments.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/governance/DISCOVERY_ADMISSION_V2_20261102.json'
SOURCE_PATHS=[
'docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json',
'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json',
'docs/judges/DISCOVERY_ADMISSION_AND_NOVELTY_20261102.md',
'docs/figures/gains_heatmap.json',
'evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json',
'evidence/redteam/trained_gain/trained_gain_summary.json',
'evidence/redteam/trained_gain/trained_gain_rows.json',
]
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
SHA=lambda b:hashlib.sha256(b).hexdigest()
def merkle(leaves):
    if not leaves:raise ValueError('EMPTY_DISCOVERY_EVENTS')
    layer=[hashlib.sha256(b'\x00'+CANON(x)).digest() for x in leaves]
    while len(layer)>1:
        if len(layer)%2:layer.append(layer[-1])
        layer=[hashlib.sha256(b'\x01'+layer[i]+layer[i+1]).digest() for i in range(0,len(layer),2)]
    return layer[0].hex()
def src_sha(path):return SHA((ROOT/path).read_bytes())
def admission(id,status,category,source,metric=None,delta=None,ci=None,p=None,holm=None,
              checkpoint=None,weight_change=None,independent_replication=False,extra=None):
    if status not in ('DISCOVERY_POSITIVE','NEGATIVE','NULL','NEUTRAL','FAILED_PRESERVED',
                      'METHOD_PASS_NO_SCIENTIFIC_PROMOTION','TRAINING_OBSERVATION','NOT_COMPUTED'):
        raise ValueError('INVALID_ADMISSION_CLASS')
    return {
     'id':id,'admission':'ADMITTED_TO_EVIDENCE_LEDGER',
     'scientific_promotion':False,'scientific_grade':'DISCOVERY_OR_TECHNICAL_ONLY',
     'status':status,'category':category,'source':source,'source_file_sha256':src_sha(source),
     'metric':metric,'delta':delta,'patient_ci95':ci,'mcnemar_p':p,'holm_p':holm,
     'recorded_checkpoint_sha256':checkpoint,'weights_changed':weight_change,
     'independent_replication':independent_replication,
     'source_claim_limits':extra or {}
    }
def build():
    j=json.loads((ROOT/SOURCE_PATHS[0]).read_text())
    o=json.loads((ROOT/SOURCE_PATHS[1]).read_text())
    h=json.loads((ROOT/SOURCE_PATHS[3]).read_text())
    fcar=json.loads((ROOT/SOURCE_PATHS[4]).read_text())
    source=json.loads((ROOT/SOURCE_PATHS[5]).read_text())
    assert j['outcome_event_count']==82 and len(j['yolo_training'])==2
    assert fcar['admit']['state']=='HOLD_NO_INDEPENDENT_PI_ADMISSION'
    assert o['observed_discovery_positive_arms']==1 and len(o['arms'])==3
    assert len(h['rows'])==31 and len(h['cells'])==52
    assert source['comparisons_vs_A0']['A1']['arm_all7']==22
    entries=[]
    for x in j['fco']['rows']:
        s='DISCOVERY_POSITIVE' if x['delta']>0 and x['holm_p']<.05 else (
           'NEGATIVE' if x['delta']<0 else 'NULL')
        entries.append(admission('FCO:'+x['arm'],s,'FCO_LEAF_LOMO',
          SOURCE_PATHS[0], 'synthetic_full_form_success',x['delta'],x['ci95_patient_cluster'],
          x['mcnemar_p'],x['holm_p'],weight_change=False,extra={'leaf':x['leaf'],
          'unit':'54 forms / 18 synthetic patients; test exposure in rule design',
          'source_fco_root':j['fco']['source_graph_root']}))
    for x in j['injected_errors']['rows']:
        s='DISCOVERY_POSITIVE' if x['delta']>0 and x['holm_p']<.05 else (
           'NEGATIVE' if x['delta']<0 else 'NULL')
        entries.append(admission('DETECTOR:'+x['leaf'],s,'DETERMINISTIC_FAULT_DETECTOR',
          SOURCE_PATHS[0], 'synthetic_seeded_error_recall',x['delta'],None,
          x['mcnemar_p'],x['holm_p'],weight_change=False,
          extra={'unit':'702 error instances; patient-cluster CI NOT_COMPUTED',
                 'known_source_binding_fp_cost':'see detector original source'}))
    for lane in j['yolo_training']:
        assert len(lane['epochs'])==30
        for x in lane['epochs']:
            st={'GAIN':'DISCOVERY_POSITIVE','LOSS':'NEGATIVE','NEUTRAL':'NEUTRAL',
                'FIRST_EPOCH':'TRAINING_OBSERVATION'}[x['state']]
            entries.append(admission('YOLO:'+lane['lane']+':epoch-'+str(x['epoch']),st,
               'TRAINED_YOLO_CHECKPOINT_DEV',SOURCE_PATHS[0],
               'full_dev_image_pass_rate',x['gain_vs_prev'],None,x['mcnemar_p'],
               None,x['weights_sha256'],True,
               extra={'dev_pass':x['dev_image_pass'],'dev_total':x['dev_image_total'],
                      'epoch_chain_root':lane['root'],
                      'checkpoint_bytes_independently_rehashed':False,
                      'unit':'44 development renderings, not patient bootstrap'}))
    for x in o['arms']:
        s='DISCOVERY_POSITIVE' if x['discovery_positive'] else (
            'NEGATIVE' if x['delta_all7']<0 else 'NULL')
        entries.append(admission('OCR:'+x['arm'],s,'SYNFORM2_LEARNED_OCR_ABLATION',
           SOURCE_PATHS[1],'all_seven_field_correct_rate',x['delta_all7'],
           x['patient_cluster_bootstrap95'],x['mcnemar_exact'],
           x['p_holm_3_comparisons'],
           o['correction_parameters_sha256'] if x['arm']=='A1' else o['detector_weights_sha256_recorded'],
           x['arm'] in ('A1','A2','A3'),
           extra={'n_images':46,'n_unique_case_ids':23,
                  'learned_component':'fitted OCR correction rule table, NOT neural fine-tuning' if x['arm']=='A1' else 'YOLO detector crops, may include fitted correction',
                  'pretest_preregistration_chronology':'NOT_INDEPENDENTLY_VERIFIED',
                  'independent_new_cohort_replication':'NOT_TESTED',
                  'source_ocr_event_root':o['ocr_event_root']}))
    for x in j['vision_models']['random_forest']:
        entries.append(admission('RF:'+str(x['train_patients'])+'syntheticpatients',
           'NEGATIVE','TRAINED_RANDOM_FOREST_CROSS_SECTION',SOURCE_PATHS[0],
           'bounding_box_f1_vs_deterministic',x['delta'],None,None,None,
           x['weights_sha256'],True,
           extra={'training_patient_count':x['train_patients'],
             'control_f1':x['control_f1'],'f1':x['f1'],
             'separate_model_checkpoints_not_training_epochs':True}))
    lg=j['vision_models']['learned_logistic']
    entries.append(admission('LOGISTIC:local_box_v1','NULL','TRAINED_LOGISTIC_FIELD_BBOX',
        SOURCE_PATHS[0],'bounding_box_recall_vs_deterministic',lg['gain'],lg['ci95_patient_cluster'],
        lg['p'],None,lg['weights_sha256'],True,
        extra={'unit':'540 DOM-labeled fields','model_beats_control':False}))
    entries.append(admission('OCR:pre_annotated_overlay','NEGATIVE','OCR_PREPROCESSING',
        SOURCE_PATHS[0],'correct_field_count_delta',(0-58)/70,None,None,None,None,
        False,extra={'source_result':'58/70 clean vs 0/70 boxes-before-OCR',
        'model_trained_in_this_intervention':False}))
    entries.append(admission('CUSTODY:original_demo_manifest','FAILED_PRESERVED',
        'PROVENANCE_ASSET_REPAIR',SOURCE_PATHS[0],None,None,None,None,None,None,
        False,extra={'original_failure':'10 mismatched annotation JSON hashes',
          'successor_verified':'62/62 source asset hashes',
          'asset_root':'227a1786183dc2535c5aeb54c28ace33c3c6b803584480eb97b646bbffcc444c'}))
    entries.append(admission('FCAR:admission','METHOD_PASS_NO_SCIENTIFIC_PROMOTION',
        'PROSPECTIVE_ADMISSION_GATE',SOURCE_PATHS[4],None,None,None,None,None,
        None,False,extra={'actual_state':fcar['admit']['state'],
          'source_methodology':'Vita DAISY-inspired freeze-challenge-replicate-admit',
          'daisy_weights_or_metrics_imported':False}))
    entries.append(admission('QWEN:LORA','NOT_COMPUTED','NEURAL_SFT_WEIGHT_GAIN',
        SOURCE_PATHS[0],None,None,None,None,None,None,True,
        extra={'observed_snapshot':'epoch 0 training validation loss only in prior frozen ledger',
               'adapter_checkpoint_bytes':'NOT_OBSERVED_IN_INITIAL_SNAPSHOT',
               'paired_heldout_gain':'NOT_COMPUTED'}))
    assert len(entries)==12+6+60+3+3+1+1+1+1+1, len(entries)
    expected={'DISCOVERY_POSITIVE','NEGATIVE','NULL','NEUTRAL','FAILED_PRESERVED',
              'METHOD_PASS_NO_SCIENTIFIC_PROMOTION','TRAINING_OBSERVATION','NOT_COMPUTED'}
    assert {x['status'] for x in entries}==expected
    assert all(not e['scientific_promotion'] and e['admission']=='ADMITTED_TO_EVIDENCE_LEDGER' for e in entries)
    components=[
      {'component':'Synthea synthetic patient/EHR and FHIR structure','standard':'MITRE Synthea, FHIR R4, ordinary form widgets','project_integration':'patient × synthetic FHIR source × form × field binding, frozen oracle decisions and echo/PNG/PDF artifacts','novelty':'INTEGRATED_ENGINEERING_ONLY_NOT_PRIOR_ART_CLEARED','origin':'multi-agent'},
      {'component':'Local OCR & model training','standard':'Apple Vision OCR, YOLOv8n pretrained base + fine-tuning, Qwen, LoRA, random forest','project_integration':'same-patient clean/scan matched four-arm OCR correction and raw answer/box receipts with negative controls','novelty':'SPECIFIC_EVALUATION_DESIGN_NOT_NEW_MODEL_ARCHITECTURE','origin':'Claude Code PR #51/#58'},
      {'component':'Clinical FCO/FCG validation','standard':'deterministic evidence abstention, field validation and clinical filtering','project_integration':'source-linked FCO L1 and L3 conditional intervention with 12-contrast LOMO, exact paired analysis, admission hold','novelty':'CONTEXTUAL_INTEGRATION_CANDIDATE_UNVERIFIED_GLOBAL_NOVELTY','origin':'multi-agent PR #10/#48'},
      {'component':'Merkle and LOMO traceability','standard':'SHA-256, canonical JSON, Merkle tree, McNemar, bootstrap, Holm','project_integration':'independently replayed data/model leaf, epoch × arm chains, patient-cluster uncertainty, negative-result ledger and GitHub/Notion labeling','novelty':'ENGINEERING_COMPOSITION_NOT_NEW_MATH','origin':'multi-agent; independent ChatGPT PR #14/#18/#64'},
      {'component':'Scientific admission methodology','standard':'Vita DAISY-style freeze–challenge–replicate–admit principle','project_integration':'separate Frontier Forms FCAR source/replication gate that refuses to promote discovery without independent PI replication','novelty':'METHOD_TRANSFER_WITHOUT_DAISY_WEIGHT_OR_DATA_REUSE','origin':'multi-agent; Claude PR #49'},
    ]
    result={'schema':'frontier-forms.discovery-admission-machine-ledger.v2',
       'program':'frontier-forms','data_policy':'SYNTHETIC_ONLY',
       'operation':'ADMISSION_INTO_DISCOVERY_AND_NEGATIVE_EVIDENCE_INDEX_NOT_MODEL_PROMOTION',
       'source_inputs_file_sha256':{p:src_sha(p) for p in SOURCE_PATHS},
       'source_predecessor_roots':{'judge_82_event_root':j['outcome_event_root'],
          'ocr_3_arm_root':o['ocr_event_root'],
          'synthetic_demo_asset_root':'227a1786183dc2535c5aeb54c28ace33c3c6b803584480eb97b646bbffcc444c'},
       'source_heatmap_rows':len(h['rows']),'source_heatmap_cells':len(h['cells']),
       'event_count':len(entries),
       'status_counts':{s:sum(e['status']==s for e in entries) for s in sorted(expected)},
       'admitted_entries':entries,
       'novel_vs_standard':components,
       'scientific_promotion_count':0,
       'scientific_admission':'HOLD_NO_INDEPENDENT_PI_ADMISSION',
       'daisy_specific_model_gain':'NOT_COMPUTED',
       'no_new_model_training_or_external_provider_calls':True,
       'publication_after_event_cutoff':'THIS_IS_A_SUCCESSOR_AUDIT_NOT_PROOF_OF_JUDGED_SUBMISSION_CONTENT',
       'root_algorithm':'SHA256(0x00||UTF8 canonical sorted compact JSON leaf); SHA256(0x01||left||right); duplicate final odd'}
    result['admission_event_root']=merkle(entries)
    return result
def presentation_successor():
    old=json.loads(OUT.read_text())
    new=build()
    src='docs/figures/gains_heatmap.json'
    assert old['admitted_entries']==new['admitted_entries'],'V2_SOURCE_LEAVES_CHANGED'
    assert old['admission_event_root']==new['admission_event_root'],'V2_EVIDENCE_ROOT_CHANGED'
    assert old['source_inputs_file_sha256'][src]!=new['source_inputs_file_sha256'][src]
    v1='evidence/admission/FF_DISCOVERY_AND_NOVELTY_V1.json'
    manifest={
      'schema':'frontier-forms.discovery-admission-v3-presentation-link.v1',
      'predecessor_v2_manifest_file_sha256':SHA(OUT.read_bytes()),
      'predecessor_v2_event_root':old['admission_event_root'],
      'v1_admission_source_file_sha256':src_sha(v1),
      'v1_source_path':v1,
      'admitted_event_count_unchanged':len(old['admitted_entries']),
      'predecessor_heatmap_file_sha256':old['source_inputs_file_sha256'][src],
      'current_heatmap_file_sha256':new['source_inputs_file_sha256'][src],
      'heatmap_cells_unchanged':52,
      'current_source_ledger_leaf_root':new['admission_event_root'],
      'source_difference':'HEATMAP_PRESENTATION_CHANGED_PR67; ALL_89_FROZEN_EVIDENCE_LEAVES_IDENTICAL',
      'scientific_promotions':0,
      'status':'SUCCESSOR_LINK_NOT_NEW_MODEL_GAIN',
      'exact_root_scheme':'SHA256(0x00 || canonical_sorted_compact_UTF8_JSON_manifest_without_root)'
    }
    manifest['successor_manifest_root']=SHA(b'\\x00'+CANON(manifest))
    return manifest

def verify_root_scheme_successor():
    v3=ROOT/'evidence/governance/DISCOVERY_ADMISSION_V3_PRESENTATION_SUCCESSOR_20261102.json'
    v4=ROOT/'evidence/governance/DISCOVERY_ADMISSION_V4_ROOT_SCHEME_CORRECTION_20261102.json'
    rec=json.loads(v4.read_text())
    assert rec['predecessor_v3_file_sha256']==SHA(v3.read_bytes()),'V3_BYTES_CHANGED'
    assert rec['predecessor_v3_declared_root_did_not_use_nul'] is True
    actual=dict(rec)
    expected=actual.pop('corrected_successor_root')
    assert SHA(bytes([0])+CANON(actual))==expected,'CORRECTED_NUL_ROOT_MISMATCH'
    assert rec['admitted_89_event_root']==json.loads(OUT.read_text())['admission_event_root']
    assert rec['scientific_promotions']==0
    return expected

def verify():
    target=json.loads(OUT.read_text())
    recomputed=build()
    assert target['admission_event_root']==merkle(target['admitted_entries']),'FROZEN_V2_EVENT_ROOT_MUTATED'
    changed=[p for p in SOURCE_PATHS if target['source_inputs_file_sha256'][p]!=recomputed['source_inputs_file_sha256'][p]]
    if changed:
        assert changed==['docs/figures/gains_heatmap.json'],'UNEXPECTED_SOURCE_DRIFT:'+str(changed)
        assert target['admitted_entries']==recomputed['admitted_entries'],'MODEL_OUTCOMES_CHANGED'
        assert target['admission_event_root']==recomputed['admission_event_root'],'LOMO_ROOT_CHANGED'
        assert target['source_heatmap_cells']==recomputed['source_heatmap_cells']==52,'HEATMAP_CELLS_CHANGED'
        successor=ROOT/'evidence/governance/DISCOVERY_ADMISSION_V3_PRESENTATION_SUCCESSOR_20261102.json'
        assert successor.is_file(),'MISSING_SOURCE_PRESENTATION_SUCCESSOR'
        assert json.loads(successor.read_text())==presentation_successor(),'SOURCE_PRESENTATION_SUCCESSOR_MUTATED'
        verify_root_scheme_successor()
    else:
        assert target==recomputed,'DISCOVERY_LEDGER_OR_SOURCE_MUTATED'
    assert target['event_count']==len(target['admitted_entries'])
    assert target['scientific_promotion_count']==0
    return {'status':'PASS_FROZEN_V2_AND_PRESENTATION_SUCCESSOR' if changed else 'PASS',
            'source_presentation_only_drift':changed,
            'entries':target['event_count'],
            'source_heatmap_cells':target['source_heatmap_cells'],
            'scientific_promotions':0,'root':target['admission_event_root'],
            'status_counts':target['status_counts']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true')
    opts=p.parse_args()
    if opts.write:
        if OUT.exists():raise FileExistsError('APPEND_ONLY_LEDGER_EXISTS')
        OUT.parent.mkdir(exist_ok=True,parents=True)
        OUT.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
    print(json.dumps(verify(),sort_keys=True,indent=2))
