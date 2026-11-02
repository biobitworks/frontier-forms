#!/usr/bin/env python3
"""Snapshot-faithful Gantt from PR metadata and existing frozen receipts.
PR bars are GitHub open -> merge/closed/as-of, NEVER training runtime.
All model and data dates have exact source timestamp OR PR-created proxy.
No new performance measurement or Merkle root is computed.
"""
import json, re, subprocess, html, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
prs=json.loads((OUT/'GANTT_PR_SOURCE_SNAPSHOT_20261102.json').read_text())
UTC=dt.timezone.utc
PST=ZoneInfo('America/Los_Angeles')
# Captured snapshot of the PR list. Open bars end at this as-of moment, not at their future merge.
ASOF='2026-11-02T23:46:01Z'
def epoch(s):
 return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def as_pt(s):
 return dt.datetime.fromtimestamp(epoch(s),PST).strftime('%I:%M:%S %p PT').lstrip('0')
CLAUDE={6,9,10,11,13,17,19,20,21,23,26,29,42,47,50,51}
CHATGPT={7,12,14,15,16,18,22,46,48,49,54,55}
TEAM={4}
SECURITY={8,27,28,30,39,43,45}
def lane(n):
 if n in TEAM:return 'Teammate / app'
 if n in CLAUDE:return 'Claude Code / red-team'
 if n in CHATGPT:return 'ChatGPT / independent'
 if n in SECURITY:return 'Security / integration'
 return 'Mixed / attribution uncertain'
def tag(n):
 if n==4:return 'App and Supabase spec'
 if n in {10,17}:return 'Synthetic cohort, B0 and FCO'
 if n in {14,15,16,19}:return 'Trained bbox or VLM'
 if n in {20,21,23}:return 'SYNFORM2 models / detectors'
 if n in {7,12,18,44,46,48,49}:return 'LOMO, Merkle and gates'
 if n in {22}:return '100-patient loopback, Qwen/PDF'
 if n in {29,50,51,54,55}:return 'Judges, screenshots and provenance'
 if n in {26,52,53}:return 'Rules and sponsor/submit docs'
 return 'Review, CI and integration'
def source_pr(n):return 'https://github.com/biobitworks/frontier-forms/pull/'+str(n)
events=[]
for p in prs:
 n=p['number']
 # GitHub createdAt is observable. Pseudo-duration captures PR open/review, not implementation/training.
 end=(p.get('mergedAt') or p.get('closedAt') or ASOF)
 events.append({'id':f'PR-{n:03}','kind':'pull_request','lane':lane(n),'title':f"#{n} {p['title']}",
 'start_utc':p['createdAt'],'end_utc':end,'timestamp_basis':'GitHub PR createdAt to mergedAt/closedAt; open to snapshot cutoff',
 'state':p['state'],'promotion':'GIT_MERGED' if p['state']=='MERGED' else 'NOT_GIT_MERGED',
 'scientific_promotion':'UNKNOWN_NOT_IMPLIED_BY_MERGE','category':tag(n),'url':p['url'],
 'source_pr':n,'sha':p['headRefOid'],'is_draft':p['isDraft']})
def milestone(code,lane_,label,when,source,pr,state,notes,origin='SOURCE_TIMESTAMP',end=None):
 events.append({'id':code,'kind':'receipt_interval' if end else 'data_model_milestone','lane':lane_,
 'title':label,'start_utc':when,'end_utc':end or when,'timestamp_basis':origin,
 'state':state,'promotion':'NOT_ADMITTED' if state not in ('PROMOTED',) else 'PROMOTED',
 'scientific_promotion':state,'category':'Data / model receipt','source_path':source,
 'source_pr':pr,'url':source_pr(pr) if pr else None,'note':notes})
milestone('DATA-001','Dataset milestones','MITRE Synthea FHIR v3.4.0 / 100 frozen patients',
          next(x for x in prs if x['number']==10)['createdAt'],
 'data/forms_cohort_v1/GENERATION.json',10,'FROZEN',
 '63 train / 19 validation / 18 test. Proxy = PR creation, not actual data-generation instant.',
 'PR_CREATED_PROXY')
