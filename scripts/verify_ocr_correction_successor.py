#!/usr/bin/env python3
"""Independently replay 46 paired, synthetic learned-OCR comparisons and 23-case bootstrap."""
from __future__ import annotations
import collections,hashlib,json,math,random
from pathlib import Path

R=Path(__file__).resolve().parents[1]
ROWS='evidence/redteam/trained_gain/trained_gain_rows.json'
SUM='evidence/redteam/trained_gain/trained_gain_summary.json'
OUTPUT=R/'docs/judges/OCR_CORRECTION_SUCCESSOR_V2.json'
CANON=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
SHA=lambda b:hashlib.sha256(b).hexdigest()
def mcn(b,c):
 n=b+c
 return min(1.0,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n) if n else 1.
def holm(x):
 s=sorted(x.items(),key=lambda kv:kv[1]); p={};m=len(s); cur=0.
 for k,(a,b) in enumerate(s):
  cur=max(cur,(m-k)*b);p[a]=min(1.,cur)
 return p
def cluster_ci(rows,arm,reps=10000,seed=20261102):
 by=collections.defaultdict(list)
 for r in rows:
  by[r['case_id']].append(int(r['arms'][arm]['all7'])-int(r['arms']['A0']['all7']))
 ids=sorted(by);assert len(ids)==23
 assert all(len(v)==2 for v in by.values()),"NOT_TWO_RENDERS_PER_PATIENT"
 rand=random.Random(seed);d=[]
 for _ in range(reps):
  picks=[ids[rand.randrange(len(ids))] for __ in ids]
  vals=[x for p in picks for x in by[p]]
  d.append(sum(vals)/len(vals))
 d.sort()
 return [d[int((len(d)-1)*.025)],d[int((len(d)-1)*.975)]]
def root(leaves):
 level=[hashlib.sha256(b'\x00'+CANON(x)).digest() for x in leaves]
 while len(level)>1:
  if len(level)%2:level.append(level[-1])
  level=[hashlib.sha256(b'\x01'+level[i]+level[i+1]).digest() for i in range(0,len(level),2)]
 return level[0].hex()
