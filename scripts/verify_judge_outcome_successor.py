#!/usr/bin/env python3
"""Independently validate frozen judge outcomes, actual epoch chains, and outcomes."""
import json,hashlib,math
from pathlib import Path
R=Path(__file__).resolve().parents[1]
CANON=lambda o:json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
SHA=lambda b:hashlib.sha256(b).hexdigest()
def root(rows):
 v=[hashlib.sha256(b'\x00'+CANON(x)).digest() for x in rows]
 if not v:raise ValueError('NO_EVIDENCE_LEAVES')
 while len(v)>1:
  if len(v)%2:v.append(v[-1])
  v=[hashlib.sha256(b'\x01'+v[i]+v[i+1]).digest() for i in range(0,len(v),2)]
 return v[0].hex()
def verify():
 data=json.loads((R/'docs/judges/JUDGE_OUTCOMES_SUCCESSOR_V1.json').read_text())
 assert data['program']=='frontier-forms' and data['study_population']=='SYNTHETIC_ONLY'
 for name,sha in data['source_bytes_sha256'].items():
  assert SHA((R/name).read_bytes())==sha, 'SOURCE_BYTES_DRIFT:'+name
 epochs=data['yolo_training']
 assert len(epochs)==2
 for lane in epochs:
  path=R/f'evidence/redteam/detector/{lane["lane"]}/epoch_ledger.jsonl'
  c=R/f'evidence/redteam/detector/{lane["lane"]}/chain_manifest.json'
  assert SHA(path.read_bytes())==lane['ledger_sha256']
  raw=[json.loads(line) for line in path.read_text().splitlines()]
  assert len(raw)==30
  assert [x['epoch'] for x in raw]==list(range(1,31))
  m=json.loads(c.read_text())
  assert m['root']==lane['root']
  lv=[hashlib.sha256(b'\x00'+CANON(m['context'])).digest()]
  lv.extend(hashlib.sha256(b'\x00'+CANON(o)).digest() for o in raw)
  while len(lv)>1:
   if len(lv)%2:lv.append(lv[-1])
   lv=[hashlib.sha256(b'\x01'+lv[i]+lv[i+1]).digest() for i in range(0,len(lv),2)]
  assert lv[0].hex()==lane['root'],'EPOCH_CHAIN_MUTATED'
  for a,b in zip(raw,lane['epochs']):
   assert a['weights_sha256']==b['weights_sha256'] and a['status']==b['state']
   assert a['dev_pass']==b['dev_image_pass']
   assert b['admission']=='NOT_PROMOTED_INDEPENDENT_REPLICATION_MISSING'
  assert lane['statuses']==dict(__import__('collections').Counter(a['status'] for a in raw))
 rows=[{'type':'fco','value':r} for r in data['fco']['rows']]
 rows += [{'type':'yolo_'+lane['lane'],'value':r} for lane in epochs for r in lane['epochs']]
 rows += [{'type':'detector','value':r} for r in data['injected_errors']['rows']]
 rows += [{'type':'vision','value':r} for r in data['vision_models']['random_forest']]
 rows += [{'type':'admission','value':data['admission']}]
 assert len(rows)==data['outcome_event_count']==82
 assert root(rows)==data['outcome_event_root'],'OUTCOME_ROOT_CHANGED'
 assert len(data['fco']['rows'])==12 and len(data['injected_errors']['rows'])==6
 assert all(a['promoted'] is False for a in data['fco']['rows'])
 assert all(a['promoted'] is False for a in data['injected_errors']['rows'])
 assert data['admission']['scientific_promotions']==0
 assert data['admission']['state']=='HOLD_NO_INDEPENDENT_PI_ADMISSION'
 x=data['apple_ocr_visualization']
 assert (x['clean_correct'],x['boxes_drawn_before_ocr_correct'],x['same_fields'])==(58,0,70)
 heat=(R/'docs/judges/JUDGE_OUTCOME_HEATMAP_V1.html').read_text()
 assert all(s in heat for s in ('Figure 11','LOSS','NOT_COMPUTED','Claude Code','ChatGPT'))
 return {'status':'PASS','root':data['outcome_event_root'],'events':len(rows),'scientific_promotions':0,'training_epochs':sum(len(lane['epochs']) for lane in epochs)}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