milestone('DATA-002','Dataset milestones','SYNFORM2 111 cases / 222 images',
 '2026-11-02T22:02:55Z','evidence/redteam/synform2/manifest.json',20,'FROZEN',
 'Source built_utc; train/dev/test 66/22/23, private oracle not published.')
milestone('DATA-003','Dataset milestones','SYNFORM2-ERR 23 cases / 230 images',
 '2026-11-02T22:13:52Z','evidence/redteam/synform2_err/manifest.json',20,'FROZEN',
 'Planted synthetic errors, private planted-key not published.')
milestone('MODEL-001','Model / OCR receipts','Qwen2.5 0.5B SFT epoch-0 snapshot, no gain admitted',
 '2026-11-02T22:56:23Z','dashboard/training_progress_latest.json',18,'BASELINE_ONLY',
 'Observed loss snapshot; trained-model lift NOT_COMPUTED. Timestamp from event ID.')
meta=json.loads((ROOT/'evidence/redteam/lanes/VLM_qwen2.5vl_3b_synform2_test_META.json').read_text())
milestone('MODEL-002','Model / OCR receipts','Local qwen2.5vl:3b on SYNFORM2 test',
 meta['started_utc'],'evidence/redteam/lanes/VLM_qwen2.5vl_3b_synform2_test_META.json',23,
 'EXECUTED_NOT_PROMOTED','46 test images; local model digest; not comparable to separate OCR field accuracy without matching protocol.',
 'SOURCE_RUN_INTERVAL',meta['finished_utc'])
mod=json.loads((ROOT/'evidence/redteam/db/models.json').read_text())
for i,(name,v) in enumerate(sorted(mod['models'].items()),3):
 runs=v.get('runs',[])
 # Refer to actual metadata receipt finishing or to PR creation where no time exists.
 best=[]
 for row in runs:
  p=ROOT/'evidence/redteam/lanes'/row.get('meta_file','')
  if p.is_file():
   try: best.append((json.loads(p.read_text()).get('finished_utc'),p))
   except: pass
 stamps=[(a,b) for a,b in best if a]
 if not stamps:continue
 when,path=max(stamps)
 milestone('MODEL-%03d'%i,'Model / OCR receipts',name+' ('+str(len(runs))+' runs indexed)',
  when,str(path.relative_to(ROOT)),23,'EXECUTED_NOT_PROMOTED',
  'Shown as latest recorded finish only; distinct runs are separately indexed in model DB.',
  'SOURCE_LATEST_FINISH')
# PR #16 has measured results but no independently documented absolute training clock.
milestone('MODEL-011','Model / OCR receipts','D1 negative / D2 exploratory local bounding boxes',
 next(x for x in prs if x['number']==16)['createdAt'],
 'evidence/forms_bbox/LOCAL_BBOX_D1_D2_AUDIT_20261102.json',16,'NEGATIVE_AND_EXPLORATORY',
 'D1 13.06% recall; D2 95.56% recall, 65.65% precision. Timestamp proxy = PR created, NOT training clock.',
 'PR_CREATED_PROXY')
milestone('MODEL-012','Model / OCR receipts','Logistic box detector = contour control (no improvement)',
 next(x for x in prs if x['number']==14)['createdAt'],
 'evidence/forms_box_validator/run_v3/summary.json',14,'NEGATIVE',
 '540/540 vs 540/540, model lift 0. Training clock unknown; PR start proxy.','PR_CREATED_PROXY')
milestone('MODEL-013','Model / OCR receipts','YOLOv8n full vs no-scan, 30 epochs each',
 next(x for x in prs if x['number']==21)['createdAt'],
 'evidence/redteam/detector/full/final_receipt.json',21,'EXECUTED_NOT_PROMOTED',
 'Full 315/322, no-scan 316/322 fields; epochs are internal training steps, NOT measured timeline points.',
 'PR_CREATED_PROXY')
