#!/usr/bin/env python3
"""Judge outcome successor: source-linked, append-only, no invented neural promotions."""
import json,hashlib,math
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1]; O=R/'docs/judges'
SHA=lambda b:hashlib.sha256(b).hexdigest()
CANON=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def j(path):return json.loads((R/path).read_bytes())
def exact(a,b):
 n=a+b
 return min(1.,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1.
def root(items):
 v=[hashlib.sha256(b'\x00'+CANON(x)).digest() for x in items]
 while len(v)>1:
  if len(v)%2:v.append(v[-1])
  v=[hashlib.sha256(b'\x01'+v[i]+v[i+1]).digest() for i in range(0,len(v),2)]
 return v[0].hex()
def verify_yolo(lane):
 base=f'evidence/redteam/detector/{lane}/'
 ledger=[json.loads(s) for s in (R/(base+'epoch_ledger.jsonl')).read_text().splitlines()]
 m=j(base+'chain_manifest.json')
 v=[hashlib.sha256(b'\x00'+CANON(m['context'])).digest()]
 v.extend(hashlib.sha256(b'\x00'+CANON(e)).digest() for e in ledger)
 while len(v)>1:
  if len(v)%2:v.append(v[-1])
  v=[hashlib.sha256(b'\x01'+v[i]+v[i+1]).digest() for i in range(0,len(v),2)]
 assert v[0].hex()==m['root']
 assert len(ledger)==30 and [x['epoch'] for x in ledger]==list(range(1,31))
 stats=[]
 for item in ledger:
  p=item['pairing']; pp=p['p_mcnemar_exact_two_sided']
  if pp is not None:assert abs(exact(p['baseline_only'],p['epoch_only'])-pp)<1e-12
  stats.append({'epoch':item['epoch'],'state':item['status'],
    'weights_sha256':item['weights_sha256'],'weights_file':item['weights_file'],
    'dev_image_pass':item['dev_pass'],'dev_image_total':item['dev_images'],
    'dev_fields_ok':item['dev_fields_ok'],'dev_fields_total':item['dev_fields_total'],
    'gain_vs_prev':p['delta_pass_rate'],'mcnemar_p':pp,
    'ci95_stratified_by_render':p['ci95'],'model_weight_file_local':'NOT_REHASHED_THIS_AUDIT',
    'admission':'NOT_PROMOTED_INDEPENDENT_REPLICATION_MISSING'})
 f=j(base+'final_receipt.json')
 return {'lane':lane,'root':m['root'],'root_computed':True,
  'start_weights_sha256':m['context']['start_weights_sha256'],
  'epochs':stats,'statuses':dict(Counter(x['state'] for x in stats)),
  'test':f['test'],'best_weights_sha256':f['best_weights_sha256'],
  'ledger_sha256':SHA((R/(base+'epoch_ledger.jsonl')).read_bytes()),
  'claim_limit':'Epoch comparisons on 44 dev renders (not patient-cluster bootstrap); held-out final test has 46 images; checkpoint weight bytes not rehashed in this audit.'}
def main():
 if (O/'JUDGE_OUTCOMES_SUCCESSOR_V1.json').exists():raise FileExistsError('APPEND_ONLY')
 t=j('dashboard/training_progress_latest.json')
 g=j('evidence/forms_arms/run_v1/FCG_ARMS_V1.json')
 fco=[v for v in t['events'] if v['family']=='fco_lomo']
 assert len(fco)==12 and all(v['promoted'] is False for v in fco)
 for v in fco:
  p=v['paired_table']
  assert abs(exact(p['baseline_only'],p['challenger_only'])-v['mcnemar_p_two_sided'])<1e-12
 sample=next(v for v in fco if v['parent']=='B0+L1' and v['child']=='B0+L1+L3')
 box=next(v for v in t['events'] if v['family']=='model_weight_comparison')
 tiny=[v for v in t['events'] if v['family']=='training_size_cross_section']
 det=[v for v in t['events'] if v['family']=='detector_lomo']
 receipt=j('evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json')
 assert receipt['admit']['state']=='HOLD_NO_INDEPENDENT_PI_ADMISSION'
 all_yolo=[verify_yolo('full'),verify_yolo('no_scan')]
 apple=j('docs/demo/ocr_boxes_vs_clean.json')
 assert (apple['images'],apple['fields_total'])==(10,70)
 assert sum(x['clean']['correct_count'] for x in apple['rows'].values())==58
 assert sum(x['with_boxes']['correct_count'] for x in apple['rows'].values())==0
 paths=['evidence/forms_arms/run_v1/FCG_ARMS_V1.json','dashboard/training_progress_latest.json',
 'evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json','docs/demo/ocr_boxes_vs_clean.json',
 'docs/demo/MANIFEST_REPAIR_V2.json']
 data={'schema':'frontier-forms.judge-promotions-negatives.v1',
 'program':'frontier-forms','study_population':'SYNTHETIC_ONLY',
 'principle':'identity not causality; exact pairing not independent replication',
 'source_bytes_sha256':{x:SHA((R/x).read_bytes()) for x in paths},
 'fco':{'source_graph_root':g['graph_root'],'n_arms':len(fco),
        'rows':[{'arm':v['parent']+' → '+v['child'],'leaf':v['leaf'],
         'n':v['n'],'delta':v['delta'],'mcnemar_p':v['mcnemar_p_two_sided'],
         'holm_p':v['holm_adjusted_p'],'ci95_patient_cluster':v['ci95_patient_cluster'],
         'state':v['status'],'promoted':False,'model_weights_changed':False} for v in fco],
        'strongest_discovery':{'baseline':18,'candidate':30,'n':54,
           'delta':sample['delta'],'mcnemar_p':sample['mcnemar_p_two_sided'],
           'holm_p':sample['holm_adjusted_p'],'ci95_patient_cluster':sample['ci95_patient_cluster'],
           'status':'DISCOVERY_NOT_PROMOTED'}},
 'injected_errors':{'n_injected':702,'rows':[{'leaf':v['leaf'],
   'delta':v['delta'],'mcnemar_p':v['mcnemar_p_two_sided'],
   'holm_p':v['holm_adjusted_p'],'state':v['status'],'promoted':False} for v in det],
   'warning':'error-instance units correlated by source and patient, not new clinical training'},
 'vision_models':{'learned_logistic':{'gain':box['delta'],'p':box['mcnemar_p_two_sided'],
    'ci95_patient_cluster':box['ci95_patient_cluster'],'weights_sha256':box['model_weights_sha256'],
    'state':'NEGATIVE_NO_GAIN'},
    'random_forest': [{'train_patients':x['train_patients'],'weights_sha256':x['model_weights_sha256'],
          'f1':x['value'],'control_f1':x['control_value'],
          'delta':x['delta'],'state':'NEGATIVE_NO_GAIN'} for x in tiny]},
 'yolo_training':all_yolo,
 'apple_ocr_visualization':{'same_images':10,'same_fields':70,
   'clean_correct':58,'boxes_drawn_before_ocr_correct':0,
   'state':'NEGATIVE_PREPROCESSING_EFFECT_NOT_MODEL_GAIN'},
 'admission':{'freeze':'PASS_SOURCE_RECEIPT',
   'challenge':'OBSERVED','technical_replay':'PASS','prospective_replicate':'NOT_TESTED',
   'scientific_promotions':0,'state':'HOLD_NO_INDEPENDENT_PI_ADMISSION',
   'daisy_method_used':True,'daisy_weights_metrics_or_roots_imported':False,
   'daisy_specific_gain':'NOT_COMPUTED'},
 'ownership':{'original_figures_demo':'CLAUDE_CODE_PR51',
   'current_demo_manifest_repair':'CHATGPT_INDEPENDENT_AUDIT',
   'fco_training_results':'MULTI_AGENT_SOURCE_SPECIFIC',
   'github_author_login':'NOT_SUFFICIENT_FOR_AGENT_ATTRIBUTION'},
 'source_main_parent':None,
 'root_scheme':'sha256 domain separated canonical json leaf + node; duplicate last; outcome integrity only'}
 # Canonical event root excludes itself; computed from actual data rows used by judge figures.
 leaves=[{'type':'fco','value':x} for x in data['fco']['rows']]
 leaves += [{'type':'yolo_'+r['lane'],'value':x} for r in all_yolo for x in r['epochs']]
 leaves += [{'type':'detector','value':x} for x in data['injected_errors']['rows']]
 leaves += [{'type':'vision','value':x} for x in data['vision_models']['random_forest']]
 leaves += [{'type':'admission','value':data['admission']}]
 data['outcome_event_root']=root(leaves)
 data['outcome_event_count']=len(leaves)
 path=O/'JUDGE_OUTCOMES_SUCCESSOR_V1.json'
 path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
 print('OUTCOMES',len(leaves),'ROOT',data['outcome_event_root'],'YOLO_STATES',all_yolo[0]['statuses'],all_yolo[1]['statuses'],'NO_PROMOTIONS',data['admission']['scientific_promotions'])
if __name__=='__main__':main()