def build():
 rows=json.loads((R/ROWS).read_text())
 source=json.loads((R/SUM).read_text())
 assert len(rows)==46 and len({r['case_id'] for r in rows})==23
 identities=[(r['case_id'],r['variant']) for r in rows]
 assert len(set(identities))==46
 assert {r['variant'] for r in rows}=={'clean','scan'}
 assert sorted(collections.Counter(r['case_id'] for r in rows).values())==[2]*23
 armdata=[]
 rawp={}
 for arm in ('A1','A2','A3'):
  b=sum(r['arms']['A0']['all7'] and not r['arms'][arm]['all7'] for r in rows)
  c=sum(r['arms'][arm]['all7'] and not r['arms']['A0']['all7'] for r in rows)
  both=sum(r['arms'][arm]['all7'] and r['arms']['A0']['all7'] for r in rows)
  succ=sum(r['arms'][arm]['all7'] for r in rows)
  own=source['comparisons_vs_A0'][arm]
  assert b==own['baseline_only'] and c==own['arm_only'] and succ==own['arm_all7']
  assert sum(r['arms']['A0']['all7'] for r in rows)==14
  assert abs(mcn(b,c)-own['p_mcnemar_exact_two_sided'])<1e-14
  assert abs((c-b)/46-own['delta_all7_rate'])<1e-14
  rawp[arm]=mcn(b,c)
  row={'arm':arm,'baseline_all7':14,'challenger_all7':succ,
       'n_images':46,'n_synthetic_cases':23,'discordant_baseline_only':b,
       'discordant_challenger_only':c,'both_correct':both,
       'both_incorrect':46-b-c-both,
       'delta_all7':(c-b)/46,'mcnemar_exact':rawp[arm],
       'source_bootstrap_stratified_by_render':own['ci95_bootstrap_stratified'],
       'patient_cluster_bootstrap95':cluster_ci(rows,arm),
       'patient_cluster_bootstrap_reps':10000,
       'effect_type':'OCR_POST_CORRECTION_TABLE' if arm=='A1' else 'DETECTOR_CROP_COMPARISON',
       'model_weights_sha256':None,
       'status':'NOT_PROMOTED_EXTERNAL_REPLICATION_PENDING'}
  armdata.append(row)
 adj=holm(rawp)
 for r in armdata:
  original=source['comparisons_vs_A0'][r['arm']]
  assert abs(adj[r['arm']]-original['p_holm'])<1e-14
  r['p_holm_3_comparisons']=adj[r['arm']]
  r['discovery_positive']=r['delta_all7']>0 and adj[r['arm']]<.05 and r['patient_cluster_bootstrap95'][0]>0
  if not r['discovery_positive']:r['status']='NULL_OR_NEGATIVE_NO_PROMOTION'
 table=source['trained_components']['post_correction']
 assert table['fit_on'].endswith('(132 images)')
 table_sha=SHA(CANON(table))
 result={'schema':'frontier-forms.ocr-correction-independent-paired-successor.v2',
   'program':'frontier-forms','scope':'SYNFORM2 synthetic 23 cases x clean/scan, 46 images, 7 fields',
   'predecessor_judge_outcome_root':'71d3bdac181ca273537a4493ea967a41bd618eabfc83590c750b633d180ceae6',
   'source_file_sha256':{ROWS:SHA((R/ROWS).read_bytes()),SUM:SHA((R/SUM).read_bytes())},
   'rows_case_variant_sha256':SHA(CANON(sorted(identities))),
   'source_form_weight_type':'FITTED_OCR_CORRECTION_TABLE_NOT_NEURAL_WEIGHTS',
   'correction_parameters_sha256':table_sha,
   'detector_weights_sha256_recorded':source['trained_components']['yolov8n_detector_best_sha256'],
   'detector_checkpoint_bytes_independently_rehashed':False,
   'source_test_split':'reported one test touch (46 images); preregistration chronology not independently proven from a pre-test signed receipt',
   'preregistration_state':'SELF_REPORTED_SCRIPT_DOCSTRING_PRETEST_TIMESTAMP_NOT_INDEPENDENTLY_VERIFIED',
   'source_multiplicity':'Holm across A1/A2/A3',
   'patient_cluster_bootstrap':'23 paired cases, 10,000 whole-case resamples, same clean+scan pair each draw',
   'arms':armdata,'scientific_admission':'HOLD_PENDING_INDEPENDENT_PROSPECTIVE_PATIENT_AND_TEMPLATE_REPLICATION',
   'observed_discovery_positive_arms':sum(r['discovery_positive'] for r in armdata),
   'external_daisy_model_or_data_used':False,'daisy_performance_gain':'NOT_COMPUTED',
   'performance_heterogeneity':'clean/scan correlated and same family layout; no cross-template replication',
   'root_recipe':'SHA256(0x00+sorted_compact_UTF8_JSON_arm); SHA256(0x01+left_raw+right_raw); duplicate last'}
 result['ocr_event_root']=root(armdata)
 return result
def verify():
 r=build()
 if not OUTPUT.exists():raise FileNotFoundError(str(OUTPUT))
 frozen=json.loads(OUTPUT.read_bytes())
 assert frozen==r,'OCR_RECEIPT_OR_SOURCE_DRIFT'
 assert r['arms'][0]['discovery_positive'] is True
 assert all(not a['discovery_positive'] for a in r['arms'][1:])
 assert r['observed_discovery_positive_arms']==1
 assert r['scientific_admission'].startswith('HOLD_')
 return {'state':'PASS','root':r['ocr_event_root'],'arms':len(r['arms']),
         'n_images':46,'n_patients':23,'patient_ci':r['arms'][0]['patient_cluster_bootstrap95'],
         'scientific_promotions':0}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true')
 a=p.parse_args()
 if a.write:
  if OUTPUT.exists():raise FileExistsError('APPEND_ONLY_OCCUPIED')
  OUTPUT.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
 print(json.dumps(verify(),sort_keys=True))