# Judge-only package on different Claude branch; be explicit it is a draft.
milestone('MODEL-014','Model / OCR receipts','Apple OCR on drawn boxes: negative draft demonstration',
 next(x for x in prs if x['number']==51)['createdAt'],
 'https://github.com/biobitworks/frontier-forms/pull/51',51,'DRAFT_NEGATIVE',
 'PR #51 reports clean 58/70 vs annotated 0/70, 10 forms; PR #55 independent audit fixes 10 annotation manifest entries. No main admission.',
 'PR_CREATED_PROXY')
# Funding and sponsor eligibility is a separate domain; don't imply Fireworks model was run.
milestone('BOUND-001','Governance / promotion','FCAR gate assessment: clinical/model superiority HOLD',
 next(x for x in prs if x['number']==49)['createdAt'],
 'evidence/admission/FF_FCAR_GATE_ASSESSMENT_V1.json',49,'HOLD_NO_PROMOTION',
 'No prospective replication / human scientific approval. Framework methodology only, DAISY model weights not imported.',
 'PR_CREATED_PROXY')
progress=json.loads((ROOT/'dashboard/training_progress_latest.json').read_text())
gates=[]
for e in progress['events']:
 gates.append({'id':e['id'],'family':e.get('family'),'model':e.get('model'),
  'status':e.get('status'),'promoted':e.get('promoted',None),
  'delta':e.get('delta'),'source':'dashboard/training_progress_latest.json',
  'time_basis':'2026-11-02T22:56:23Z snapshot; individual event wall times not all independently recorded'})
gate_counts={k:sum(g['status'].startswith(k) for g in gates) for k in ('NEGATIVE','DISCOVERY_POSITIVE','OBSERVED')}
positive=sum(g['status']=='DISCOVERY_POSITIVE_NOT_PROMOTED' for g in gates)
promoted=sum(g['promoted'] is True for g in gates)
# Existing public JSON and data manifest coverage index: paths, Git blob SHA (identity only).
names=subprocess.check_output(['git','ls-files','-s','-z'],cwd=ROOT).split(b'\0')
source_index=[]
for item in names:
 if not item:continue
 hdr,path=item.split(b'\t',1)
 chunks=hdr.decode().split()
 p=path.decode()
 if p.endswith('.json') and p.startswith(('evidence/','data/','dashboard/','redteam/')):
  source_index.append({'path':p,'git_blob_sha1':chunks[1],'family':p.split('/')[1] if '/' in p else p,
    'bytes_in_github':True,'url':'https://github.com/biobitworks/frontier-forms/blob/'+
    subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()+'/'+p})
ledger={'schema':'frontier_forms.gantt.evidence.v1','snapshot_utc':ASOF,
 'snapshot_timezone':'America/Los_Angeles','pr_count':len(prs),
 'pr_counts':{x:sum(p['state']==x for p in prs) for x in ('MERGED','OPEN','CLOSED')},
 'interval_rule':'PR creation-to-merge/closure is review lifetime, NOT actual engineering start/end; open intervals to cutoff',
 'promotion_policy':'MERGED_GIT is NOT scientifically ADMITTED. Trained model promotion requires preregistered independent replicated gain.',
 'scientific_promotions_in_24_training_events':promoted,'discovery_positives_not_promoted':positive,
 'negative_or_tie_events':sum(g['status'].startswith('NEGATIVE') for g in gates),
 'unknowns':'Training clock times absent for several PR-linked models; do not invent them.',
 'events':events,'gates':gates,'indexed_existing_public_json_sources':source_index,
 'legacy_public_images_policy':'Existing public images remain historical; no new PNG/PDF/model weights pushed.',
 'merkle_root':'NOT_COMPUTED'}
(OUT/'FRONTIER_FORMS_GANTT_EVIDENCE_20261102.json').write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print('GANTT_ITEMS',len(events),'PR',len(prs),'MODEL_GATE_EVENTS',len(gates),
 'NEGATIVE',ledger['negative_or_tie_events'],'DISCOVERY',positive,'PROMOTED',promoted,
 'INDEXED_JSON',len(source_index))
